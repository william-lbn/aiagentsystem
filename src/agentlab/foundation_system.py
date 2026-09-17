"""Executable foundations for Chapters 1-6.

This module is intentionally provider-independent.  It models the contracts a
production agent runtime must enforce *around* a probabilistic model:

* a model proposes an action; a runtime authorizes and executes it;
* model output is decoded through syntax, schema, and semantic gates;
* context is selected under trust, tenant, freshness, and token constraints;
* tool calls and tool results form a typed, identity-preserving message ledger;
* plans are checked for graph, capability, and resource feasibility;
* run state is reconstructed from events and protected by versioned writes.

The code uses only the standard library and AgentLab primitives so the Core
Labs remain deterministic on macOS/Linux, x86_64/arm64, and Python 3.11-3.13.
Real provider and upstream-SDK evidence belongs in the separate integration
track; these classes are the inspectable reference semantics for that track.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Iterable, Mapping
from collections import Counter
import hashlib
import json

from .checkpoint import JsonCheckpointStore


class EvidenceLevel(str, Enum):
    L1_MECHANISM = "L1_MECHANISM"
    L2_ORACLE_ONLY = "L2_ORACLE_ONLY"
    L2_DETECTED = "L2_DETECTED"
    L3_CONTAINED = "L3_CONTAINED"
    L4_RECOVERED = "L4_RECOVERED"


@dataclass(frozen=True, slots=True)
class ScenarioOutcome:
    """Facts observed by a scenario, before conversion to a public result.

    Unlike a scenario-name allowlist, these fields force every lab to state
    what the component detected, what it prevented, and what it recovered.
    """

    scenario: str
    invariant: str
    observation: dict[str, Any]
    fault_injected: bool
    oracle_detected: bool
    system_detected: bool
    contained: bool
    recovered: bool
    invariant_holds: bool

    def __post_init__(self) -> None:
        if not self.fault_injected and any(
            (self.oracle_detected, self.system_detected, self.contained, self.recovered)
        ):
            raise ValueError("normal-path evidence cannot claim fault handling")
        if self.system_detected and not self.oracle_detected:
            raise ValueError("system detection must be observable to the experiment oracle")
        if self.contained and not (self.system_detected and self.invariant_holds):
            raise ValueError("containment requires system detection and a preserved invariant")
        if self.recovered and not self.contained:
            raise ValueError("recovery evidence requires prior containment")

    @property
    def passed(self) -> bool:
        return self.oracle_detected if self.fault_injected else self.invariant_holds

    @property
    def evidence_level(self) -> EvidenceLevel:
        if not self.fault_injected:
            return EvidenceLevel.L1_MECHANISM
        if self.recovered:
            return EvidenceLevel.L4_RECOVERED
        if self.contained:
            return EvidenceLevel.L3_CONTAINED
        if self.system_detected:
            return EvidenceLevel.L2_DETECTED
        return EvidenceLevel.L2_ORACLE_ONLY

    @property
    def evidence_meaning(self) -> str:
        return {
            EvidenceLevel.L1_MECHANISM: "normal_path_assertion_satisfied",
            EvidenceLevel.L2_ORACLE_ONLY: "external_oracle_observed_bad_outcome_only",
            EvidenceLevel.L2_DETECTED: "fault_detected_but_not_containment_or_recovery",
            EvidenceLevel.L3_CONTAINED: "fault_detected_and_contained",
            EvidenceLevel.L4_RECOVERED: "fault_detected_contained_and_reconciled",
        }[self.evidence_level]


@dataclass(frozen=True, slots=True)
class DecisionValidation:
    accepted: bool
    stage: str
    errors: tuple[str, ...]
    decision: dict[str, Any] | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "accepted": self.accepted,
            "stage": self.stage,
            "errors": list(self.errors),
            "decision": self.decision,
        }


class StrictDecisionDecoder:
    """Decode a discriminated model decision at a software boundary.

    ``schema`` maps tool names to required argument names and Python types.  A
    bool is deliberately not accepted as an int: Python's subtype relation is
    convenient for programs but surprising at a JSON/API boundary.
    """

    _TOP_LEVEL = {"kind", "tool", "arguments", "final", "confidence"}

    def __init__(self, schema: Mapping[str, Mapping[str, type]], *, min_confidence: float = 0.0):
        self.schema = {name: dict(arguments) for name, arguments in schema.items()}
        self.min_confidence = min_confidence

    @staticmethod
    def _is_type(value: Any, expected: type) -> bool:
        if expected is int:
            return isinstance(value, int) and not isinstance(value, bool)
        return isinstance(value, expected)

    def decode(self, payload: str) -> DecisionValidation:
        try:
            obj = json.loads(payload)
        except json.JSONDecodeError as exc:
            return DecisionValidation(False, "syntax", (f"invalid_json:{exc.msg}",), None)
        if not isinstance(obj, dict):
            return DecisionValidation(False, "schema", ("decision_must_be_object",), None)

        unknown = sorted(set(obj) - self._TOP_LEVEL)
        kind = obj.get("kind")
        errors: list[str] = [f"unknown_field:{key}" for key in unknown]
        if kind not in {"tool", "final"}:
            errors.append("kind_must_be_tool_or_final")
        if kind == "final":
            if not isinstance(obj.get("final"), str) or not obj["final"].strip():
                errors.append("final_must_be_nonempty_string")
            if "tool" in obj or "arguments" in obj:
                errors.append("final_must_not_contain_tool_fields")
        if kind == "tool":
            tool_name = obj.get("tool")
            arguments = obj.get("arguments")
            if "final" in obj:
                errors.append("tool_must_not_contain_final")
            if not isinstance(tool_name, str):
                errors.append("tool_must_be_string")
            if not isinstance(arguments, dict):
                errors.append("arguments_must_be_object")
            elif isinstance(tool_name, str) and tool_name in self.schema:
                expected = self.schema[tool_name]
                missing = sorted(set(expected) - set(arguments))
                extra = sorted(set(arguments) - set(expected))
                errors += [f"missing_argument:{key}" for key in missing]
                errors += [f"unknown_argument:{key}" for key in extra]
                for key, typ in expected.items():
                    if key in arguments and not self._is_type(arguments[key], typ):
                        errors.append(f"argument_type:{key}:expected_{typ.__name__}")
        if errors:
            return DecisionValidation(False, "schema", tuple(errors), obj)

        if kind == "tool" and obj["tool"] not in self.schema:
            return DecisionValidation(False, "semantic", ("tool_not_available",), obj)
        confidence = obj.get("confidence")
        if confidence is not None:
            if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
                return DecisionValidation(False, "schema", ("confidence_must_be_number",), obj)
            if not 0.0 <= float(confidence) <= 1.0:
                return DecisionValidation(False, "semantic", ("confidence_out_of_range",), obj)
            if float(confidence) < self.min_confidence:
                return DecisionValidation(False, "semantic", ("confidence_below_policy",), obj)
        return DecisionValidation(True, "accepted", (), obj)


@dataclass(frozen=True, slots=True)
class ContextRecord:
    record_id: str
    channel: str
    content: str
    source: str
    tenant_id: str
    token_cost: int
    priority: int
    freshness: float = 1.0
    authority: float = 1.0
    mandatory: bool = False
    untrusted: bool = False

    def utility(self) -> float:
        return self.priority * 4.0 + self.authority * 2.0 + self.freshness


@dataclass(frozen=True, slots=True)
class ContextAssembly:
    selected: tuple[ContextRecord, ...]
    excluded: Mapping[str, str]
    used_tokens: int
    budget: int
    invariant_holds: bool

    def manifest(self) -> dict[str, Any]:
        return {
            "selected": [r.record_id for r in self.selected],
            "excluded": dict(sorted(self.excluded.items())),
            "used_tokens": self.used_tokens,
            "budget": self.budget,
            "channels": [r.channel for r in self.selected],
            "sources": [r.source for r in self.selected],
        }


class ContextAssembler:
    """Select context without allowing untrusted data to become instructions."""

    _INSTRUCTION_CHANNELS = {"system", "developer", "user"}

    def assemble(self, records: Iterable[ContextRecord], *, tenant_id: str, budget: int) -> ContextAssembly:
        if not tenant_id:
            raise ValueError("tenant_id must be non-empty")
        if budget < 0:
            raise ValueError("budget must be non-negative")
        materialized = list(records)
        duplicate_ids = {record_id for record_id, count in Counter(r.record_id for r in materialized).items() if count > 1}
        candidates: list[ContextRecord] = []
        excluded: dict[str, str] = {}
        for record in materialized:
            if not record.record_id or record.record_id in duplicate_ids:
                excluded[record.record_id] = "duplicate_or_empty_record_id"
            elif record.tenant_id != tenant_id:
                excluded[record.record_id] = "tenant_mismatch"
            elif record.untrusted and record.channel in self._INSTRUCTION_CHANNELS:
                excluded[record.record_id] = "untrusted_instruction_channel"
            elif record.token_cost <= 0:
                excluded[record.record_id] = "invalid_token_cost"
            elif not 0.0 <= record.freshness <= 1.0 or not 0.0 <= record.authority <= 1.0:
                excluded[record.record_id] = "invalid_record_metadata"
            else:
                candidates.append(record)

        mandatory = sorted((r for r in candidates if r.mandatory), key=lambda r: (-r.priority, r.record_id))
        used = sum(r.token_cost for r in mandatory)
        if used > budget:
            for record in candidates:
                if not record.mandatory:
                    excluded[record.record_id] = "budget_exhausted_by_mandatory_context"
            return ContextAssembly(tuple(), excluded, used, budget, False)

        selected = list(mandatory)
        optional = sorted(
            (r for r in candidates if not r.mandatory),
            key=lambda r: (-(r.utility() / r.token_cost), -r.priority, r.record_id),
        )
        for record in optional:
            if used + record.token_cost <= budget:
                selected.append(record)
                used += record.token_cost
            else:
                excluded[record.record_id] = "token_budget"

        ids = {r.record_id for r in selected}
        invariant = (
            all(r.record_id in ids for r in mandatory)
            and used <= budget
            and all(r.tenant_id == tenant_id for r in selected)
            and not any(r.untrusted and r.channel in self._INSTRUCTION_CHANNELS for r in selected)
        )
        return ContextAssembly(tuple(selected), excluded, used, budget, invariant)


@dataclass(frozen=True, slots=True)
class MessageItem:
    item_id: str
    kind: str
    actor: str
    content: Any
    call_id: str | None = None
    name: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class AppendResult:
    accepted: bool
    errors: tuple[str, ...]
    ledger_size: int
    pending_calls: tuple[str, ...]


class MessageLedger:
    """Append-only typed item ledger with tool-call/result correlation."""

    _KINDS = {"user_message", "assistant_message", "assistant_tool_call", "tool_result"}

    def __init__(self) -> None:
        self.items: list[MessageItem] = []
        self._item_ids: set[str] = set()
        self._pending: dict[str, str] = {}
        self._completed: set[str] = set()

    def append(self, item: MessageItem) -> AppendResult:
        errors: list[str] = []
        if item.kind not in self._KINDS:
            errors.append("unknown_item_kind")
        if item.item_id in self._item_ids:
            errors.append("duplicate_item_id")
        if item.kind == "user_message":
            if item.actor != "user" or not isinstance(item.content, str) or not item.content.strip():
                errors.append("invalid_user_message")
            if item.call_id is not None or item.name is not None:
                errors.append("user_message_must_not_contain_tool_identity")
        elif item.kind == "assistant_message":
            if item.actor != "assistant" or not isinstance(item.content, str) or not item.content.strip():
                errors.append("invalid_assistant_message")
            if item.call_id is not None or item.name is not None:
                errors.append("assistant_message_must_not_contain_tool_identity")
            if self._pending:
                errors.append("final_message_with_pending_tool_calls")
        elif item.kind == "assistant_tool_call":
            if item.actor != "assistant" or not item.call_id or not item.name or not isinstance(item.content, dict):
                errors.append("invalid_tool_call")
            elif item.call_id in self._pending or item.call_id in self._completed:
                errors.append("duplicate_call_id")
        elif item.kind == "tool_result":
            if item.actor != "tool" or not item.call_id:
                errors.append("invalid_tool_result")
            elif item.call_id not in self._pending:
                errors.append("orphan_or_duplicate_tool_result")
            elif item.name != self._pending[item.call_id]:
                errors.append("tool_result_name_mismatch")

        if not errors:
            self.items.append(item)
            self._item_ids.add(item.item_id)
            if item.kind == "assistant_tool_call" and item.call_id and item.name:
                self._pending[item.call_id] = item.name
            elif item.kind == "tool_result" and item.call_id:
                self._pending.pop(item.call_id)
                self._completed.add(item.call_id)
        return AppendResult(not errors, tuple(errors), len(self.items), tuple(sorted(self._pending)))

    def digest(self) -> str:
        payload = json.dumps([i.to_dict() for i in self.items], ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class PlanStep:
    step_id: str
    depends_on: tuple[str, ...]
    capability: str
    cost: int
    effect: str = "read"


@dataclass(frozen=True, slots=True)
class FeasibilityReport:
    feasible: bool
    errors: tuple[str, ...]
    execution_order: tuple[str, ...]
    total_cost: int


class PlanValidator:
    """Check plan structure separately from task execution."""

    def validate(
        self,
        steps: Iterable[PlanStep],
        *,
        capabilities: set[str],
        budget: int,
    ) -> FeasibilityReport:
        materialized = list(steps)
        by_id = {step.step_id: step for step in materialized}
        errors: list[str] = []
        if not materialized:
            errors.append("empty_plan")
        if budget < 0:
            errors.append("negative_budget")
        if len(by_id) != len(materialized):
            errors.append("duplicate_step_id")
        for step in materialized:
            for dependency in step.depends_on:
                if dependency not in by_id:
                    errors.append(f"missing_dependency:{step.step_id}:{dependency}")
            if step.capability not in capabilities:
                errors.append(f"unavailable_capability:{step.step_id}:{step.capability}")
            if step.cost < 0:
                errors.append(f"negative_cost:{step.step_id}")

        indegree = {step_id: 0 for step_id in by_id}
        followers = {step_id: [] for step_id in by_id}
        for step in materialized:
            for dependency in step.depends_on:
                if dependency in by_id:
                    indegree[step.step_id] += 1
                    followers[dependency].append(step.step_id)
        ready = sorted(step_id for step_id, degree in indegree.items() if degree == 0)
        order: list[str] = []
        while ready:
            current = ready.pop(0)
            order.append(current)
            for follower in sorted(followers[current]):
                indegree[follower] -= 1
                if indegree[follower] == 0:
                    ready.append(follower)
                    ready.sort()
        if len(order) != len(by_id):
            errors.append("dependency_cycle")

        total_cost = sum(step.cost for step in materialized)
        if budget >= 0 and total_cost > budget:
            errors.append(f"budget_exceeded:{total_cost}>{budget}")
        unique_errors = tuple(dict.fromkeys(errors))
        return FeasibilityReport(not unique_errors, unique_errors, tuple(order) if not unique_errors else (), total_cost)


class RunPhase(str, Enum):
    RECEIVED = "RECEIVED"
    RUNNING = "RUNNING"
    WAITING_TOOL = "WAITING_TOOL"
    FINISHED = "FINISHED"
    FAILED = "FAILED"


@dataclass(frozen=True, slots=True)
class StateEvent:
    sequence: int
    from_phase: RunPhase
    to_phase: RunPhase
    reason: str

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["from_phase"] = self.from_phase.value
        data["to_phase"] = self.to_phase.value
        return data


@dataclass(frozen=True, slots=True)
class ReplayResult:
    valid: bool
    phase: RunPhase
    errors: tuple[str, ...]
    digest: str


class RunStateReducer:
    _ALLOWED = {
        RunPhase.RECEIVED: {RunPhase.RUNNING},
        RunPhase.RUNNING: {RunPhase.WAITING_TOOL, RunPhase.FINISHED, RunPhase.FAILED},
        RunPhase.WAITING_TOOL: {RunPhase.RUNNING, RunPhase.FAILED},
        RunPhase.FINISHED: set(),
        RunPhase.FAILED: set(),
    }

    def replay(self, events: Iterable[StateEvent]) -> ReplayResult:
        materialized = list(events)
        phase = RunPhase.RECEIVED
        errors: list[str] = []
        for expected_sequence, event in enumerate(materialized, 1):
            if not event.reason.strip():
                errors.append(f"empty_reason:{event.sequence}")
            if event.sequence != expected_sequence:
                errors.append(f"sequence_gap:{expected_sequence}:{event.sequence}")
            if event.from_phase != phase:
                errors.append(f"from_state_mismatch:{event.sequence}")
            if event.to_phase not in self._ALLOWED.get(phase, set()):
                errors.append(f"illegal_transition:{phase.value}->{event.to_phase.value}")
            if errors:
                break
            phase = event.to_phase
        payload = json.dumps([event.to_dict() for event in materialized], sort_keys=True, separators=(",", ":"))
        return ReplayResult(not errors, phase, tuple(errors), hashlib.sha256(payload.encode()).hexdigest())


def persist_replay(
    store: JsonCheckpointStore,
    *,
    run_id: str,
    replay: ReplayResult,
    expected_version: int,
) -> int:
    if not replay.valid:
        raise ValueError("invalid trajectory cannot be checkpointed")
    return store.save(
        run_id,
        {"phase": replay.phase.value, "trajectory_sha256": replay.digest},
        expected_version=expected_version,
    )


def compact_hash(value: str) -> str:
    """Return a stable, short display hash without weakening stored SHA-256."""

    return value[:16]
