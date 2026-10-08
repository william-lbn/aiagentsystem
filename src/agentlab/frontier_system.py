"""Executable mechanisms for Part VII: deployment through the capstone.

The code stays provider-independent so every core lab can run offline on
amd64 or arm64.  Model calls are an optional policy layer; release identity,
dataset provenance, realtime cancellation, improvement promotion and effect
reconciliation remain deterministic software responsibilities.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any, Mapping, Sequence
import json
import re
import sqlite3

from .assurance_system import (
    CapabilityGateway,
    EffectCoordinator,
    EffectOutcomeUnknown,
    ExternalEffectLedger,
    ToolIntent,
    canonical_json,
    content_digest,
)


# ---------------------------------------------------------------------------
# Chapter 36: deployment contract and source-to-runtime preflight


@dataclass(frozen=True)
class DeploymentEvidence:
    base_image: str
    base_digest: str | None
    exposed_port: int | None
    command_port: int | None
    compose_host_port: int | None
    compose_container_port: int | None
    health_path: str | None
    run_as_user: str | None
    source_digest: str
    supported_platforms: tuple[str, ...]
    locked_base_image: str | None


@dataclass(frozen=True)
class DeploymentDecision:
    checks: Mapping[str, bool]
    release_allowed: bool
    status: str


class DeploymentGate:
    """Inspect the repository's real Docker/Compose text before release."""

    _FROM = re.compile(r"^FROM\s+(?P<image>[^\s@]+)(?:@sha256:(?P<digest>[0-9a-f]{64}))?", re.MULTILINE)
    _EXPOSE = re.compile(r"^EXPOSE\s+(?P<port>\d+)\s*$", re.MULTILINE)
    _CMD_PORT = re.compile(r'["\']--port["\']\s*,\s*["\'](?P<port>\d+)["\']')
    _USER = re.compile(r"^USER\s+(?P<user>[^\s]+)\s*$", re.MULTILINE)
    _HEALTH = re.compile(r"^HEALTHCHECK[^\n]*\n?(?P<body>(?:\s+.*(?:\n|$))?)", re.MULTILINE)
    _COMPOSE_PORT = re.compile(r'["\'](?P<host>\d+):(?P<container>\d+)["\']')

    @staticmethod
    def _integer(match: re.Match[str] | None, group: str = "port") -> int | None:
        return int(match.group(group)) if match else None

    def inspect(
        self,
        dockerfile_text: str,
        compose_text: str,
        *,
        image_lock: Mapping[str, Any] | None = None,
    ) -> DeploymentEvidence:
        image = self._FROM.search(dockerfile_text)
        compose_port = self._COMPOSE_PORT.search(compose_text)
        health = self._HEALTH.search(dockerfile_text)
        health_body = health.group(0) if health else ""
        health_path_match = re.search(r"/[A-Za-z0-9_.-]*health[A-Za-z0-9_./-]*", health_body)
        user = self._USER.search(dockerfile_text)
        return DeploymentEvidence(
            base_image=image.group("image") if image else "",
            base_digest=image.group("digest") if image else None,
            exposed_port=self._integer(self._EXPOSE.search(dockerfile_text)),
            command_port=self._integer(self._CMD_PORT.search(dockerfile_text)),
            compose_host_port=self._integer(compose_port, "host"),
            compose_container_port=self._integer(compose_port, "container"),
            health_path=health_path_match.group(0) if health_path_match else None,
            run_as_user=user.group("user") if user else None,
            source_digest=sha256((dockerfile_text + "\n---compose---\n" + compose_text).encode()).hexdigest(),
            supported_platforms=tuple(sorted(set(image_lock.get("platforms", ())))) if image_lock else (),
            locked_base_image=image_lock.get("base_image") if image_lock else None,
        )

    def verify(self, evidence: DeploymentEvidence) -> DeploymentDecision:
        port = evidence.exposed_port
        checks = {
            "base_digest_pinned": bool(evidence.base_digest),
            "port_contract": port is not None
            and port == evidence.command_port
            and port == evidence.compose_container_port
            and evidence.compose_host_port is not None,
            "semantic_healthcheck": evidence.health_path == "/healthz",
            "non_root": evidence.run_as_user not in {None, "0", "root"},
            "multi_arch_declared": {"linux/amd64", "linux/arm64"}.issubset(evidence.supported_platforms),
            "image_lock_matches": evidence.locked_base_image
            == f"{evidence.base_image}@sha256:{evidence.base_digest}",
            "source_fingerprint_present": bool(re.fullmatch(r"[0-9a-f]{64}", evidence.source_digest)),
        }
        allowed = all(checks.values())
        return DeploymentDecision(checks, allowed, "STATIC_CONTRACT_READY" if allowed else "BLOCKED")

    def inspect_repository(self, root: str | Path) -> DeploymentEvidence:
        root = Path(root)
        lock_path = root / "production/agentops_service/IMAGE_LOCK.json"
        image_lock = json.loads(lock_path.read_text(encoding="utf-8")) if lock_path.exists() else None
        return self.inspect(
            (root / "production/agentops_service/Dockerfile").read_text(encoding="utf-8"),
            (root / "docker-compose.yml").read_text(encoding="utf-8"),
            image_lock=image_lock,
        )


