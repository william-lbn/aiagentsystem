from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable
import hashlib
import json
import time
import uuid

from .models import Model
from .tools import ToolRegistry, ToolResult
from .events import Event
from .journal import EffectJournal
from .checkpoint import JsonCheckpointStore
from .budget import RuntimeBudget
from .security import PolicyEngine
from .tracing import TraceRecorder


@dataclass
class AgentState:
    run_id: str
    messages: list[dict[str, Any]] = field(default_factory=list)
    steps: int = 0
    answer: str | None = None
    status: str = "RUNNING"
    pending_approval: dict[str, Any] | None = None
    pending_effect: dict[str, Any] | None = None
    version: int = 0


class AgentRuntime:
    """Small, inspectable runtime with explicit external-effect correctness rules.

    Teaching invariants:
    1. policy is checked before a tool executes;
    2. the immutable tool intent is journaled before the side effect;
    3. approval is bound to that exact intent, not merely to a tool name;
    4. the EXECUTING_EFFECT checkpoint is durable before entering user code;
    5. COMMITTED / NOT_APPLIED / UNKNOWN remain distinct outcomes;
    6. recovery from an interrupted effect never blindly replays the effect.

    The runtime deliberately does *not* claim unconditional exactly-once effects:
    a crash after an external system commits but before local result persistence
    is an ambiguous outcome unless the external system supplies an idempotency or
    reconciliation mechanism.  That window transitions to NEEDS_RECONCILIATION.
    """

    def __init__(
        self,
        model: Model,
        tools: ToolRegistry,
        *,
        journal=None,
        checkpoint=None,
        budget=None,
        policy=None,
        tracer=None,
        clock: Callable[[], float] | None = None,
        approval_ttl_seconds: float = 3600.0,
    ):
        self.model = model
        self.tools = tools
        self.journal = journal or EffectJournal()
        self.checkpoint = checkpoint or JsonCheckpointStore()
        self.budget = budget or RuntimeBudget()
        self.policy = policy or PolicyEngine()
        self.tracer = tracer or TraceRecorder()
        self.clock = clock or time.time
        self.approval_ttl_seconds = approval_ttl_seconds

    def _event(self, typ: str, state: AgentState, data: dict[str, Any]):
        self.journal.append(Event(typ, state.run_id, state.steps, data))

    def _state_dict(self, state: AgentState) -> dict[str, Any]:
        return {
            "messages": state.messages,
            "steps": state.steps,
            "answer": state.answer,
            "status": state.status,
            "pending_approval": state.pending_approval,
            "pending_effect": state.pending_effect,
        }

    def _save(self, state: AgentState):
        state.version = self.checkpoint.save(
            state.run_id,
            self._state_dict(state),
            expected_version=state.version,
        )

    def _load_or_create(self, user_input: str, resume: bool, run_id: str | None) -> AgentState:
        loaded = self.checkpoint.load(run_id) if resume else None
        if loaded:
            return AgentState(run_id=loaded["run_id"], version=loaded.get("version", 0), **loaded["state"])
        if resume:
            raise KeyError(f"no checkpoint found for run_id={run_id!r}")
        state = AgentState(str(uuid.uuid4()), [{"role": "user", "content": user_input}])
        self._event("run_started", state, {"input": user_input})
        self._save(state)
        return state

    @staticmethod
    def _canonical_args(args: dict[str, Any]) -> str:
        return json.dumps(args, sort_keys=True, ensure_ascii=False, separators=(",", ":"))

    def _make_intent(
        self, state: AgentState, tool: str, args: dict[str, Any], *, approval_required: bool
    ) -> dict[str, Any]:
        canonical = self._canonical_args(args)
        args_hash = hashlib.sha256(canonical.encode()).hexdigest()
        raw = f"{state.run_id}:{state.steps}:{tool}:{args_hash}".encode()
        action_id = hashlib.sha256(raw).hexdigest()
        meta = self.tools.metadata_or_default(tool)
        now = float(self.clock())
        return {
            "action_id": action_id,
            "tool": tool,
            "args": args,
            "args_hash": args_hash,
            "idempotent": bool(meta.get("idempotent", False)),
            "risk": meta.get("risk", "unknown"),
            "approval_required": approval_required,
            "approval_state_version": state.version + 1,
            "created_at": now,
            "expires_at": now + self.approval_ttl_seconds if approval_required else None,
        }

    def _execute_intent(self, state: AgentState, intent: dict[str, Any]) -> ToolResult:
        # Persist the ambiguous crash window *before* user/tool code runs.
        state.pending_effect = dict(intent)
        state.pending_approval = None
        state.status = "EXECUTING_EFFECT"
        self._save(state)
        self._event("effect_execution_started", state, {"action_id": intent["action_id"], "tool": intent["tool"]})

        with self.tracer.span("tool.execute", tool=intent["tool"], step=state.steps, action_id=intent["action_id"]):
            self.budget.charge_tool()
            result = self.tools.execute(intent["tool"], intent["args"])

        state.messages += [
            {"role": "assistant", "tool": intent["tool"], "args": intent["args"], "action_id": intent["action_id"]},
            result.to_message(),
        ]
        self._event(
            "tool_result",
            state,
            {"action_id": intent["action_id"], "tool": intent["tool"], "result": result.to_message()},
        )

        if result.status == "COMMITTED":
            state.status = "RUNNING"
            state.pending_effect = None
        elif result.status == "NOT_APPLIED":
            # Fail closed: a rejected/invalid tool call cannot be silently turned
            # into a later FINISHED answer in the same run.
            state.status = "TOOL_NOT_APPLIED"
            state.pending_effect = None
        else:  # UNKNOWN
            state.status = "NEEDS_RECONCILIATION"
            state.pending_effect = {**intent, "reported_status": "UNKNOWN", "retryable": result.retryable}

        self._save(state)
        self._event("checkpoint", state, {"path": str(self.checkpoint.path), "version": state.version})
        return result

    def _resume_preflight(self, state: AgentState) -> bool:
        """Return True when caller should stop and surface current state."""
        if state.status == "EXECUTING_EFFECT":
            # The process may have crashed before, during, or just after the
            # external effect. Re-executing would be unsafe without observation.
            state.status = "NEEDS_RECONCILIATION"
            self._event(
                "effect_outcome_unknown",
                state,
                {
                    "reason": "resumed_from_executing_effect",
                    "pending_effect": state.pending_effect or {},
                },
            )
            self._save(state)
            return True
        if state.status == "APPROVED_PENDING_EFFECT":
            if not state.pending_effect:
                state.status = "FAILED"
                self._event("run_failed", state, {"reason": "approved_effect_missing"})
                self._save(state)
                return True
            self._execute_intent(state, state.pending_effect)
            return state.status != "RUNNING"
        return state.status in {
            "NEEDS_RECONCILIATION",
            "FINISHED",
            "REJECTED",
            "BLOCKED",
            "FAILED",
            "TOOL_NOT_APPLIED",
            "BUDGET_EXCEEDED",
            "APPROVAL_EXPIRED",
        }

    def run(
        self,
        user_input: str,
        *,
        resume: bool = False,
        run_id: str | None = None,
        approval: str | None = None,
        approval_action_id: str | None = None,
    ) -> dict[str, Any]:
        state = self._load_or_create(user_input, resume, run_id)

        if state.status == "WAITING_APPROVAL":
            pending = state.pending_approval or {}
            if approval not in {"approve", "reject"}:
                return self._finish(state, terminal=False)
            if approval_action_id != pending.get("action_id"):
                self._event(
                    "stale_approval_rejected",
                    state,
                    {
                        "provided": approval_action_id,
                        "expected": pending.get("action_id"),
                        "reason": "approval_must_bind_exact_pending_action",
                    },
                )
                return self._finish(state, terminal=False)
            expires_at = pending.get("expires_at")
            if isinstance(expires_at, (int, float)) and self.clock() > expires_at:
                state.status = "APPROVAL_EXPIRED"
                self._event("approval_expired", state, pending)
                self._save(state)
                return self._finish(state)
            if approval == "reject":
                state.status = "REJECTED"
                self._event("approval_rejected", state, pending)
                self._save(state)
                return self._finish(state)

            # Persist the decision before entering the effect. If we crash now,
            # APPROVED_PENDING_EFFECT is safe to resume because execution has not
            # started yet.
            state.pending_approval = None
            state.pending_effect = dict(pending)
            state.status = "APPROVED_PENDING_EFFECT"
            self._event("approval_granted", state, pending)
            self._save(state)
            self._execute_intent(state, pending)
            if state.status != "RUNNING":
                return self._finish(state)

        elif resume and self._resume_preflight(state):
            return self._finish(state, terminal=state.status not in {"NEEDS_RECONCILIATION"})

        # Prompt policy belongs to run creation.  A resume call is a transport
        # operation over an already-persisted run, not a new user request;
        # re-authorizing on the resume payload would let an arbitrary transport
        # string change the semantics of an existing approval/recovery decision.
        if not resume:
            prompt_decision = self.policy.check_prompt(user_input)
            if not prompt_decision.allowed:
                state.status = "BLOCKED"
                self._event("run_failed", state, {"reason": prompt_decision.reason})
                self._save(state)
                return self._finish(state)

        while state.status == "RUNNING":
            state.steps += 1
            ok, reason = self.budget.check(state.steps)
            if not ok:
                state.status = "BUDGET_EXCEEDED"
                self._event("budget_exceeded", state, {"reason": reason})
                break
            with self.tracer.span("model.complete", run_id=state.run_id, step=state.steps):
                self.budget.charge_model()
                decision = self.model.complete(state.messages, self.tools.schema())
            self._event(
                "model_decision",
                state,
                {
                    "final": decision.final,
                    "tool": decision.tool,
                    "args": decision.args,
                    "rationale": decision.rationale,
                },
            )
            if decision.final is not None:
                state.answer = decision.final
                state.status = "FINISHED"
                break
            if not decision.tool:
                state.status = "FAILED"
                self._event("run_failed", state, {"reason": "empty_model_decision"})
                break

            args = decision.args or {}
            p = self.policy.check_tool(decision.tool, args)
            intent = self._make_intent(state, decision.tool, args, approval_required=p.require_approval)
            self._event(
                "tool_intent",
                state,
                {
                    **intent,
                    "policy": {"allowed": p.allowed, "reason": p.reason, "require_approval": p.require_approval},
                },
            )
            if not p.allowed:
                state.status = "BLOCKED"
                break
            if p.require_approval:
                state.status = "WAITING_APPROVAL"
                state.pending_approval = intent
                self._event("approval_required", state, intent)
                self._save(state)
                return self._finish(state, terminal=False)

            self._execute_intent(state, intent)
            if state.status != "RUNNING":
                break

        self._save(state)
        return self._finish(state)

    def _finish(self, state: AgentState, terminal: bool = True):
        if terminal:
            self._event("run_finished", state, {"status": state.status, "answer": state.answer})
        return {
            "run_id": state.run_id,
            "state_version": state.version,
            "status": state.status,
            "answer": state.answer,
            "messages": state.messages,
            "pending_approval": state.pending_approval,
            "pending_effect": state.pending_effect,
            "trace": self.tracer.spans,
            "budget": self.budget.__dict__,
        }
