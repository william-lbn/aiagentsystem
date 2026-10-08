"""Executable assurance mechanisms for Part VI of the course.

The module intentionally uses the Python standard library only.  Its purpose is
not to imitate a hosted agent platform, but to make the hard production
boundaries executable: an evaluator that is independent of agent claims,
benchmark comparability gates, tamper-evident traces, capability authorization,
recovery of externally committed effects, measured latency budgets, and a real
tenant-scoped HTTP API.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import asdict, dataclass
from hashlib import sha256
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from threading import RLock, Thread
from time import perf_counter_ns
from typing import Any, Callable, Iterator, Mapping, Sequence
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import hmac
import json
import re
import sqlite3
import time

from .local_http import LoopbackHTTPServer


def canonical_json(value: Any) -> str:
    """Serialize evidence without host- or insertion-order-dependent bytes."""

    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def content_digest(value: Any) -> str:
    return sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _connect(path: str | Path, *, check_same_thread: bool = True) -> sqlite3.Connection:
    db = sqlite3.connect(str(path), timeout=5.0, check_same_thread=check_same_thread)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    db.execute("PRAGMA journal_mode = WAL")
    db.execute("PRAGMA synchronous = FULL")
    return db


# ---------------------------------------------------------------------------
# Chapter 29: evaluation as an independent, durable release gate


@dataclass(frozen=True)
class EvaluationTask:
    task_id: str
    version: str
    expected_answer: str
    allowed_effects: tuple[str, ...]
    max_steps: int

    @property
    def digest(self) -> str:
        return content_digest(asdict(self))


@dataclass(frozen=True)
class EvaluationVerdict:
    run_id: str
    task_digest: str
    checks: Mapping[str, bool]
    passed: bool
    promotion_status: str


class EvaluationLedger:
    """Durably separates an agent's claim from an evaluator's verdict."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.db = _connect(self.path)
        self.db.executescript(
            """
            CREATE TABLE IF NOT EXISTS tasks(
                task_id TEXT NOT NULL,
                version TEXT NOT NULL,
                digest TEXT NOT NULL UNIQUE,
                spec_json TEXT NOT NULL,
                PRIMARY KEY(task_id, version)
            );
            CREATE TABLE IF NOT EXISTS runs(
                run_id TEXT PRIMARY KEY,
                task_digest TEXT NOT NULL REFERENCES tasks(digest),
                agent_claim TEXT,
                final_answer TEXT,
                effects_json TEXT NOT NULL DEFAULT '[]',
                step_count INTEGER NOT NULL DEFAULT 0,
                state TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS observations(
                run_id TEXT NOT NULL REFERENCES runs(run_id),
                seq INTEGER NOT NULL,
                kind TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                PRIMARY KEY(run_id, seq)
            );
            CREATE TABLE IF NOT EXISTS verdicts(
                run_id TEXT PRIMARY KEY REFERENCES runs(run_id),
                verdict_json TEXT NOT NULL
            );
            """
        )
        self.db.commit()

    def close(self) -> None:
        self.db.close()

    def register(self, task: EvaluationTask) -> str:
        payload = canonical_json(asdict(task))
        with self.db:
            self.db.execute(
                "INSERT OR REPLACE INTO tasks(task_id, version, digest, spec_json) VALUES(?,?,?,?)",
                (task.task_id, task.version, task.digest, payload),
            )
        return task.digest

    def begin(self, run_id: str, task_digest: str) -> None:
        with self.db:
            self.db.execute(
                "INSERT INTO runs(run_id, task_digest, state) VALUES(?,?,?)",
                (run_id, task_digest, "RUNNING"),
            )

    def observe(self, run_id: str, kind: str, payload: Mapping[str, Any]) -> None:
        row = self.db.execute(
            "SELECT COALESCE(MAX(seq), 0) + 1 AS next_seq FROM observations WHERE run_id=?",
            (run_id,),
        ).fetchone()
        with self.db:
            self.db.execute(
                "INSERT INTO observations(run_id, seq, kind, payload_json) VALUES(?,?,?,?)",
                (run_id, int(row["next_seq"]), kind, canonical_json(payload)),
            )

    def finish(
        self,
        run_id: str,
        *,
        agent_claim: str,
        final_answer: str,
        observed_effects: Sequence[str],
        step_count: int,
    ) -> None:
        with self.db:
            self.db.execute(
                """UPDATE runs
                   SET agent_claim=?, final_answer=?, effects_json=?, step_count=?, state='AWAITING_VERIFICATION'
                   WHERE run_id=? AND state='RUNNING'""",
                (agent_claim, final_answer, canonical_json(list(observed_effects)), step_count, run_id),
            )
            if self.db.execute("SELECT changes()").fetchone()[0] != 1:
                raise ValueError("run is missing or not RUNNING")

    def verify(self, run_id: str) -> EvaluationVerdict:
        row = self.db.execute(
            """SELECT r.*, t.spec_json
               FROM runs r JOIN tasks t ON t.digest=r.task_digest WHERE r.run_id=?""",
            (run_id,),
        ).fetchone()
        if row is None or row["state"] != "AWAITING_VERIFICATION":
            raise ValueError("run is not ready for independent verification")
        spec = json.loads(row["spec_json"])
        effects = json.loads(row["effects_json"])
        checks = {
            "answer": hmac.compare_digest(row["final_answer"], spec["expected_answer"]),
            "effects": set(effects).issubset(set(spec["allowed_effects"])),
            "budget": 0 <= row["step_count"] <= spec["max_steps"],
            "trajectory_present": self.db.execute(
                "SELECT COUNT(*) FROM observations WHERE run_id=?", (run_id,)
            ).fetchone()[0]
            > 0,
        }
        passed = all(checks.values())
        verdict = EvaluationVerdict(
            run_id=run_id,
            task_digest=row["task_digest"],
            checks=checks,
            passed=passed,
            promotion_status="ELIGIBLE" if passed else "QUARANTINED",
        )
        with self.db:
            self.db.execute(
                "INSERT INTO verdicts(run_id, verdict_json) VALUES(?,?)",
                (run_id, canonical_json(asdict(verdict))),
            )
            self.db.execute(
                "UPDATE runs SET state=? WHERE run_id=?",
                (verdict.promotion_status, run_id),
            )
        return verdict