# ---------------------------------------------------------------------------
# Chapter 37: trajectory provenance and contamination-resistant post-training


@dataclass(frozen=True)
class TrajectorySample:
    sample_id: str
    task_family: str
    split: str
    transcript: str
    source_run: str
    policy_id: str
    outcome_score: float
    safety_violations: int
    cost_units: float

    @property
    def transcript_digest(self) -> str:
        return sha256(self.transcript.encode("utf-8")).hexdigest()

    @property
    def record_digest(self) -> str:
        return content_digest(asdict(self))


@dataclass(frozen=True)
class DatasetAudit:
    checks: Mapping[str, bool]
    train_records: int
    eval_records: int
    leaked_task_families: tuple[str, ...]
    duplicate_transcripts: tuple[str, ...]
    promotion_allowed: bool
    status: str


class PostTrainingDatasetGate:
    """Fail closed on split leakage, copied transcripts and missing lineage."""

    def audit(self, samples: Sequence[TrajectorySample]) -> DatasetAudit:
        if not samples:
            raise ValueError("dataset must contain trajectory records")
        if any(sample.split not in {"train", "eval"} for sample in samples):
            raise ValueError("split must be train or eval")
        train = [sample for sample in samples if sample.split == "train"]
        evaluation = [sample for sample in samples if sample.split == "eval"]
        train_families = {sample.task_family for sample in train}
        eval_families = {sample.task_family for sample in evaluation}
        train_digests = {sample.transcript_digest for sample in train}
        eval_digests = {sample.transcript_digest for sample in evaluation}
        leaked = tuple(sorted(train_families & eval_families))
        duplicates = tuple(sorted(train_digests & eval_digests))
        ids = [sample.sample_id for sample in samples]
        checks = {
            "non_empty_splits": bool(train and evaluation),
            "unique_sample_ids": len(ids) == len(set(ids)),
            "group_disjoint": not leaked,
            "transcript_disjoint": not duplicates,
            "complete_provenance": all(sample.source_run and sample.policy_id for sample in samples),
            "bounded_labels": all(
                0.0 <= sample.outcome_score <= 1.0
                and sample.safety_violations >= 0
                and sample.cost_units >= 0
                for sample in samples
            ),
        }
        allowed = all(checks.values())
        return DatasetAudit(
            checks,
            len(train),
            len(evaluation),
            leaked,
            duplicates,
            allowed,
            "DATASET_ELIGIBLE" if allowed else "QUARANTINED",
        )


# ---------------------------------------------------------------------------
# Chapter 38: multimodal event time and cancellation epochs


@dataclass(frozen=True)
class RealtimeEvent:
    seq: int
    event_time_ms: int
    modality: str
    kind: str
    epoch: int
    payload_digest: str


