from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import json

import pytest

from agentlab.frontier_system import (
    CandidateTaskResult,
    CanaryRollout,
    CapstoneLedger,
    CapstoneOrchestrator,
    DeploymentGate,
    ImprovementGate,
    PostTrainingDatasetGate,
    RealtimeSession,
    TrajectorySample,
)


ROOT = Path(__file__).resolve().parents[1]


def test_deployment_gate_inspects_real_repository_contract():
    gate = DeploymentGate()
    evidence = gate.inspect_repository(ROOT)
    decision = gate.verify(evidence)
    assert decision.release_allowed
    assert decision.status == "STATIC_CONTRACT_READY"
    assert evidence.exposed_port == evidence.command_port == evidence.compose_container_port == 8010
    assert evidence.run_as_user == "65532:65532"


def test_deployment_gate_blocks_port_drift_in_compose():
    dockerfile = (ROOT / "production/agentops_service/Dockerfile").read_text()
    compose = (ROOT / "docker-compose.yml").read_text().replace('"8010:8010"', '"8010:8000"')
    lock = json.loads((ROOT / "production/agentops_service/IMAGE_LOCK.json").read_text())
    decision = DeploymentGate().verify(DeploymentGate().inspect(dockerfile, compose, image_lock=lock))
    assert not decision.release_allowed
    assert not decision.checks["port_contract"]


def test_deployment_gate_blocks_mutable_root_image_without_healthcheck():
    evidence = DeploymentGate().inspect(
        'FROM python:latest\nEXPOSE 8010\nCMD ["server","--port","8010"]\n',
        'ports:\n  - "8010:8010"\n',
    )
    decision = DeploymentGate().verify(evidence)
    assert decision.status == "BLOCKED"
    assert not decision.checks["base_digest_pinned"]
    assert not decision.checks["non_root"]
    assert not decision.checks["semantic_healthcheck"]


def test_deployment_gate_does_not_invent_platform_or_matching_image_lock():
    dockerfile = (ROOT / "production/agentops_service/Dockerfile").read_text()
    compose = (ROOT / "docker-compose.yml").read_text()
    gate = DeploymentGate()
    missing = gate.verify(gate.inspect(dockerfile, compose))
    assert not missing.release_allowed
    assert not missing.checks["multi_arch_declared"]
    assert not missing.checks["image_lock_matches"]
    incorrect = gate.verify(gate.inspect(dockerfile, compose, image_lock={"base_image": "other@sha256:" + "0" * 64, "platforms": ["linux/arm64"]}))
    assert not incorrect.release_allowed
    assert not incorrect.checks["image_lock_matches"]
    assert not incorrect.checks["multi_arch_declared"]


def _datasets() -> list[TrajectorySample]:
    return [
        TrajectorySample("train-1", "billing-train", "train", "tool read invoice 7", "run-1", "p0", 1.0, 0, 3),
        TrajectorySample("train-2", "support-train", "train", "retrieve ticket 9", "run-2", "p0", 0.8, 0, 2),
        TrajectorySample("eval-1", "billing-heldout", "eval", "audit invoice 42", "run-3", "p0", 1.0, 0, 4),
        TrajectorySample("eval-2", "support-heldout", "eval", "triage ticket 55", "run-4", "p0", 0.0, 0, 2),
    ]


def test_post_training_gate_accepts_disjoint_provenanced_trajectories():
    audit = PostTrainingDatasetGate().audit(_datasets())
    assert audit.promotion_allowed
    assert audit.status == "DATASET_ELIGIBLE"
    assert audit.train_records == audit.eval_records == 2


def test_post_training_gate_quarantines_group_and_transcript_leakage():
    samples = _datasets()
    leaked = replace(
        samples[0],
        sample_id="leak",
        split="eval",
        source_run="run-leak",
    )
    audit = PostTrainingDatasetGate().audit(samples + [leaked])
    assert not audit.promotion_allowed
    assert audit.status == "QUARANTINED"
    assert audit.leaked_task_families == ("billing-train",)
    assert len(audit.duplicate_transcripts) == 1


def test_post_training_gate_rejects_missing_lineage_and_invalid_split():
    samples = _datasets()
    audit = PostTrainingDatasetGate().audit([replace(samples[0], source_run=""), *samples[1:]])
    assert not audit.checks["complete_provenance"]
    with pytest.raises(ValueError, match="split"):
        PostTrainingDatasetGate().audit([replace(samples[0], split="test")])


def test_realtime_session_commits_current_epoch_effect():
    session = RealtimeSession()
    session.ingest(100, "audio", "audio.partial", {"text": "turn on"})
    epoch = session.begin_effect("light-1", 110, {"action": "turn_on"})
    assert session.complete_effect("light-1", epoch, 120, {"ok": True}) == "COMMITTED"
    assert len(session.effects) == 1
    assert [event.seq for event in session.events] == [1, 2, 3]


def test_realtime_session_drops_completion_from_pre_interrupt_epoch():
    session = RealtimeSession()
    session.ingest(100, "vision", "vision.frame", {"object": "robot-arm"})
    epoch = session.begin_effect("move-1", 110, {"distance_cm": 5})
    session.interrupt(115, "stop")
    result = session.complete_effect("move-1", epoch, 120, {"moved": True})
    assert result == "STALE_DROPPED"
    assert session.effects == []
    assert session.events[-1].kind == "effect.stale_dropped"