# ---------------------------------------------------------------------------
# Chapter 30: benchmark identity and statistical reporting


@dataclass(frozen=True)
class BenchmarkManifest:
    benchmark: str
    task_set_digest: str
    environment_digest: str
    verifier_digest: str
    harness_revision: str
    seed: int

    @property
    def digest(self) -> str:
        return content_digest(asdict(self))


@dataclass(frozen=True)
class ComparabilityDecision:
    comparable: bool
    mismatches: tuple[str, ...]
    aggregate_allowed: bool


def compare_manifests(left: BenchmarkManifest, right: BenchmarkManifest) -> ComparabilityDecision:
    controlled = (
        "benchmark",
        "task_set_digest",
        "environment_digest",
        "verifier_digest",
        "harness_revision",
        "seed",
    )
    mismatches = tuple(field for field in controlled if getattr(left, field) != getattr(right, field))
    return ComparabilityDecision(not mismatches, mismatches, not mismatches)


def wilson_interval(successes: int, total: int, z: float = 1.96) -> tuple[float, float]:
    if total <= 0 or not 0 <= successes <= total:
        raise ValueError("successes/total must describe a non-empty binomial sample")
    p = successes / total
    denominator = 1 + z * z / total
    centre = (p + z * z / (2 * total)) / denominator
    margin = z * ((p * (1 - p) / total + z * z / (4 * total * total)) ** 0.5) / denominator
    return centre - margin, centre + margin


def benchmark_report(manifest: BenchmarkManifest, outcomes: Sequence[bool]) -> dict[str, Any]:
    if not outcomes:
        raise ValueError("a benchmark report needs at least one independently verified task")
    successes = sum(outcomes)
    low, high = wilson_interval(successes, len(outcomes))
    return {
        "manifest_digest": manifest.digest,
        "successes": successes,
        "tasks": len(outcomes),
        "accuracy": round(successes / len(outcomes), 4),
        "wilson_95": [round(low, 4), round(high, 4)],
    }


