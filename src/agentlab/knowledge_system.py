"""Deterministic reference mechanisms for Part II of the course.

The module deliberately separates mechanisms that can be proved without a
model provider from provider-dependent quality claims.  It uses no network and
no model-shaped stubs: retrieval, validation, effect reconciliation, temporal
memory and protocol state transitions are executed by inspectable algorithms.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
import math
import re
from typing import Any, Iterable


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode()).hexdigest()


class Risk(str, Enum):
    READ_ONLY = "read_only"
    REVERSIBLE_WRITE = "reversible_write"
    IRREVERSIBLE = "irreversible"


class EffectSemantics(str, Enum):
    PURE = "pure"
    IDEMPOTENT = "idempotent"
    RECONCILABLE = "reconcilable"


@dataclass(frozen=True, slots=True)
class ToolContract:
    name: str
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    risk: Risk
    effect: EffectSemantics
    capabilities: tuple[str, ...]
    result_limit_bytes: int = 4096


def validate_tool_contract(contract: ToolContract) -> tuple[str, ...]:
    """Reject ambiguous or internally inconsistent tool contracts."""

    errors: list[str] = []
    if not re.fullmatch(r"[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*", contract.name):
        errors.append("name_must_be_namespaced")
    lowered = contract.description.lower()
    if len(contract.description.strip()) < 40 or "use when" not in lowered or "do not use" not in lowered:
        errors.append("description_missing_use_and_non_use_boundary")
    if contract.input_schema.get("type") != "object":
        errors.append("input_schema_must_be_object")
    properties = contract.input_schema.get("properties")
    required = contract.input_schema.get("required")
    if not isinstance(properties, dict) or not isinstance(required, list):
        errors.append("input_schema_missing_properties_or_required")
    elif set(required) - set(properties):
        errors.append("required_field_without_schema")
    if contract.output_schema.get("type") != "object":
        errors.append("output_schema_must_be_object")
    if not contract.capabilities or any(cap == "*" for cap in contract.capabilities):
        errors.append("capability_scope_not_least_privilege")
    if contract.risk is Risk.READ_ONLY and contract.effect is not EffectSemantics.PURE:
        errors.append("read_only_tool_cannot_declare_write_effect")
    if contract.risk is Risk.IRREVERSIBLE and contract.effect is EffectSemantics.IDEMPOTENT:
        errors.append("irreversible_effect_requires_reconciliation_contract")
    if contract.result_limit_bytes <= 0:
        errors.append("invalid_result_limit")
    return tuple(errors)


@dataclass(frozen=True, slots=True)
class ArtifactRef:
    artifact_id: str
    sha256: str
    media_type: str
    bytes: int
    preview: str


class ArtifactStore:
    def __init__(self) -> None:
        self._objects: dict[str, bytes] = {}

    def put(self, payload: bytes, *, media_type: str, preview_chars: int = 120) -> ArtifactRef:
        digest = hashlib.sha256(payload).hexdigest()
        artifact_id = f"sha256:{digest}"
        self._objects.setdefault(artifact_id, payload)
        preview = payload.decode("utf-8", errors="replace")[:preview_chars]
        return ArtifactRef(artifact_id, digest, media_type, len(payload), preview)

    def get(self, artifact_id: str) -> bytes:
        return self._objects[artifact_id]


class EffectPhase(str, Enum):
    PREPARED = "PREPARED"
    COMMITTED = "COMMITTED"
    NOT_APPLIED = "NOT_APPLIED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class ActionIntent:
    action_id: str
    tool: str
    args_sha256: str
    idempotency_key: str


@dataclass(frozen=True, slots=True)
class EffectRecord:
    phase: EffectPhase
    action_id: str
    receipt: dict[str, Any] | None = None
    reason: str | None = None


class InMemoryEffectJournal:
    def __init__(self) -> None:
        self._records: list[EffectRecord] = []

    def append(self, record: EffectRecord) -> None:
        current = self.latest(record.action_id)
        allowed = {
            None: {EffectPhase.PREPARED},
            EffectPhase.PREPARED: {EffectPhase.COMMITTED, EffectPhase.NOT_APPLIED, EffectPhase.UNKNOWN},
            EffectPhase.UNKNOWN: {EffectPhase.COMMITTED, EffectPhase.NOT_APPLIED},
        }
        if record.phase not in allowed.get(current.phase if current else None, set()):
            raise ValueError(f"illegal_effect_transition:{current.phase if current else None}->{record.phase}")
        self._records.append(record)

    def latest(self, action_id: str) -> EffectRecord | None:
        return next((record for record in reversed(self._records) if record.action_id == action_id), None)

    @property
    def records(self) -> tuple[EffectRecord, ...]:
        return tuple(self._records)


class SimulatedRemoteLedger:
    """Deterministic external system with a queryable idempotency ledger."""

    def __init__(self) -> None:
        self._effects: dict[str, dict[str, Any]] = {}

    def apply(self, intent: ActionIntent, args: dict[str, Any], *, lose_reply: bool = False) -> dict[str, Any]:
        receipt = self._effects.setdefault(
            intent.idempotency_key,
            {
                "receipt_id": f"rcpt-{len(self._effects) + 1}",
                "idempotency_key": intent.idempotency_key,
                "args_sha256": sha256_json(args),
            },
        )
        if lose_reply:
            raise TimeoutError("reply_lost_after_remote_commit")
        return dict(receipt)

    def lookup(self, idempotency_key: str) -> dict[str, Any] | None:
        receipt = self._effects.get(idempotency_key)
        return dict(receipt) if receipt else None

    @property
    def effect_count(self) -> int:
        return len(self._effects)


class EffectController:
    def __init__(self, journal: InMemoryEffectJournal, remote: SimulatedRemoteLedger) -> None:
        self.journal = journal
        self.remote = remote

    def execute(self, intent: ActionIntent, args: dict[str, Any], *, lose_reply: bool = False) -> EffectRecord:
        if sha256_json(args) != intent.args_sha256:
            raise ValueError("intent_args_digest_mismatch")
        self.journal.append(EffectRecord(EffectPhase.PREPARED, intent.action_id))
        try:
            receipt = self.remote.apply(intent, args, lose_reply=lose_reply)
        except TimeoutError as exc:
            record = EffectRecord(EffectPhase.UNKNOWN, intent.action_id, reason=str(exc))
        else:
            record = EffectRecord(EffectPhase.COMMITTED, intent.action_id, receipt=receipt)
        self.journal.append(record)
        return record

    def reconcile(self, intent: ActionIntent) -> EffectRecord:
        current = self.journal.latest(intent.action_id)
        if current is None or current.phase is not EffectPhase.UNKNOWN:
            raise ValueError("reconcile_requires_unknown")
        receipt = self.remote.lookup(intent.idempotency_key)
        phase = EffectPhase.COMMITTED if receipt else EffectPhase.NOT_APPLIED
        record = EffectRecord(phase, intent.action_id, receipt=receipt, reason="remote_ledger_query")
        self.journal.append(record)
        return record


def tokenize(text: str) -> tuple[str, ...]:
    return tuple(re.findall(r"[a-z0-9_]+|[\u4e00-\u9fff]", text.lower()))


@dataclass(frozen=True, slots=True)
class EvidenceDocument:
    doc_id: str
    tenant_id: str
    text: str
    source_uri: str
    observed_at: str
    authority: int


@dataclass(frozen=True, slots=True)
class SearchHit:
    doc_id: str
    score: float
    source_uri: str
    observed_at: str
    authority: int


@dataclass(frozen=True, slots=True)
class SearchReport:
    hits: tuple[SearchHit, ...]
    excluded: dict[str, str]
    abstained: bool


class BM25Index:
    def __init__(self, documents: Iterable[EvidenceDocument], *, k1: float = 1.5, b: float = 0.75) -> None:
        self.documents = tuple(documents)
        if not self.documents:
            raise ValueError("empty_corpus")
        self.k1, self.b = k1, b
        self.tokens = {doc.doc_id: tokenize(doc.text) for doc in self.documents}
        self.lengths = {doc_id: len(tokens) for doc_id, tokens in self.tokens.items()}
        self.avgdl = sum(self.lengths.values()) / len(self.lengths)
        self.df: Counter[str] = Counter()
        for terms in self.tokens.values():
            self.df.update(set(terms))

    def _score(self, query: tuple[str, ...], doc_id: str) -> float:
        counts = Counter(self.tokens[doc_id])
        n = len(self.documents)
        score = 0.0
        for term in query:
            if not counts[term]:
                continue
            idf = math.log(1.0 + (n - self.df[term] + 0.5) / (self.df[term] + 0.5))
            tf = counts[term]
            denom = tf + self.k1 * (1 - self.b + self.b * self.lengths[doc_id] / self.avgdl)
            score += idf * (tf * (self.k1 + 1)) / denom
        return score

    def search(self, query: str, *, tenant_id: str, k: int = 3, min_score: float = 0.01) -> SearchReport:
        terms = tokenize(query)
        excluded: dict[str, str] = {}
        scored: list[SearchHit] = []
        for doc in self.documents:
            if doc.tenant_id != tenant_id:
                excluded[doc.doc_id] = "tenant_mismatch"
                continue
            score = self._score(terms, doc.doc_id)
            if score < min_score:
                excluded[doc.doc_id] = "below_score_threshold"
                continue
            scored.append(SearchHit(doc.doc_id, round(score, 6), doc.source_uri, doc.observed_at, doc.authority))
        hits = tuple(sorted(scored, key=lambda hit: (-hit.score, -hit.authority, hit.doc_id))[:k])
        return SearchReport(hits, excluded, not hits)


def character_ngrams(text: str, n: int = 3) -> Counter[str]:
    normalized = " ".join(tokenize(text))
    return Counter(normalized[index : index + n] for index in range(max(0, len(normalized) - n + 1)))


def cosine(left: Counter[str], right: Counter[str]) -> float:
    numerator = sum(value * right[key] for key, value in left.items())
    left_norm = math.sqrt(sum(value * value for value in left.values()))
    right_norm = math.sqrt(sum(value * value for value in right.values()))
    return numerator / (left_norm * right_norm) if left_norm and right_norm else 0.0


class CharacterNgramIndex:
    """A deterministic second retriever, explicitly not a neural embedding model."""

    def __init__(self, documents: Iterable[EvidenceDocument]) -> None:
        self.documents = tuple(documents)
        self.vectors = {doc.doc_id: character_ngrams(doc.text) for doc in self.documents}

    def rank(self, query: str, *, tenant_id: str) -> list[str]:
        query_vector = character_ngrams(query)
        scored = [
            (doc.doc_id, cosine(query_vector, self.vectors[doc.doc_id]))
            for doc in self.documents
            if doc.tenant_id == tenant_id
        ]
        return [doc_id for doc_id, score in sorted(scored, key=lambda item: (-item[1], item[0])) if score > 0]


@dataclass(frozen=True, slots=True)
class FusionReport:
    ranking: tuple[tuple[str, float], ...]
    provenance: dict[str, tuple[str, ...]]
    rejected: dict[str, str]


def reciprocal_rank_fusion(
    rankings: dict[str, list[str]], *, allowed_ids: set[str], k: int = 60
) -> FusionReport:
    scores: dict[str, float] = defaultdict(float)
    provenance: dict[str, list[str]] = defaultdict(list)
    rejected: dict[str, str] = {}
    for retriever, ranking in rankings.items():
        seen: set[str] = set()
        for rank, doc_id in enumerate(ranking, 1):
            if doc_id in seen:
                rejected[f"{retriever}:{rank}:{doc_id}"] = "duplicate_in_ranking"
                continue
            seen.add(doc_id)
            if doc_id not in allowed_ids:
                rejected[f"{retriever}:{rank}:{doc_id}"] = "unknown_or_forbidden_document"
                continue
            scores[doc_id] += 1.0 / (k + rank)
            provenance[doc_id].append(retriever)
    ordered = tuple((doc_id, round(score, 8)) for doc_id, score in sorted(scores.items(), key=lambda x: (-x[1], x[0])))
    return FusionReport(ordered, {key: tuple(value) for key, value in provenance.items()}, rejected)


def parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp_requires_timezone")
    return parsed.astimezone(timezone.utc)


@dataclass(frozen=True, slots=True)
class MemoryRecord:
    memory_id: str
    tenant_id: str
    subject: str
    key: str
    value: Any
    source_uri: str
    authority: int
    confidence: float
    valid_from: str
    valid_to: str | None
    recorded_at: str
    supersedes: str | None = None


@dataclass(frozen=True, slots=True)
class MemoryResolution:
    selected: MemoryRecord | None
    candidates: tuple[str, ...]
    quarantined: dict[str, str]


class TemporalMemoryStore:
    def __init__(self) -> None:
        self._records: dict[str, MemoryRecord] = {}

    def append(self, record: MemoryRecord) -> None:
        if record.memory_id in self._records:
            raise ValueError("duplicate_memory_id")
        if not (0.0 <= record.confidence <= 1.0):
            raise ValueError("invalid_confidence")
        parse_utc(record.valid_from)
        parse_utc(record.recorded_at)
        if record.valid_to is not None and parse_utc(record.valid_to) <= parse_utc(record.valid_from):
            raise ValueError("invalid_valid_interval")
        if record.supersedes is not None:
            previous = self._records.get(record.supersedes)
            if previous is None:
                raise ValueError("superseded_memory_missing")
            if (previous.tenant_id, previous.subject, previous.key) != (record.tenant_id, record.subject, record.key):
                raise ValueError("supersedes_scope_mismatch")
        self._records[record.memory_id] = record

    def resolve(self, *, tenant_id: str, subject: str, key: str, at: str) -> MemoryResolution:
        point = parse_utc(at)
        candidates: list[MemoryRecord] = []
        quarantined: dict[str, str] = {}
        for record in self._records.values():
            if record.subject != subject or record.key != key:
                continue
            if record.tenant_id != tenant_id:
                quarantined[record.memory_id] = "tenant_mismatch"
                continue
            start = parse_utc(record.valid_from)
            end = parse_utc(record.valid_to) if record.valid_to else None
            if point < start or (end is not None and point >= end):
                quarantined[record.memory_id] = "outside_valid_time"
                continue
            candidates.append(record)
        ordered = sorted(
            candidates,
            key=lambda record: (-record.authority, -record.confidence, -parse_utc(record.recorded_at).timestamp(), record.memory_id),
        )
        if len(ordered) > 1 and (ordered[0].authority, ordered[0].confidence) == (
            ordered[1].authority,
            ordered[1].confidence,
        ) and ordered[0].value != ordered[1].value:
            quarantined[ordered[0].memory_id] = "unresolved_equal_rank_conflict"
            quarantined[ordered[1].memory_id] = "unresolved_equal_rank_conflict"
            return MemoryResolution(None, tuple(record.memory_id for record in ordered), quarantined)
        return MemoryResolution(ordered[0] if ordered else None, tuple(record.memory_id for record in ordered), quarantined)


@dataclass(frozen=True, slots=True)
class SkillStep:
    step_id: str
    capability: str
    depends_on: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class SkillManifest:
    name: str
    version: str
    source_sha256: str
    steps: tuple[SkillStep, ...]
    declared_capabilities: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CompiledSkill:
    execution_order: tuple[str, ...]
    capability_grant: tuple[str, ...]
    manifest_sha256: str


def compile_skill(manifest: SkillManifest, *, policy_capabilities: set[str]) -> CompiledSkill:
    if not re.fullmatch(r"[a-z][a-z0-9_-]*", manifest.name):
        raise ValueError("invalid_skill_name")
    if not re.fullmatch(r"\d+\.\d+\.\d+", manifest.version):
        raise ValueError("invalid_skill_version")
    if not re.fullmatch(r"[0-9a-f]{64}", manifest.source_sha256):
        raise ValueError("invalid_source_digest")
    declared = set(manifest.declared_capabilities)
    if not declared <= policy_capabilities:
        raise PermissionError(f"capability_escalation:{sorted(declared - policy_capabilities)}")
    by_id = {step.step_id: step for step in manifest.steps}
    if len(by_id) != len(manifest.steps):
        raise ValueError("duplicate_step_id")
    for step in manifest.steps:
        if step.capability not in declared:
            raise ValueError(f"undeclared_step_capability:{step.step_id}")
        if set(step.depends_on) - set(by_id):
            raise ValueError(f"missing_step_dependency:{step.step_id}")
    indegree = {step_id: 0 for step_id in by_id}
    followers: dict[str, list[str]] = defaultdict(list)
    for step in manifest.steps:
        for dependency in step.depends_on:
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
        raise ValueError("skill_dependency_cycle")
    digest_payload = {
        "name": manifest.name,
        "version": manifest.version,
        "source_sha256": manifest.source_sha256,
        "steps": [
            {"step_id": step.step_id, "capability": step.capability, "depends_on": step.depends_on}
            for step in manifest.steps
        ],
        "declared_capabilities": sorted(declared),
    }
    return CompiledSkill(tuple(order), tuple(sorted(declared)), sha256_json(digest_payload))


@dataclass(frozen=True, slots=True)
class InputRequired:
    request_state: str
    input_requests: dict[str, dict[str, Any]]


class MRTRCoordinator:
    """Minimal state-integrity gate for MCP 2026-07-28 MRTR retries."""

    def __init__(self, *, max_rounds: int = 3) -> None:
        self.max_rounds = max_rounds
        self._pending: dict[str, tuple[str, int, frozenset[str]]] = {}

    def require_input(self, request_id: str, fields: dict[str, dict[str, Any]]) -> InputRequired:
        if request_id in self._pending:
            raise ValueError("request_already_pending")
        state = sha256_json({"request_id": request_id, "fields": fields})[:24]
        self._pending[request_id] = (state, 1, frozenset(fields))
        return InputRequired(state, fields)

    def resume(self, request_id: str, *, request_state: str, input_responses: dict[str, Any]) -> dict[str, Any]:
        pending = self._pending.get(request_id)
        if pending is None:
            raise ValueError("no_pending_request")
        expected_state, round_number, required = pending
        if request_state != expected_state:
            raise ValueError("request_state_mismatch")
        if round_number > self.max_rounds:
            raise ValueError("mrtr_round_limit_exceeded")
        if set(input_responses) != set(required):
            raise ValueError("input_response_shape_mismatch")
        del self._pending[request_id]
        return {"resultType": "complete", "requestId": request_id, "acceptedInputs": sorted(input_responses)}