def test_realtime_session_rejects_time_regression_and_unknown_effect():
    session = RealtimeSession()
    session.ingest(100, "audio", "audio.partial", {})
    with pytest.raises(ValueError, match="regressed"):
        session.ingest(99, "vision", "vision.frame", {})
    with pytest.raises(ValueError, match="not in flight"):
        session.complete_effect("missing", 0, 101, {})


def _baseline_and_candidate():
    baseline = [
        CandidateTaskResult("safe-read", "low", True, 0, 2),
        CandidateTaskResult("refund", "high", False, 0, 3),
        CandidateTaskResult("research", "low", True, 0, 4),
        CandidateTaskResult("delete", "high", True, 0, 3),
    ]
    candidate = [
        CandidateTaskResult("safe-read", "low", True, 0, 2),
        CandidateTaskResult("refund", "high", True, 0, 3.2),
        CandidateTaskResult("research", "low", True, 0, 4.1),
        CandidateTaskResult("delete", "high", True, 0, 3),
    ]
    return baseline, candidate


def test_improvement_gate_and_canary_promote_verified_candidate():
    baseline, candidate = _baseline_and_candidate()
    decision = ImprovementGate().compare(baseline, candidate)
    rollout = CanaryRollout("policy-v1")
    rollout.start("policy-v2", decision)
    assert rollout.finish(verifier_passed=True, safety_violations=0) == "PROMOTED"
    assert rollout.active_version == "policy-v2"


def test_canary_rolls_back_even_after_offline_gate_passes():
    baseline, candidate = _baseline_and_candidate()
    decision = ImprovementGate().compare(baseline, candidate)
    rollout = CanaryRollout("policy-v1")
    rollout.start("policy-v2", decision)
    assert rollout.finish(verifier_passed=False, safety_violations=1) == "ROLLED_BACK"
    assert rollout.active_version == "policy-v1"


def test_improvement_gate_rejects_high_risk_safety_regression():
    baseline, candidate = _baseline_and_candidate()
    unsafe = [replace(row, safety_violations=1) if row.task_id == "delete" else row for row in candidate]
    decision = ImprovementGate().compare(baseline, unsafe)
    assert not decision.eligible
    assert not decision.checks["no_high_risk_regression"]
    with pytest.raises(ValueError, match="offline"):
        CanaryRollout("v1").start("unsafe", decision)


def test_improvement_gate_requires_paired_tasks():
    baseline, candidate = _baseline_and_candidate()
    with pytest.raises(ValueError, match="same"):
        ImprovementGate().compare(baseline, candidate[:-1])


def test_improvement_gate_rejects_duplicate_ids_and_risk_relabeling():
    baseline, candidate = _baseline_and_candidate()
    with pytest.raises(ValueError, match="duplicate"):
        ImprovementGate().compare(baseline + [baseline[0]], candidate)
    relabeled = [replace(row, risk_tier="low") if row.task_id == "refund" else row for row in candidate]
    with pytest.raises(ValueError, match="risk tier"):
        ImprovementGate().compare(baseline, relabeled)


def test_capstone_normal_path_is_durable_authorized_and_verified(tmp_path):
    orchestrator = CapstoneOrchestrator(tmp_path)
    result = orchestrator.run("run-normal", approval=orchestrator.demonstration_approval("run-normal"))
    orchestrator.close()
    assert result["path"][-1] == "COMPLETED"
    assert result["effect_count"] == 1
    assert result["recovery_used"] is False
    assert result["trace_verified"] and result["verified"]


def test_capstone_recovers_lost_ack_without_duplicate_effect(tmp_path):
    orchestrator = CapstoneOrchestrator(tmp_path)
    result = orchestrator.run("run-recovery", approval=orchestrator.demonstration_approval("run-recovery"), lose_ack=True)
    orchestrator.close()
    assert "UNKNOWN" in result["path"] and "RECONCILING" in result["path"]
    assert result["path"][-1] == "COMPLETED"
    assert result["effect_count"] == 1
    assert result["recovery_used"] and result["verified"]


def test_capstone_rejects_stale_approval_before_any_effect(tmp_path):
    orchestrator = CapstoneOrchestrator(tmp_path)
    stale = orchestrator.demonstration_approval("another-run")
    with pytest.raises(ValueError, match="approval"):
        orchestrator.run("current-run", approval=stale)
    assert orchestrator.remote.count("current-run:ticket-17") == 0
    assert orchestrator.gateway.effects == []
    assert orchestrator.ledger.states("current-run")[-1] == "WAITING_APPROVAL"
    orchestrator.close()


def test_capstone_ledger_rejects_illegal_transition_and_detects_tamper(tmp_path):
    path = tmp_path / "ledger.db"
    ledger = CapstoneLedger(path)
    ledger.append("r", "RECEIVED", {"tenant": "a"})
    with pytest.raises(ValueError, match="invalid"):
        ledger.append("r", "COMPLETED", {})
    ledger.db.execute("UPDATE events SET state='FORGED' WHERE run_id='r'")
    ledger.db.commit()
    assert ledger.verify("r") is False
    ledger.close()