class RealtimeSession:
    """Local result-commit fence, not a physical actuator or remote-effect canceler.

    ``begin_effect`` registers speculative work only.  Callers must not dispatch
    irreversible work before a separate authorization/fencing decision; after
    dispatch, an interrupt needs provider observation and reconciliation.
    """

    def __init__(self) -> None:
        self.epoch = 0
        self.events: list[RealtimeEvent] = []
        self.inflight: dict[str, int] = {}
        self.effects: list[dict[str, Any]] = []

    def _record(self, event_time_ms: int, modality: str, kind: str, payload: Any) -> RealtimeEvent:
        if self.events and event_time_ms < self.events[-1].event_time_ms:
            raise ValueError("event time regressed; reorder or quarantine before applying")
        event = RealtimeEvent(
            seq=len(self.events) + 1,
            event_time_ms=event_time_ms,
            modality=modality,
            kind=kind,
            epoch=self.epoch,
            payload_digest=content_digest(payload),
        )
        self.events.append(event)
        return event

    def ingest(self, event_time_ms: int, modality: str, kind: str, payload: Any) -> RealtimeEvent:
        return self._record(event_time_ms, modality, kind, payload)

    def begin_effect(self, effect_id: str, event_time_ms: int, intent: Mapping[str, Any]) -> int:
        if effect_id in self.inflight:
            raise ValueError("effect_id is already in flight")
        self.inflight[effect_id] = self.epoch
        self._record(event_time_ms, "tool", "effect.started", {"effect_id": effect_id, "intent": intent})
        return self.epoch

    def interrupt(self, event_time_ms: int, reason: str) -> int:
        self.epoch += 1
        self._record(event_time_ms, "audio", "user.interrupt", {"reason": reason})
        return self.epoch

    def complete_effect(
        self,
        effect_id: str,
        started_epoch: int,
        event_time_ms: int,
        result: Mapping[str, Any],
    ) -> str:
        registered = self.inflight.pop(effect_id, None)
        if registered is None:
            raise ValueError("effect was not in flight")
        if registered != started_epoch:
            raise ValueError("effect epoch does not match its registration")
        if started_epoch != self.epoch:
            self._record(event_time_ms, "tool", "effect.stale_dropped", {"effect_id": effect_id})
            return "STALE_DROPPED"
        self.effects.append({"effect_id": effect_id, "result": dict(result), "epoch": self.epoch})
        self._record(event_time_ms, "tool", "effect.committed", {"effect_id": effect_id, "result": result})
        return "COMMITTED"


# ---------------------------------------------------------------------------
# Chapter 39: paired evaluation, canary promotion and rollback


@dataclass(frozen=True)
class CandidateTaskResult:
    task_id: str
    risk_tier: str
    success: bool
    safety_violations: int
    cost_units: float


@dataclass(frozen=True)
class ImprovementDecision:
    checks: Mapping[str, bool]
    success_delta: float
    cost_ratio: float
    eligible: bool
    status: str


class ImprovementGate:
    """Compare the same tasks and treat safety as a hard, not averaged, gate."""

    def compare(
        self,
        baseline: Sequence[CandidateTaskResult],
        candidate: Sequence[CandidateTaskResult],
        *,
        max_cost_ratio: float = 1.2,
    ) -> ImprovementDecision:
        if not 0 < max_cost_ratio or not baseline or not candidate:
            raise ValueError("a positive cost ratio and non-empty paired task sets are required")
        for group in (baseline, candidate):
            if len({row.task_id for row in group}) != len(group):
                raise ValueError("duplicate task_id in paired evaluation")
            if any(not row.task_id or row.risk_tier not in {"low", "high"}
                   or row.safety_violations < 0 or row.cost_units < 0 for row in group):
                raise ValueError("invalid evaluation task result")
        base = {row.task_id: row for row in baseline}
        cand = {row.task_id: row for row in candidate}
        if not base or set(base) != set(cand):
            raise ValueError("baseline and candidate must cover the same non-empty task set")
        if any(base[task_id].risk_tier != cand[task_id].risk_tier for task_id in base):
            raise ValueError("paired task risk tier changed")
        base_success = sum(row.success for row in base.values()) / len(base)
        cand_success = sum(row.success for row in cand.values()) / len(cand)
        base_cost = sum(row.cost_units for row in base.values())
        cand_cost = sum(row.cost_units for row in cand.values())
        ratio = cand_cost / base_cost if base_cost else float("inf")
        high_risk_regression = any(
            cand[task_id].risk_tier == "high"
            and cand[task_id].safety_violations > base[task_id].safety_violations
            for task_id in base
        )
        checks = {
            "paired_tasks": set(base) == set(cand),
            "success_improves": cand_success > base_success,
            "no_safety_regression": sum(row.safety_violations for row in cand.values())
            <= sum(row.safety_violations for row in base.values()),
            "no_high_risk_regression": not high_risk_regression,
            "cost_within_budget": ratio <= max_cost_ratio,
        }
        eligible = all(checks.values())
        return ImprovementDecision(
            checks,
            round(cand_success - base_success, 4),
            round(ratio, 4),
            eligible,
            "CANARY_ELIGIBLE" if eligible else "REJECTED",
        )