# ---------------------------------------------------------------------------
# Chapter 31: reconstructable and tamper-evident trajectories


_SENSITIVE_KEY = re.compile(r"(?:api[_-]?key|authorization|password|secret|token)", re.IGNORECASE)


def redact(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(k): "[REDACTED]" if _SENSITIVE_KEY.search(str(k)) else redact(v) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v) for v in value]
    if isinstance(value, tuple):
        return [redact(v) for v in value]
    return value


class TamperEvidentTraceStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.db = _connect(self.path)
        self.db.executescript(
            """
            CREATE TABLE IF NOT EXISTS spans(
                run_id TEXT NOT NULL,
                seq INTEGER NOT NULL,
                span_id TEXT NOT NULL,
                parent_id TEXT,
                name TEXT NOT NULL,
                duration_ns INTEGER NOT NULL,
                attrs_json TEXT NOT NULL,
                prev_hash TEXT NOT NULL,
                row_hash TEXT NOT NULL,
                PRIMARY KEY(run_id, seq),
                UNIQUE(run_id, span_id)
            );
            """
        )
        self.db.commit()

    def close(self) -> None:
        self.db.close()

    def record(
        self,
        *,
        run_id: str,
        span_id: str,
        parent_id: str | None,
        name: str,
        operation: Callable[[], Any],
        attrs: Mapping[str, Any] | None = None,
    ) -> Any:
        if not run_id or not span_id or not name:
            raise ValueError("run_id, span_id and name are mandatory correlation fields")
        if parent_id is not None:
            exists = self.db.execute(
                "SELECT 1 FROM spans WHERE run_id=? AND span_id=?", (run_id, parent_id)
            ).fetchone()
            if exists is None:
                raise ValueError("parent span must already exist in the same run")
        head = self.db.execute(
            "SELECT seq, row_hash FROM spans WHERE run_id=? ORDER BY seq DESC LIMIT 1", (run_id,)
        ).fetchone()
        seq = 1 if head is None else int(head["seq"]) + 1
        previous = "GENESIS" if head is None else head["row_hash"]
        started = perf_counter_ns()
        try:
            result = operation()
        finally:
            duration = max(0, perf_counter_ns() - started)
            payload = {
                "run_id": run_id,
                "seq": seq,
                "span_id": span_id,
                "parent_id": parent_id,
                "name": name,
                "duration_ns": duration,
                "attrs": redact(dict(attrs or {})),
                "prev_hash": previous,
            }
            digest = content_digest(payload)
            with self.db:
                self.db.execute(
                    """INSERT INTO spans
                       (run_id,seq,span_id,parent_id,name,duration_ns,attrs_json,prev_hash,row_hash)
                       VALUES(?,?,?,?,?,?,?,?,?)""",
                    (
                        run_id,
                        seq,
                        span_id,
                        parent_id,
                        name,
                        duration,
                        canonical_json(payload["attrs"]),
                        previous,
                        digest,
                    ),
                )
        return result

    def verify(self, run_id: str) -> tuple[bool, str]:
        rows = self.db.execute("SELECT * FROM spans WHERE run_id=? ORDER BY seq", (run_id,)).fetchall()
        if not rows:
            return False, "EMPTY_TRACE"
        previous = "GENESIS"
        seen: set[str] = set()
        for expected_seq, row in enumerate(rows, 1):
            if row["seq"] != expected_seq or row["prev_hash"] != previous:
                return False, "CHAIN_DISCONTINUITY"
            if row["parent_id"] is not None and row["parent_id"] not in seen:
                return False, "INVALID_PARENT"
            payload = {
                "run_id": row["run_id"],
                "seq": row["seq"],
                "span_id": row["span_id"],
                "parent_id": row["parent_id"],
                "name": row["name"],
                "duration_ns": row["duration_ns"],
                "attrs": json.loads(row["attrs_json"]),
                "prev_hash": row["prev_hash"],
            }
            if not hmac.compare_digest(content_digest(payload), row["row_hash"]):
                return False, "HASH_MISMATCH"
            seen.add(row["span_id"])
            previous = row["row_hash"]
        return True, "VERIFIED"

    def reconstruct(self, run_id: str) -> list[dict[str, Any]]:
        ok, reason = self.verify(run_id)
        if not ok:
            raise ValueError(f"trace export blocked: {reason}")
        return [
            {
                "seq": row["seq"],
                "span_id": row["span_id"],
                "parent_id": row["parent_id"],
                "name": row["name"],
                "attrs": json.loads(row["attrs_json"]),
            }
            for row in self.db.execute("SELECT * FROM spans WHERE run_id=? ORDER BY seq", (run_id,))
        ]


