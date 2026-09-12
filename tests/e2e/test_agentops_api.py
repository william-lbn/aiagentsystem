from fastapi.testclient import TestClient
from production.agentops_service.app.main import app, DB

TENANT_A = {"X-Tenant-ID": "tenant-a"}
TENANT_B = {"X-Tenant-ID": "tenant-b"}


def fresh_client():
    DB.unlink(missing_ok=True)
    for suffix in ("-wal", "-shm"):
        DB.with_name(DB.name + suffix).unlink(missing_ok=True)
    return TestClient(app)


def test_read_only_run_finishes_with_verifier_evidence():
    c = fresh_client()
    assert c.get("/healthz").json()["ok"]
    r = c.post("/runs", headers=TENANT_A, json={"request": "investigate payments timeout"}).json()
    assert r["status"] == "FINISHED"
    detail = c.get(f"/runs/{r['run_id']}", headers=TENANT_A).json()
    assert detail["verifier_status"] == "PASS"
    assert detail["evidence"]["effect_executed"] is False


def test_high_risk_approval_executes_bound_effect_and_verifies_it():
    c = fresh_client()
    w = c.post("/runs", headers=TENANT_A, json={"request": "删除旧记录"}).json()
    assert w["status"] == "WAITING_APPROVAL"
    assert w["action_id"]
    before = c.get(f"/runs/{w['run_id']}", headers=TENANT_A).json()
    assert before["evidence"]["effect_executed"] is False

    a = c.post(
        f"/runs/{w['run_id']}/approval",
        headers=TENANT_A,
        json={"decision": "approve", "action_id": w["action_id"]},
    ).json()
    assert a["status"] == "FINISHED"
    assert a["verifier_status"] == "PASS"

    after = c.get(f"/runs/{w['run_id']}", headers=TENANT_A).json()
    assert after["evidence"]["effect_executed"] is True
    assert after["evidence"]["observation"]["observed_state"] == "DELETED"
    effects = c.get(f"/runs/{w['run_id']}/effects", headers=TENANT_A).json()["effects"]
    assert len(effects) == 1
    assert effects[0]["action_id"] == w["action_id"]
    assert effects[0]["status"] == "COMMITTED"

    # Same decision is idempotent and cannot execute a second effect.
    replay = c.post(
        f"/runs/{w['run_id']}/approval",
        headers=TENANT_A,
        json={"decision": "approve", "action_id": w["action_id"]},
    ).json()
    assert replay["idempotent_replay"] is True
    assert len(c.get(f"/runs/{w['run_id']}/effects", headers=TENANT_A).json()["effects"]) == 1


def test_stale_action_id_and_cross_tenant_access_fail_closed():
    c = fresh_client()
    w = c.post("/runs", headers=TENANT_A, json={"request": "delete demo record"}).json()
    stale = c.post(
        f"/runs/{w['run_id']}/approval",
        headers=TENANT_A,
        json={"decision": "approve", "action_id": "stale-action"},
    )
    assert stale.status_code == 409
    assert c.get(f"/runs/{w['run_id']}", headers=TENANT_A).json()["status"] == "WAITING_APPROVAL"
    assert c.get(f"/runs/{w['run_id']}", headers=TENANT_B).status_code == 404
    assert (
        c.post(
            f"/runs/{w['run_id']}/approval",
            headers=TENANT_B,
            json={"decision": "approve", "action_id": w["action_id"]},
        ).status_code
        == 404
    )


def test_rejection_records_evidence_without_effect():
    c = fresh_client()
    w = c.post("/runs", headers=TENANT_A, json={"request": "update demo record"}).json()
    out = c.post(
        f"/runs/{w['run_id']}/approval",
        headers=TENANT_A,
        json={"decision": "reject", "action_id": w["action_id"]},
    ).json()
    assert out["status"] == "REJECTED"
    detail = c.get(f"/runs/{w['run_id']}", headers=TENANT_A).json()
    assert detail["evidence"]["effect_executed"] is False
    assert c.get(f"/runs/{w['run_id']}/effects", headers=TENANT_A).json()["effects"] == []
