"""Production-style AgentOps teaching service.

The service is intentionally small, but the write path preserves the same
correctness boundaries taught in the runtime chapters:

request -> immutable pending action -> action-bound approval -> effect record
-> state mutation -> independent verifier -> evidence -> FINISHED.

All state in this fixture lives in one SQLite database, so the mutation and its
local effect record can share one database transaction.  This is *not* a claim
of exactly-once behavior for remote APIs.  A real external adapter must use an
idempotency key and/or observation/reconciliation before retrying an ambiguous
outcome.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
import hashlib
import json
import sqlite3
import time
import uuid
from contextlib import closing

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

DB = Path(__file__).resolve().parents[1] / "data" / "agentops.db"
app = FastAPI(title="AgentOps Service Desk", version="0.2")


def _connect() -> sqlite3.Connection:
    DB.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB, timeout=5.0, isolation_level=None)
    c.row_factory = sqlite3.Row
    c.execute("pragma foreign_keys=on")
    c.execute("pragma journal_mode=WAL")
    _ensure_schema(c)
    return c


def _columns(c: sqlite3.Connection, table: str) -> set[str]:
    return {str(r[1]) for r in c.execute(f"pragma table_info({table})")}


def _ensure_schema(c: sqlite3.Connection) -> None:
    # Create the v0.2 schema for clean databases.
    c.executescript(
        """
        create table if not exists runs(
          id text primary key,
          tenant_id text not null default 'legacy',
          request text not null,
          status text not null,
          proposal text not null,
          pending_action text,
          evidence text not null default '{}',
          verifier_status text not null default 'NOT_RUN',
          version integer not null default 1
        );
        create table if not exists approvals(
          run_id text primary key,
          tenant_id text not null default 'legacy',
          action_id text,
          decision text not null,
          decided_at real not null default 0,
          foreign key(run_id) references runs(id)
        );
        create table if not exists resources(
          tenant_id text not null,
          resource_id text not null,
          state text not null,
          primary key(tenant_id,resource_id)
        );
        create table if not exists effects(
          action_id text primary key,
          run_id text not null,
          tenant_id text not null,
          operation text not null,
          status text not null,
          result text,
          created_at real not null,
          foreign key(run_id) references runs(id)
        );
        """
    )
    # The source package may contain the earlier v0.1 fixture DB.  Migrate it
    # explicitly rather than requiring users to delete state by hand.
    run_cols = _columns(c, "runs")
    for name, ddl in {
        "tenant_id": "text not null default 'legacy'",
        "pending_action": "text",
        "verifier_status": "text not null default 'NOT_RUN'",
        "version": "integer not null default 1",
    }.items():
        if name not in run_cols:
            c.execute(f"alter table runs add column {name} {ddl}")
    approval_cols = _columns(c, "approvals")
    for name, ddl in {
        "tenant_id": "text not null default 'legacy'",
        "action_id": "text",
        "decided_at": "real not null default 0",
    }.items():
        if name not in approval_cols:
            c.execute(f"alter table approvals add column {name} {ddl}")


def _canonical(obj: dict[str, Any]) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def _make_action(run_id: str, tenant_id: str, request: str) -> dict[str, Any]:
    lowered = request.lower()
    operation = "delete_demo_record" if ("delete" in lowered or "删除" in request) else "update_demo_record"
    base = {
        "run_id": run_id,
        "tenant_id": tenant_id,
        "operation": operation,
        "resource_id": "demo-record",
        "desired_state": "DELETED" if operation == "delete_demo_record" else "UPDATED",
    }
    action_id = hashlib.sha256(_canonical(base).encode("utf-8")).hexdigest()
    return {"action_id": action_id, **base}


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    data = dict(row)
    for key in ("pending_action", "evidence"):
        raw = data.get(key)
        if isinstance(raw, str) and raw:
            try:
                data[key] = json.loads(raw)
            except json.JSONDecodeError:
                # Existing corrupt evidence must remain visible, not be hidden.
                data[key] = {"decode_error": True, "raw": raw}
    return data


class RunIn(BaseModel):
    request: str = Field(min_length=1, max_length=4000)


class Decision(BaseModel):
    decision: str
    action_id: str | None = None


@app.post("/runs")
def create_run(body: RunIn, x_tenant_id: str = Header(..., alias="X-Tenant-ID")):
    tenant = x_tenant_id.strip()
    if not tenant:
        raise HTTPException(400, "X-Tenant-ID must be non-empty")
    rid = str(uuid.uuid4())
    is_write = any(x in body.request.lower() for x in ["delete", "update"]) or any(
        x in body.request for x in ["删除", "修改"]
    )
    if is_write:
        action = _make_action(rid, tenant, body.request)
        status = "WAITING_APPROVAL"
        proposal = "write proposal requires approval bound to action_id"
        evidence = {
            "request": body.request,
            "policy": "write_requires_action_bound_approval",
            "effect_executed": False,
        }
        verifier = "NOT_RUN"
    else:
        action = None
        status = "FINISHED"
        proposal = "read-only investigation completed"
        evidence = {
            "request": body.request,
            "policy": "read_only_allowed",
            "effect_executed": False,
            "verifier": {"status": "PASS", "reason": "no_mutating_effect"},
        }
        verifier = "PASS"
    with closing(_connect()) as c:
        c.execute("begin immediate")
        if action:
            # Demo resource starts ACTIVE.  A real adapter would point to a
            # remote resource and require observation/reconciliation semantics.
            c.execute(
                "insert into resources(tenant_id,resource_id,state) values(?,?,?) "
                "on conflict(tenant_id,resource_id) do nothing",
                (tenant, action["resource_id"], "ACTIVE"),
            )
        c.execute(
            "insert into runs(id,tenant_id,request,status,proposal,pending_action,evidence,verifier_status,version) "
            "values(?,?,?,?,?,?,?,?,1)",
            (
                rid,
                tenant,
                body.request,
                status,
                proposal,
                json.dumps(action, ensure_ascii=False) if action else None,
                json.dumps(evidence, ensure_ascii=False),
                verifier,
            ),
        )
        c.commit()
    response = {"run_id": rid, "status": status, "proposal": proposal}
    if action:
        response["action_id"] = action["action_id"]
    return response


@app.get("/runs/{rid}")
def get_run(rid: str, x_tenant_id: str = Header(..., alias="X-Tenant-ID")):
    with closing(_connect()) as c:
        row = c.execute("select * from runs where id=? and tenant_id=?", (rid, x_tenant_id)).fetchone()
    if not row:
        # Deliberately do not reveal whether another tenant owns this run.
        raise HTTPException(404, "run not found")
    return _row_to_dict(row)


@app.get("/runs/{rid}/effects")
def get_effects(rid: str, x_tenant_id: str = Header(..., alias="X-Tenant-ID")):
    with closing(_connect()) as c:
        if not c.execute("select 1 from runs where id=? and tenant_id=?", (rid, x_tenant_id)).fetchone():
            raise HTTPException(404, "run not found")
        rows = c.execute(
            "select action_id,operation,status,result,created_at from effects where run_id=? and tenant_id=? order by created_at",
            (rid, x_tenant_id),
        ).fetchall()
    return {"effects": [dict(r) for r in rows]}


@app.post("/runs/{rid}/approval")
def approve(rid: str, body: Decision, x_tenant_id: str = Header(..., alias="X-Tenant-ID")):
    if body.decision not in {"approve", "reject"}:
        raise HTTPException(400, "decision must be approve/reject")
    with closing(_connect()) as c:
        c.execute("begin immediate")
        row = c.execute("select * from runs where id=? and tenant_id=?", (rid, x_tenant_id)).fetchone()
        if not row:
            c.rollback()
            raise HTTPException(404, "run not found")
        current = _row_to_dict(row)
        pending = current.get("pending_action")
        if current["status"] in {"FINISHED", "REJECTED"}:
            existing = c.execute(
                "select decision,action_id from approvals where run_id=? and tenant_id=?", (rid, x_tenant_id)
            ).fetchone()
            if (
                existing
                and existing["decision"] == body.decision
                and (body.action_id is None or existing["action_id"] == body.action_id)
            ):
                c.commit()
                return {
                    "run_id": rid,
                    "status": current["status"],
                    "idempotent_replay": True,
                    "verifier_status": current["verifier_status"],
                }
            c.rollback()
            raise HTTPException(409, "run already has a terminal approval outcome")
        if current["status"] != "WAITING_APPROVAL" or not isinstance(pending, dict):
            c.rollback()
            raise HTTPException(409, f"run is not awaiting approval: {current['status']}")
        expected_action_id = pending["action_id"]
        if body.action_id != expected_action_id:
            c.rollback()
            raise HTTPException(409, "approval action_id does not match pending action")

        now = time.time()
        if body.decision == "reject":
            evidence = {
                "action_id": expected_action_id,
                "effect_executed": False,
                "verifier": {"status": "PASS", "reason": "rejected_before_effect"},
            }
            c.execute(
                "insert into approvals(run_id,tenant_id,action_id,decision,decided_at) values(?,?,?,?,?)",
                (rid, x_tenant_id, expected_action_id, "reject", now),
            )
            c.execute(
                "update runs set status='REJECTED',evidence=?,verifier_status='PASS',version=version+1 where id=? and tenant_id=?",
                (json.dumps(evidence, ensure_ascii=False), rid, x_tenant_id),
            )
            c.commit()
            return {"run_id": rid, "status": "REJECTED", "action_id": expected_action_id, "verifier_status": "PASS"}

        # Persist action-bound approval and one effect record in the same local
        # transaction as the demo mutation.  action_id is the idempotency key.
        c.execute(
            "insert into approvals(run_id,tenant_id,action_id,decision,decided_at) values(?,?,?,?,?)",
            (rid, x_tenant_id, expected_action_id, "approve", now),
        )
        c.execute(
            "insert into effects(action_id,run_id,tenant_id,operation,status,result,created_at) values(?,?,?,?,?,?,?)",
            (expected_action_id, rid, x_tenant_id, pending["operation"], "INTENT_RECORDED", None, now),
        )
        c.execute(
            "update resources set state=? where tenant_id=? and resource_id=?",
            (pending["desired_state"], x_tenant_id, pending["resource_id"]),
        )
        observed = c.execute(
            "select state from resources where tenant_id=? and resource_id=?",
            (x_tenant_id, pending["resource_id"]),
        ).fetchone()
        verifier_ok = bool(observed and observed["state"] == pending["desired_state"])
        result = {
            "resource_id": pending["resource_id"],
            "desired_state": pending["desired_state"],
            "observed_state": observed["state"] if observed else None,
        }
        c.execute(
            "update effects set status=?,result=? where action_id=?",
            ("COMMITTED" if verifier_ok else "UNKNOWN", json.dumps(result, ensure_ascii=False), expected_action_id),
        )
        evidence = {
            "action_id": expected_action_id,
            "effect_executed": True,
            "effect_status": "COMMITTED" if verifier_ok else "UNKNOWN",
            "observation": result,
            "verifier": {"status": "PASS" if verifier_ok else "FAIL"},
        }
        final_status = "FINISHED" if verifier_ok else "NEEDS_RECONCILIATION"
        c.execute(
            "update runs set status=?,evidence=?,verifier_status=?,version=version+1 where id=? and tenant_id=?",
            (
                final_status,
                json.dumps(evidence, ensure_ascii=False),
                "PASS" if verifier_ok else "FAIL",
                rid,
                x_tenant_id,
            ),
        )
        c.commit()
    return {
        "run_id": rid,
        "status": final_status,
        "action_id": expected_action_id,
        "verifier_status": "PASS" if verifier_ok else "FAIL",
    }


@app.get("/healthz")
def healthz():
    return {"ok": True, "schema": "0.2"}