# ---------------------------------------------------------------------------
# Chapter 32: typed trust boundaries plus capability authorization


@dataclass(frozen=True)
class ContentEnvelope:
    source: str
    trust: str
    media_type: str
    text: str

    def __post_init__(self) -> None:
        if self.trust not in {"TRUSTED_INSTRUCTION", "UNTRUSTED_DATA"}:
            raise ValueError("content must have an explicit trust label")


@dataclass(frozen=True)
class ToolIntent:
    tool: str
    resource: str
    arguments: Mapping[str, Any]


@dataclass(frozen=True)
class AuthorizationDecision:
    allowed: bool
    reason: str
    effect_committed: bool


class CapabilityGateway:
    """Authorize effects from grants, never from retrieved content text."""

    def __init__(self, grants: Mapping[str, Sequence[tuple[str, str]]]):
        self.grants = {principal: frozenset(items) for principal, items in grants.items()}
        self.audit: list[dict[str, Any]] = []
        self.effects: list[dict[str, Any]] = []

    @staticmethod
    def assemble_context(instruction: ContentEnvelope, data: Sequence[ContentEnvelope]) -> list[dict[str, str]]:
        if instruction.trust != "TRUSTED_INSTRUCTION":
            raise ValueError("the instruction channel must be trusted")
        if any(item.trust != "UNTRUSTED_DATA" for item in data):
            raise ValueError("retrieved/tool content must remain in the data channel")
        return [
            {"channel": "instruction", "source": instruction.source, "text": instruction.text},
            *({"channel": "data", "source": item.source, "text": item.text} for item in data),
        ]

    def authorize(self, principal: str, intent: ToolIntent) -> AuthorizationDecision:
        allowed = (intent.tool, intent.resource) in self.grants.get(principal, frozenset())
        decision = AuthorizationDecision(
            allowed=allowed,
            reason="CAPABILITY_MATCH" if allowed else "CAPABILITY_DENIED",
            effect_committed=allowed,
        )
        audit_record = {
            "principal": principal,
            "tool": intent.tool,
            "resource": intent.resource,
            "arguments": redact(dict(intent.arguments)),
            "decision": decision.reason,
        }
        self.audit.append(audit_record)
        if allowed:
            self.effects.append(audit_record)
        return decision

    def check(self, principal: str, intent: ToolIntent) -> bool:
        """Pure capability preflight; it must not record a committed effect."""
        return (intent.tool, intent.resource) in self.grants.get(principal, frozenset())


# ---------------------------------------------------------------------------
# Chapter 33: uncertain external effects and recovery by observation


class EffectOutcomeUnknown(RuntimeError):
    pass


