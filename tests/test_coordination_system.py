from pathlib import Path

import pytest

from agentlab.coordination_system import (
    A2ATaskLedger,
    CoordinationRejected,
    DelegationAuthority,
    DelegationGrant,
    DelegationRejected,
    MultiAgentCoordinator,
    WorkOrder,
)


def _authority() -> DelegationAuthority:
    return DelegationAuthority(b"course-only-fixed-secret")


def _grant(authority: DelegationAuthority, **changes) -> DelegationGrant:
    values = {
        "principal": "supervisor",
        "delegate": "researcher",
        "task_id": "task-27",
        "scopes": ("evidence.read", "artifact.publish"),
        "issued_at": 100,
        "expires_at": 200,
        "nonce": "nonce-27",
    }
    values.update(changes)
    return authority.issue(**values)


def test_delegation_grant_binds_delegate_task_scope_and_time():
    authority = _authority()
    grant = _grant(authority)
    authority.verify(
        grant,
        delegate="researcher",
        task_id="task-27",
        required_scope="artifact.publish",
        now=150,
    )


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"delegate": "coder"}, "delegate_mismatch"),
        ({"task_id": "other"}, "task_mismatch"),
        ({"required_scope": "repository.write"}, "scope_missing"),
        ({"now": 200}, "expired"),
    ],
)
def test_delegation_grant_rejects_binding_mismatch(kwargs, message):
    authority = _authority()
    grant = _grant(authority)
    request = {
        "delegate": "researcher",
        "task_id": "task-27",
        "required_scope": "artifact.publish",
        "now": 150,
    }
    request.update(kwargs)
    with pytest.raises(DelegationRejected, match=message):
        authority.verify(grant, **request)


def test_delegation_grant_rejects_payload_tampering():
    authority = _authority()
    grant = _grant(authority)
    tampered = DelegationGrant(
        grant.principal,
        grant.delegate,
        grant.task_id,
        ("admin",),
        grant.issued_at,
        grant.expires_at,
        grant.nonce,
        grant.signature,
    )
    with pytest.raises(DelegationRejected, match="signature_invalid"):
        authority.verify(
            tampered,
            delegate="researcher",
            task_id="task-27",
            required_scope="admin",
            now=150,
        )


def test_a2a_task_ledger_persists_lifecycle_and_artifact(tmp_path: Path):
    path = tmp_path / "a2a.sqlite"
    authority = _authority()
    ledger = A2ATaskLedger(path, authority)
    submitted = ledger.submit(
        task_id="task-27",
        context_id="ctx-27",
        delegate="researcher",
        required_scope="artifact.publish",
        idempotency_key="send-27",
        grant=_grant(authority),
        now=150,
    )
    working = ledger.transition(
        "task-27", expected_version=submitted["version"], target="TASK_STATE_WORKING"
    )
    completed = ledger.complete(
        "task-27",
        expected_version=working["version"],
        artifact={"name": "evidence.json", "claims": 3},
    )
    ledger.close()

    reopened = A2ATaskLedger(path, authority)
    assert reopened.snapshot("task-27") == completed
    assert completed["state"] == "TASK_STATE_COMPLETED"
    assert len(completed["artifact_digest"]) == 64
    assert reopened.events("task-27") == (
        "task.submitted",
        "task.status",
        "task.artifact",
        "task.status",
    )
    reopened.close()


def test_a2a_task_rejects_unauthorized_submission_without_row(tmp_path: Path):
    authority = _authority()
    ledger = A2ATaskLedger(tmp_path / "a2a.sqlite", authority)
    with pytest.raises(DelegationRejected, match="scope_missing"):
        ledger.submit(
            task_id="task-27",
            context_id="ctx-27",
            delegate="researcher",
            required_scope="repository.write",
            idempotency_key="send-27",
            grant=_grant(authority),
            now=150,
        )
    assert ledger.task_count() == 0
    ledger.close()