class CanaryRollout:
    """Single-process teaching state machine, not a durable multi-host CAS."""

    def __init__(self, baseline_version: str):
        self.active_version = baseline_version
        self.baseline_version = baseline_version
        self.candidate_version: str | None = None
        self.history = [f"ACTIVE:{baseline_version}"]

    def start(self, candidate_version: str, decision: ImprovementDecision) -> None:
        if not decision.eligible:
            self.history.append(f"REJECTED:{candidate_version}")
            raise ValueError("candidate did not pass the offline improvement gate")
        self.candidate_version = candidate_version
        self.history.append(f"CANARY:{candidate_version}")

    def finish(self, *, verifier_passed: bool, safety_violations: int) -> str:
        if self.candidate_version is None:
            raise ValueError("no candidate is in canary")
        candidate = self.candidate_version
        if verifier_passed and safety_violations == 0:
            self.active_version = candidate
            action = "PROMOTED"
        else:
            self.active_version = self.baseline_version
            action = "ROLLED_BACK"
        self.history.append(f"{action}:{candidate}")
        self.candidate_version = None
        return action


# ---------------------------------------------------------------------------
# Chapter 40: durable capstone with authorization and effect reconciliation


class CapstoneLedger:
    _TRANSITIONS = {
        None: {"RECEIVED"},
        "RECEIVED": {"TRIAGED"},
        "TRIAGED": {"PLANNED"},
        "PLANNED": {"WAITING_APPROVAL"},
        "WAITING_APPROVAL": {"EXECUTING"},
        "EXECUTING": {"UNKNOWN", "VERIFYING"},
        "UNKNOWN": {"RECONCILING"},
        "RECONCILING": {"VERIFYING"},
        "VERIFYING": {"COMPLETED", "QUARANTINED"},
    }

    def __init__(self, path: str | Path):
        self.db = sqlite3.connect(str(path))
        self.db.row_factory = sqlite3.Row
        self.db.execute(
            """CREATE TABLE IF NOT EXISTS events(
                 run_id TEXT NOT NULL, seq INTEGER NOT NULL, state TEXT NOT NULL,
                 evidence_json TEXT NOT NULL, previous_hash TEXT NOT NULL,
                 event_hash TEXT NOT NULL, PRIMARY KEY(run_id, seq))"""
        )
        self.db.commit()

    def close(self) -> None:
        self.db.close()

    def append(self, run_id: str, state: str, evidence: Mapping[str, Any]) -> None:
        last = self.db.execute(
            "SELECT seq,state,event_hash FROM events WHERE run_id=? ORDER BY seq DESC LIMIT 1", (run_id,)
        ).fetchone()
        previous_state = last["state"] if last else None
        if state not in self._TRANSITIONS.get(previous_state, set()):
            raise ValueError(f"invalid capstone transition {previous_state!r} -> {state!r}")
        seq = int(last["seq"]) + 1 if last else 1
        previous_hash = str(last["event_hash"]) if last else "GENESIS"
        payload = canonical_json({"run_id": run_id, "seq": seq, "state": state, "evidence": evidence})
        event_hash = sha256((previous_hash + payload).encode()).hexdigest()
        with self.db:
            self.db.execute(
                "INSERT INTO events VALUES(?,?,?,?,?,?)",
                (run_id, seq, state, canonical_json(evidence), previous_hash, event_hash),
            )

    def states(self, run_id: str) -> list[str]:
        return [
            str(row["state"])
            for row in self.db.execute("SELECT state FROM events WHERE run_id=? ORDER BY seq", (run_id,))
        ]

    def verify(self, run_id: str) -> bool:
        previous = "GENESIS"
        previous_state: str | None = None
        rows = self.db.execute("SELECT * FROM events WHERE run_id=? ORDER BY seq", (run_id,)).fetchall()
        for expected_seq, row in enumerate(rows, start=1):
            if row["seq"] != expected_seq or row["state"] not in self._TRANSITIONS.get(previous_state, set()):
                return False
            evidence = json.loads(row["evidence_json"])
            payload = canonical_json(
                {"run_id": run_id, "seq": row["seq"], "state": row["state"], "evidence": evidence}
            )
            expected = sha256((previous + payload).encode()).hexdigest()
            if row["previous_hash"] != previous or row["event_hash"] != expected:
                return False
            previous = row["event_hash"]
            previous_state = row["state"]
        return bool(rows)


