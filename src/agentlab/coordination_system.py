"""Executable coordination mechanisms for Part V.

The module keeps protocol interoperability separate from authorization and
orchestration.  It uses canonical JSON, HMAC-bound delegation grants and real
SQLite transactions so the labs can test durable ownership, least privilege,
budget reservation, dependency joins and effect idempotency without pretending
that a language model or a remote service was exercised.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable
import hashlib
import hmac
import json
import sqlite3


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


class DelegationRejected(ValueError):
    """Raised before a delegated task is persisted or executed."""


@dataclass(frozen=True, slots=True)
class DelegationGrant:
    principal: str
    delegate: str
    task_id: str
    scopes: tuple[str, ...]
    issued_at: int
    expires_at: int
    nonce: str
    signature: str

    def signed_payload(self) -> dict[str, Any]:
        value = asdict(self)
        value.pop("signature")
        value["scopes"] = list(self.scopes)
        return value

    def to_wire(self) -> dict[str, Any]:
        return {**self.signed_payload(), "signature": self.signature}


class DelegationAuthority:
    """Issue and verify task-bound, time-bounded capability grants.

    HMAC is used only as a deterministic course mechanism.  A deployment would
    normally use an identity provider, asymmetric signatures, key rotation and
    a revocation service; A2A transport reachability does not supply those.
    """

    def __init__(self, secret: bytes):
        if len(secret) < 16:
            raise ValueError("delegation_secret_too_short")
        self._secret = secret

    def _sign(self, payload: dict[str, Any]) -> str:
        return hmac.new(self._secret, _canonical(payload), hashlib.sha256).hexdigest()

    def issue(
        self,
        *,
        principal: str,
        delegate: str,
        task_id: str,
        scopes: Iterable[str],
        issued_at: int,
        expires_at: int,
        nonce: str,
    ) -> DelegationGrant:
        normalized_scopes = tuple(sorted(set(scopes)))
        if expires_at <= issued_at:
            raise ValueError("delegation_expiry_invalid")
        unsigned = {
            "principal": principal,
            "delegate": delegate,
            "task_id": task_id,
            "scopes": list(normalized_scopes),
            "issued_at": issued_at,
            "expires_at": expires_at,
            "nonce": nonce,
        }
        return DelegationGrant(
            principal,
            delegate,
            task_id,
            normalized_scopes,
            issued_at,
            expires_at,
            nonce,
            self._sign(unsigned),
        )

    def verify(
        self,
        grant: DelegationGrant,
        *,
        delegate: str,
        task_id: str,
        required_scope: str,
        now: int,
    ) -> None:
        expected = self._sign(grant.signed_payload())
        if not hmac.compare_digest(expected, grant.signature):
            raise DelegationRejected("delegation_signature_invalid")
        if grant.delegate != delegate:
            raise DelegationRejected("delegation_delegate_mismatch")
        if grant.task_id != task_id:
            raise DelegationRejected("delegation_task_mismatch")
        if required_scope not in grant.scopes:
            raise DelegationRejected("delegation_scope_missing")
        if now < grant.issued_at or now >= grant.expires_at:
            raise DelegationRejected("delegation_expired_or_not_yet_valid")


class A2ATaskLedger:
    """Durable A2A task/evidence boundary with authorization before insert."""

    _TRANSITIONS = {
        "TASK_STATE_SUBMITTED": frozenset({"TASK_STATE_WORKING", "TASK_STATE_CANCELED"}),
        "TASK_STATE_WORKING": frozenset(
            {"TASK_STATE_COMPLETED", "TASK_STATE_FAILED", "TASK_STATE_CANCELED"}
        ),
    }

    def __init__(self, path: Path, authority: DelegationAuthority):
        self.connection = sqlite3.connect(path)
        self.connection.row_factory = sqlite3.Row
        self.authority = authority
        self.connection.executescript(
            """
            create table if not exists a2a_tasks(
              task_id text primary key,
              context_id text not null,
              principal text not null,
              delegate text not null,
              required_scope text not null,
              state text not null,
              version integer not null,
              idempotency_key text not null unique,
              delegation_nonce text not null unique,
              artifact_digest text,
              artifact_json text
            );
            create table if not exists a2a_events(
              task_id text not null,
              sequence integer not null,
              event_type text not null,
              payload_json text not null,
              primary key(task_id, sequence)
            );
            """
        )

    def close(self) -> None:
        self.connection.close()

    def _event(self, task_id: str, event_type: str, payload: dict[str, Any]) -> None:
        sequence = int(
            self.connection.execute(
                "select coalesce(max(sequence),0)+1 from a2a_events where task_id=?", (task_id,)
            ).fetchone()[0]
        )
        self.connection.execute(
            "insert into a2a_events values(?,?,?,?)",
            (task_id, sequence, event_type, _canonical(payload).decode()),
        )

    def submit(
        self,
        *,
        task_id: str,
        context_id: str,
        delegate: str,
        required_scope: str,
        idempotency_key: str,
        grant: DelegationGrant,
        now: int,
    ) -> dict[str, Any]:
        self.authority.verify(
            grant,
            delegate=delegate,
            task_id=task_id,
            required_scope=required_scope,
            now=now,
        )
        existing = self.connection.execute(
            "select task_id from a2a_tasks where idempotency_key=?", (idempotency_key,)
        ).fetchone()
        if existing is not None:
            if existing["task_id"] != task_id:
                raise DelegationRejected("idempotency_key_conflict")
            return self.snapshot(task_id)
        try:
            self.connection.execute("begin immediate")
            self.connection.execute(
                "insert into a2a_tasks values(?,?,?,?,?,?,?,?,?,?,?)",
                (
                    task_id,
                    context_id,
                    grant.principal,
                    delegate,
                    required_scope,
                    "TASK_STATE_SUBMITTED",
                    1,
                    idempotency_key,
                    grant.nonce,
                    None,
                    None,
                ),
            )
            self._event(task_id, "task.submitted", {"context_id": context_id})
            self.connection.commit()
        except sqlite3.IntegrityError as exc:
            self.connection.rollback()
            raise DelegationRejected("delegation_nonce_or_identity_reused") from exc
        return self.snapshot(task_id)

    def transition(self, task_id: str, *, expected_version: int, target: str) -> dict[str, Any]:
        row = self.connection.execute(
            "select state,version from a2a_tasks where task_id=?", (task_id,)
        ).fetchone()
        if row is None:
            raise DelegationRejected("task_missing")
        if row["version"] != expected_version:
            raise DelegationRejected("task_version_conflict")
        if target not in self._TRANSITIONS.get(row["state"], frozenset()):
            raise DelegationRejected("task_transition_invalid")
        self.connection.execute(
            "update a2a_tasks set state=?,version=version+1 where task_id=? and version=?",
            (target, task_id, expected_version),
        )
        self._event(task_id, "task.status", {"state": target})
        self.connection.commit()
        return self.snapshot(task_id)

    def complete(
        self, task_id: str, *, expected_version: int, artifact: dict[str, Any]
    ) -> dict[str, Any]:
        row = self.connection.execute(
            "select state,version from a2a_tasks where task_id=?", (task_id,)
        ).fetchone()
        if row is None or row["state"] != "TASK_STATE_WORKING":
            raise DelegationRejected("task_not_working")
        if row["version"] != expected_version:
            raise DelegationRejected("task_version_conflict")
        digest = _digest(artifact)
        self.connection.execute(
            "update a2a_tasks set state='TASK_STATE_COMPLETED',version=version+1,"
            "artifact_digest=?,artifact_json=? where task_id=? and version=?",
            (digest, _canonical(artifact).decode(), task_id, expected_version),
        )
        self._event(task_id, "task.artifact", {"sha256": digest})
        self._event(task_id, "task.status", {"state": "TASK_STATE_COMPLETED"})
        self.connection.commit()
        return self.snapshot(task_id)

    def snapshot(self, task_id: str) -> dict[str, Any]:
        row = self.connection.execute(
            "select * from a2a_tasks where task_id=?", (task_id,)
        ).fetchone()
        if row is None:
            raise DelegationRejected("task_missing")
        return {
            "task_id": row["task_id"],
            "context_id": row["context_id"],
            "delegate": row["delegate"],
            "state": row["state"],
            "version": row["version"],
            "artifact_digest": row["artifact_digest"],
        }

    def events(self, task_id: str) -> tuple[str, ...]:
        rows = self.connection.execute(
            "select event_type from a2a_events where task_id=? order by sequence", (task_id,)
        ).fetchall()
        return tuple(row["event_type"] for row in rows)

    def task_count(self) -> int:
        return int(self.connection.execute("select count(*) from a2a_tasks").fetchone()[0])


class CoordinationRejected(ValueError):
    """Raised when ownership, scope, dependency or budget checks fail closed."""


@dataclass(frozen=True, slots=True)
class WorkOrder:
    task_id: str
    owner: str
    required_scope: str
    max_cost: int
    input_refs: tuple[str, ...]
    depends_on: tuple[str, ...] = ()


class MultiAgentCoordinator:
    """SQLite-backed scheduler for explicit ownership and bounded fan-out."""

    def __init__(self, path: Path):
        self.connection = sqlite3.connect(path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("pragma foreign_keys=on")
        self.connection.executescript(
            """
            create table if not exists coordination_runs(
              run_id text primary key,
              budget_limit integer not null,
              budget_reserved integer not null default 0,
              status text not null
            );
            create table if not exists work_orders(
              run_id text not null references coordination_runs(run_id),
              task_id text not null,
              owner text not null,
              required_scope text not null,
              max_cost integer not null,
              input_refs_json text not null,
              status text not null,
              artifact_digest text,
              primary key(run_id, task_id)
            );
            create table if not exists dependencies(
              run_id text not null,
              task_id text not null,
              dependency_id text not null,
              primary key(run_id, task_id, dependency_id)
            );
            create table if not exists coordination_effects(
              run_id text not null,
              effect_key text not null,
              receipt_sha256 text not null,
              primary key(run_id, effect_key)
            );
            """
        )

    def close(self) -> None:
        self.connection.close()

    def create_run(self, run_id: str, *, budget_limit: int, orders: Iterable[WorkOrder]) -> None:
        materialized = tuple(orders)
        ids = {order.task_id for order in materialized}
        if len(ids) != len(materialized):
            raise CoordinationRejected("duplicate_task_id")
        if any(dep not in ids or dep == order.task_id for order in materialized for dep in order.depends_on):
            raise CoordinationRejected("dependency_invalid")
        self.connection.execute("insert into coordination_runs values(?,?,0,'RUNNING')", (run_id, budget_limit))
        for order in materialized:
            self.connection.execute(
                "insert into work_orders values(?,?,?,?,?,?, 'READY', null)",
                (
                    run_id,
                    order.task_id,
                    order.owner,
                    order.required_scope,
                    order.max_cost,
                    _canonical(list(order.input_refs)).decode(),
                ),
            )
            self.connection.executemany(
                "insert into dependencies values(?,?,?)",
                ((run_id, order.task_id, dep) for dep in order.depends_on),
            )
        self.connection.commit()

    def ready(self, run_id: str) -> tuple[str, ...]:
        rows = self.connection.execute(
            """
            select w.task_id from work_orders w
            where w.run_id=? and w.status='READY' and not exists(
              select 1 from dependencies d join work_orders p
                on p.run_id=d.run_id and p.task_id=d.dependency_id
              where d.run_id=w.run_id and d.task_id=w.task_id and p.status!='COMPLETED'
            ) order by w.task_id
            """,
            (run_id,),
        ).fetchall()
        return tuple(row["task_id"] for row in rows)

    def claim(self, run_id: str, task_id: str, *, agent: str, scopes: Iterable[str]) -> dict[str, Any]:
        scope_set = set(scopes)
        try:
            self.connection.execute("begin immediate")
            row = self.connection.execute(
                "select * from work_orders where run_id=? and task_id=?", (run_id, task_id)
            ).fetchone()
            if row is None or row["status"] != "READY":
                raise CoordinationRejected("work_order_not_ready")
            if row["owner"] != agent:
                raise CoordinationRejected("work_order_owner_mismatch")
            if row["required_scope"] not in scope_set:
                raise CoordinationRejected("work_order_scope_missing")
            if task_id not in self.ready(run_id):
                raise CoordinationRejected("work_order_dependency_incomplete")
            budget = self.connection.execute(
                "select budget_limit,budget_reserved from coordination_runs where run_id=?", (run_id,)
            ).fetchone()
            if budget is None or budget["budget_reserved"] + row["max_cost"] > budget["budget_limit"]:
                raise CoordinationRejected("run_budget_exceeded")
            self.connection.execute(
                "update work_orders set status='CLAIMED' where run_id=? and task_id=?",
                (run_id, task_id),
            )
            self.connection.execute(
                "update coordination_runs set budget_reserved=budget_reserved+? where run_id=?",
                (row["max_cost"], run_id),
            )
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise
        return {
            "task_id": task_id,
            "owner": agent,
            "required_scope": row["required_scope"],
            "max_cost": row["max_cost"],
            "input_refs": tuple(json.loads(row["input_refs_json"])),
        }

    def complete(self, run_id: str, task_id: str, *, agent: str, artifact: dict[str, Any]) -> str:
        row = self.connection.execute(
            "select owner,status from work_orders where run_id=? and task_id=?", (run_id, task_id)
        ).fetchone()
        if row is None or row["status"] != "CLAIMED":
            raise CoordinationRejected("work_order_not_claimed")
        if row["owner"] != agent:
            raise CoordinationRejected("completion_owner_mismatch")
        digest = _digest(artifact)
        self.connection.execute(
            "update work_orders set status='COMPLETED',artifact_digest=? where run_id=? and task_id=?",
            (digest, run_id, task_id),
        )
        self.connection.commit()
        return digest

    def join(self, run_id: str, *, expected_tasks: Iterable[str], effect_key: str) -> dict[str, Any]:
        expected = tuple(sorted(expected_tasks))
        rows = self.connection.execute(
            "select task_id,status,artifact_digest from work_orders where run_id=? order by task_id",
            (run_id,),
        ).fetchall()
        if tuple(row["task_id"] for row in rows) != expected:
            raise CoordinationRejected("join_task_set_mismatch")
        if any(row["status"] != "COMPLETED" or row["artifact_digest"] is None for row in rows):
            raise CoordinationRejected("join_incomplete")
        receipt = {
            "run_id": run_id,
            "artifacts": {row["task_id"]: row["artifact_digest"] for row in rows},
        }
        receipt_digest = _digest(receipt)
        self.connection.execute(
            "insert or ignore into coordination_effects values(?,?,?)",
            (run_id, effect_key, receipt_digest),
        )
        self.connection.execute(
            "update coordination_runs set status='COMPLETED' where run_id=?", (run_id,)
        )
        self.connection.commit()
        return {**receipt, "receipt_sha256": receipt_digest, "effect_count": self.effect_count(run_id)}

    def run_snapshot(self, run_id: str) -> dict[str, Any]:
        run = self.connection.execute(
            "select * from coordination_runs where run_id=?", (run_id,)
        ).fetchone()
        if run is None:
            raise CoordinationRejected("run_missing")
        states = {
            row["task_id"]: row["status"]
            for row in self.connection.execute(
                "select task_id,status from work_orders where run_id=? order by task_id", (run_id,)
            )
        }
        return {
            "status": run["status"],
            "budget_limit": run["budget_limit"],
            "budget_reserved": run["budget_reserved"],
            "tasks": states,
        }

    def effect_count(self, run_id: str) -> int:
        return int(
            self.connection.execute(
                "select count(*) from coordination_effects where run_id=?", (run_id,)
            ).fetchone()[0]
        )