def test_a2a_submission_is_idempotent_and_nonce_is_single_use(tmp_path: Path):
    authority = _authority()
    ledger = A2ATaskLedger(tmp_path / "a2a.sqlite", authority)
    args = {
        "task_id": "task-27",
        "context_id": "ctx-27",
        "delegate": "researcher",
        "required_scope": "artifact.publish",
        "idempotency_key": "send-27",
        "grant": _grant(authority),
        "now": 150,
    }
    first = ledger.submit(**args)
    assert ledger.submit(**args) == first
    with pytest.raises(DelegationRejected, match="nonce_or_identity_reused"):
        ledger.submit(
            **{
                **args,
                "task_id": "task-other",
                "idempotency_key": "send-other",
                "grant": _grant(authority, task_id="task-other"),
            }
        )
    ledger.close()


def _orders() -> tuple[WorkOrder, ...]:
    return (
        WorkOrder("research", "researcher", "sources.read", 3, ("source:policy",)),
        WorkOrder("patch", "coder", "repository.write", 4, ("repo:workspace",)),
        WorkOrder(
            "verify",
            "reviewer",
            "artifacts.verify",
            2,
            ("artifact:research", "artifact:patch"),
            ("research", "patch"),
        ),
    )


def test_multi_agent_coordinator_enforces_join_budget_and_effect_once(tmp_path: Path):
    path = tmp_path / "coordination.sqlite"
    coordinator = MultiAgentCoordinator(path)
    coordinator.create_run("run-28", budget_limit=9, orders=_orders())
    assert coordinator.ready("run-28") == ("patch", "research")

    research = coordinator.claim(
        "run-28", "research", agent="researcher", scopes={"sources.read"}
    )
    patch = coordinator.claim("run-28", "patch", agent="coder", scopes={"repository.write"})
    assert research["input_refs"] == ("source:policy",)
    assert patch["input_refs"] == ("repo:workspace",)
    coordinator.complete("run-28", "research", agent="researcher", artifact={"claims": 3})
    coordinator.complete("run-28", "patch", agent="coder", artifact={"tests": "passed"})
    assert coordinator.ready("run-28") == ("verify",)
    coordinator.claim("run-28", "verify", agent="reviewer", scopes={"artifacts.verify"})
    coordinator.complete("run-28", "verify", agent="reviewer", artifact={"accepted": True})
    first = coordinator.join(
        "run-28", expected_tasks=("research", "patch", "verify"), effect_key="publish-28"
    )
    second = coordinator.join(
        "run-28", expected_tasks=("research", "patch", "verify"), effect_key="publish-28"
    )
    assert first["effect_count"] == second["effect_count"] == 1
    assert coordinator.run_snapshot("run-28")["budget_reserved"] == 9
    coordinator.close()

    reopened = MultiAgentCoordinator(path)
    assert reopened.run_snapshot("run-28")["status"] == "COMPLETED"
    assert reopened.effect_count("run-28") == 1
    reopened.close()


def test_multi_agent_coordinator_rejects_wrong_owner_before_budget_or_effect(tmp_path: Path):
    coordinator = MultiAgentCoordinator(tmp_path / "coordination.sqlite")
    coordinator.create_run("run-28", budget_limit=9, orders=_orders())
    with pytest.raises(CoordinationRejected, match="owner_mismatch"):
        coordinator.claim("run-28", "research", agent="coder", scopes={"sources.read"})
    snapshot = coordinator.run_snapshot("run-28")
    assert snapshot["budget_reserved"] == 0
    assert snapshot["tasks"]["research"] == "READY"
    assert coordinator.effect_count("run-28") == 0
    coordinator.close()


def test_multi_agent_coordinator_rejects_early_join_and_budget_overrun(tmp_path: Path):
    coordinator = MultiAgentCoordinator(tmp_path / "coordination.sqlite")
    coordinator.create_run("run-28", budget_limit=6, orders=_orders())
    coordinator.claim("run-28", "research", agent="researcher", scopes={"sources.read"})
    with pytest.raises(CoordinationRejected, match="budget_exceeded"):
        coordinator.claim("run-28", "patch", agent="coder", scopes={"repository.write"})
    with pytest.raises(CoordinationRejected, match="join_incomplete"):
        coordinator.join(
            "run-28", expected_tasks=("research", "patch", "verify"), effect_key="publish-28"
        )
    assert coordinator.effect_count("run-28") == 0
    coordinator.close()