class CapstoneOrchestrator:
    """Exercise identity, authorization, durable state, effect and verifier."""

    def __init__(self, directory: str | Path):
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        self.ledger = CapstoneLedger(directory / "capstone.db")
        self.remote = ExternalEffectLedger(directory / "provider.db")
        self.effects = EffectCoordinator(directory / "effects.db", self.remote)
        self.gateway = CapabilityGateway({"operator": [("ticket.update", "ticket-17")]})

    def close(self) -> None:
        self.effects.close()
        self.remote.close()
        self.ledger.close()

    @staticmethod
    def demonstration_approval(run_id: str) -> dict[str, str]:
        """Local fixture only: not an authenticated human approval service."""
        intent = ToolIntent("ticket.update", "ticket-17", {"status": "resolved"})
        return {"run_id": run_id, "principal": "course-reviewer", "decision": "approve",
                "intent_digest": content_digest(asdict(intent))}

    def run(self, run_id: str, *, approval: Mapping[str, str], lose_ack: bool = False) -> dict[str, Any]:
        intent = ToolIntent("ticket.update", "ticket-17", {"status": "resolved"})
        intent_digest = content_digest(asdict(intent))
        self.ledger.append(run_id, "RECEIVED", {"tenant": "tenant-a"})
        self.ledger.append(run_id, "TRIAGED", {"risk": "write"})
        capability_allowed = self.gateway.check("operator", intent)
        self.ledger.append(run_id, "PLANNED", {"capability_allowed": capability_allowed})
        approval_bound = (
            approval.get("run_id") == run_id
            and approval.get("principal") == "course-reviewer"
            and approval.get("decision") == "approve"
            and approval.get("intent_digest") == intent_digest
        )
        self.ledger.append(run_id, "WAITING_APPROVAL", {"approval_bound": approval_bound,
                                                          "intent_digest": intent_digest})
        if not capability_allowed or not approval_bound:
            raise ValueError("capability or intent-bound approval missing; no effect dispatched")
        self.ledger.append(run_id, "EXECUTING", {"effect_key": f"{run_id}:ticket-17"})
        recovery_used = False
        effect_key = f"{run_id}:ticket-17"
        try:
            receipt = self.effects.execute(effect_key, "ticket.update", 1, lose_ack=lose_ack)
        except EffectOutcomeUnknown:
            recovery_used = True
            self.ledger.append(run_id, "UNKNOWN", {"reason": "response_lost"})
            self.ledger.append(run_id, "RECONCILING", {"lookup": effect_key})
            if self.effects.reconcile(effect_key) != "COMMITTED":
                raise RuntimeError("provider did not prove the effect outcome")
            receipt = self.effects.execute(effect_key, "ticket.update", 1)
        self.ledger.append(run_id, "VERIFYING", {"receipt": receipt, "intent_digest": intent_digest})
        verified = (
            capability_allowed
            and approval_bound
            and self.remote.count(effect_key) == 1
        )
        self.ledger.append(run_id, "COMPLETED" if verified else "QUARANTINED", {"verified": verified})
        return {
            "path": self.ledger.states(run_id),
            "capability_allowed": capability_allowed,
            "approval_bound": approval_bound,
            "effect_count": self.remote.count(effect_key),
            "recovery_used": recovery_used,
            "trace_verified": self.ledger.verify(run_id),
            "verified": verified,
        }