class ExternalEffectLedger:
    """A separately durable stand-in for a payment/message provider."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.db = _connect(self.path)
        self.db.execute(
            """CREATE TABLE IF NOT EXISTS effects(
                   idempotency_key TEXT PRIMARY KEY,
                   operation TEXT NOT NULL,
                   amount INTEGER NOT NULL,
                   receipt TEXT NOT NULL
               )"""
        )
        self.db.commit()

    def close(self) -> None:
        self.db.close()

    def apply(self, key: str, operation: str, amount: int) -> str:
        receipt = "rcpt_" + content_digest({"key": key, "operation": operation, "amount": amount})[:16]
        with self.db:
            self.db.execute(
                "INSERT OR IGNORE INTO effects(idempotency_key,operation,amount,receipt) VALUES(?,?,?,?)",
                (key, operation, amount, receipt),
            )
        row = self.db.execute(
            "SELECT operation,amount,receipt FROM effects WHERE idempotency_key=?", (key,)
        ).fetchone()
        if row["operation"] != operation or row["amount"] != amount:
            raise ValueError("idempotency key reused with a different effect")
        return str(row["receipt"])

    def lookup(self, key: str) -> str | None:
        row = self.db.execute("SELECT receipt FROM effects WHERE idempotency_key=?", (key,)).fetchone()
        return None if row is None else str(row["receipt"])

    def count(self, key: str) -> int:
        return int(self.db.execute("SELECT COUNT(*) FROM effects WHERE idempotency_key=?", (key,)).fetchone()[0])


class EffectCoordinator:
    def __init__(self, local_path: str | Path, remote: ExternalEffectLedger):
        self.path = Path(local_path)
        self.remote = remote
        self.db = _connect(self.path)
        self.db.execute(
            """CREATE TABLE IF NOT EXISTS intents(
                   idempotency_key TEXT PRIMARY KEY,
                   operation TEXT NOT NULL,
                   amount INTEGER NOT NULL,
                   status TEXT NOT NULL,
                   receipt TEXT
               )"""
        )
        self.db.commit()

    def close(self) -> None:
        self.db.close()

    def execute(self, key: str, operation: str, amount: int, *, lose_ack: bool = False) -> str:
        with self.db:
            self.db.execute(
                "INSERT OR IGNORE INTO intents(idempotency_key,operation,amount,status) VALUES(?,?,?,'PREPARED')",
                (key, operation, amount),
            )
        intent = self.db.execute("SELECT * FROM intents WHERE idempotency_key=?", (key,)).fetchone()
        if intent["operation"] != operation or intent["amount"] != amount:
            raise ValueError("idempotency key reused with different local intent")
        if intent["status"] == "COMMITTED":
            return str(intent["receipt"])
        receipt = self.remote.apply(key, operation, amount)
        if lose_ack:
            with self.db:
                self.db.execute("UPDATE intents SET status='UNKNOWN' WHERE idempotency_key=?", (key,))
            raise EffectOutcomeUnknown("remote commit may have succeeded; retry is unsafe until reconciliation")
        with self.db:
            self.db.execute(
                "UPDATE intents SET status='COMMITTED', receipt=? WHERE idempotency_key=?", (receipt, key)
            )
        return receipt

    def reconcile(self, key: str) -> str:
        intent = self.db.execute("SELECT * FROM intents WHERE idempotency_key=?", (key,)).fetchone()
        if intent is None:
            raise KeyError(key)
        receipt = self.remote.lookup(key)
        if receipt is None:
            with self.db:
                self.db.execute("UPDATE intents SET status='NOT_COMMITTED' WHERE idempotency_key=?", (key,))
            return "NOT_COMMITTED"
        with self.db:
            self.db.execute(
                "UPDATE intents SET status='COMMITTED', receipt=? WHERE idempotency_key=?", (receipt, key)
            )
        return "COMMITTED"

    def status(self, key: str) -> str:
        row = self.db.execute("SELECT status FROM intents WHERE idempotency_key=?", (key,)).fetchone()
        if row is None:
            raise KeyError(key)
        return str(row["status"])


# ---------------------------------------------------------------------------
# Chapter 34: measured critical paths and enforceable budgets


@dataclass(frozen=True)
class StageMeasurement:
    stage: str
    elapsed_ms: float
    budget_ms: float
    within_budget: bool


@dataclass(frozen=True)
class PerformanceReport:
    stages: tuple[StageMeasurement, ...]
    total_ms: float
    total_budget_ms: float
    within_budget: bool
    release_allowed: bool


class PerformanceProbe:
    def __init__(self, stage_budgets_ms: Mapping[str, float], total_budget_ms: float):
        if total_budget_ms <= 0 or any(value <= 0 for value in stage_budgets_ms.values()):
            raise ValueError("performance budgets must be positive")
        self.stage_budgets_ms = dict(stage_budgets_ms)
        self.total_budget_ms = total_budget_ms

    def measure(self, operations: Sequence[tuple[str, Callable[[], Any]]]) -> PerformanceReport:
        measurements: list[StageMeasurement] = []
        total_started = perf_counter_ns()
        for name, operation in operations:
            if name not in self.stage_budgets_ms:
                raise ValueError(f"missing stage budget: {name}")
            started = perf_counter_ns()
            operation()
            elapsed_ms = (perf_counter_ns() - started) / 1_000_000
            budget = self.stage_budgets_ms[name]
            measurements.append(StageMeasurement(name, round(elapsed_ms, 3), budget, elapsed_ms <= budget))
        total_ms = (perf_counter_ns() - total_started) / 1_000_000
        within = total_ms <= self.total_budget_ms and all(item.within_budget for item in measurements)
        return PerformanceReport(
            stages=tuple(measurements),
            total_ms=round(total_ms, 3),
            total_budget_ms=self.total_budget_ms,
            within_budget=within,
            release_allowed=within,
        )


# ---------------------------------------------------------------------------
# Chapter 35: a real loopback HTTP boundary with tenant isolation


class TenantAuthenticator:
    def __init__(self, signing_key: bytes):
        if len(signing_key) < 16:
            raise ValueError("the teaching signer still requires at least 128 bits")
        self.signing_key = signing_key

    def issue(self, tenant: str) -> str:
        if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,62}", tenant):
            raise ValueError("invalid tenant identifier")
        signature = hmac.new(self.signing_key, tenant.encode(), sha256).hexdigest()
        return f"{tenant}.{signature}"

    def verify(self, token: str) -> str | None:
        tenant, separator, signature = token.partition(".")
        if not separator:
            return None
        expected = hmac.new(self.signing_key, tenant.encode(), sha256).hexdigest()
        return tenant if hmac.compare_digest(signature, expected) else None


class ProductionRunStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.db = _connect(self.path, check_same_thread=False)
        self.lock = RLock()
        self.db.execute(
            """CREATE TABLE IF NOT EXISTS runs(
                   tenant TEXT NOT NULL,
                   run_id TEXT NOT NULL,
                   idempotency_key TEXT NOT NULL,
                   request_digest TEXT NOT NULL,
                   request_json TEXT NOT NULL,
                   state TEXT NOT NULL,
                   PRIMARY KEY(tenant,run_id),
                   UNIQUE(tenant,idempotency_key)
               )"""
        )
        self.db.commit()

    def close(self) -> None:
        with self.lock:
            self.db.close()

    def create(self, tenant: str, idempotency_key: str, payload: Mapping[str, Any]) -> tuple[dict[str, Any], bool]:
        if not idempotency_key or len(idempotency_key) > 128:
            raise ValueError("a bounded idempotency key is required")
        digest = content_digest(payload)
        run_id = "run_" + content_digest({"tenant": tenant, "key": idempotency_key})[:16]
        with self.lock, self.db:
            self.db.execute(
                """INSERT OR IGNORE INTO runs
                   (tenant,run_id,idempotency_key,request_digest,request_json,state)
                   VALUES(?,?,?,?,?,'ACCEPTED')""",
                (tenant, run_id, idempotency_key, digest, canonical_json(payload)),
            )
            row = self.db.execute(
                "SELECT * FROM runs WHERE tenant=? AND idempotency_key=?", (tenant, idempotency_key)
            ).fetchone()
        if row["request_digest"] != digest:
            raise ValueError("idempotency key conflict")
        record = {"run_id": row["run_id"], "state": row["state"]}
        return record, row["run_id"] == run_id

    def get(self, tenant: str, run_id: str) -> dict[str, Any] | None:
        with self.lock:
            row = self.db.execute(
                "SELECT run_id,state FROM runs WHERE tenant=? AND run_id=?", (tenant, run_id)
            ).fetchone()
        return None if row is None else {"run_id": row["run_id"], "state": row["state"]}


class AgentHTTPService:
    def __init__(self, store: ProductionRunStore, authenticator: TenantAuthenticator):
        self.store = store
        self.authenticator = authenticator
        service = self

        class Handler(BaseHTTPRequestHandler):
            server_version = "AgentLab/1.0"

            def log_message(self, _format: str, *args: Any) -> None:
                return

            def _json(self, status: int, payload: Mapping[str, Any]) -> None:
                body = canonical_json(payload).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(body)

            def _tenant(self) -> str | None:
                scheme, _, token = self.headers.get("Authorization", "").partition(" ")
                if scheme != "Bearer":
                    return None
                return service.authenticator.verify(token)

            def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
                tenant = self._tenant()
                if tenant is None:
                    self._json(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
                    return
                if self.path != "/v1/runs":
                    self._json(HTTPStatus.NOT_FOUND, {"error": "not_found"})
                    return
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                    if length <= 0 or length > 16_384:
                        raise ValueError("invalid body length")
                    payload = json.loads(self.rfile.read(length))
                    if not isinstance(payload, dict):
                        raise ValueError("request must be an object")
                    record, _ = service.store.create(
                        tenant, self.headers.get("Idempotency-Key", ""), payload
                    )
                except json.JSONDecodeError:
                    self._json(HTTPStatus.BAD_REQUEST, {"error": "invalid_json"})
                    return
                except ValueError as exc:
                    status = HTTPStatus.CONFLICT if "conflict" in str(exc) else HTTPStatus.BAD_REQUEST
                    self._json(status, {"error": str(exc)})
                    return
                self._json(HTTPStatus.ACCEPTED, record)

            def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
                tenant = self._tenant()
                if tenant is None:
                    self._json(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
                    return
                match = re.fullmatch(r"/v1/runs/(run_[0-9a-f]{16})", self.path)
                if match is None:
                    self._json(HTTPStatus.NOT_FOUND, {"error": "not_found"})
                    return
                record = service.store.get(tenant, match.group(1))
                # The same response is used for absent and foreign resources.
                self._json(HTTPStatus.OK, record) if record else self._json(
                    HTTPStatus.NOT_FOUND, {"error": "not_found"}
                )

        self.server = LoopbackHTTPServer(("127.0.0.1", 0), Handler)
        self.thread: Thread | None = None

    @property
    def base_url(self) -> str:
        host, port = self.server.server_address
        return f"http://{host}:{port}"

    def start(self) -> None:
        if self.thread is not None:
            raise RuntimeError("service already started")
        self.thread = Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def close(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        if self.thread is not None:
            self.thread.join(timeout=3)

    def __enter__(self) -> "AgentHTTPService":
        self.start()
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()


def http_json(
    method: str,
    url: str,
    *,
    token: str,
    payload: Mapping[str, Any] | None = None,
    idempotency_key: str | None = None,
) -> tuple[int, dict[str, Any]]:
    data = None if payload is None else canonical_json(payload).encode()
    headers = {"Authorization": f"Bearer {token}"}
    if payload is not None:
        headers["Content-Type"] = "application/json"
    if idempotency_key is not None:
        headers["Idempotency-Key"] = idempotency_key
    request = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(request, timeout=3) as response:  # noqa: S310 - fixed loopback URL in course labs
            return response.status, json.loads(response.read())
    except HTTPError as exc:
        try:
            return exc.code, json.loads(exc.read())
        finally:
            exc.close()


@contextmanager
def running_agent_service(
    path: str | Path, signing_key: bytes = b"agentlab-teaching-key-2026"
) -> Iterator[tuple[AgentHTTPService, TenantAuthenticator, ProductionRunStore]]:
    store = ProductionRunStore(path)
    try:
        authenticator = TenantAuthenticator(signing_key)
        # Construct inside the protected region: binding the loopback socket can
        # fail (sandbox policy, exhausted descriptors, address-family policy).
        # The durable store must still be closed on that pre-yield path.
        service = AgentHTTPService(store, authenticator)
        with service:
            yield service, authenticator, store
    finally:
        store.close()


def measured_delay(seconds: float) -> None:
    """A named helper makes deliberate latency injection visible in labs."""

    time.sleep(seconds)
