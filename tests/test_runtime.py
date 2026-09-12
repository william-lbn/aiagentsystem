from __future__ import annotations

import threading
import pytest

from agentlab import AgentRuntime, ModelDecision, ScriptedModel, ToolRegistry, tool
from agentlab.security import PolicyEngine
from agentlab.checkpoint import JsonCheckpointStore, CheckpointConflictError, CheckpointCorruptionError
from agentlab.journal import EffectJournal, JournalCorruptionError
from agentlab.events import Event


def runtime(tmp_path, model, tools, **kw):
    return AgentRuntime(
        model,
        tools,
        checkpoint=JsonCheckpointStore(tmp_path / "cp.json"),
        journal=EffectJournal(tmp_path / "j.jsonl"),
        **kw,
    )


def test_tool_flow_commits_then_finishes(tmp_path):
    @tool("add")
    def add(a: int, b: int):
        return a + b

    t = ToolRegistry()
    t.register(add)
    r = runtime(
        tmp_path, ScriptedModel([ModelDecision(tool="add", args={"a": 2, "b": 3}), ModelDecision(final="5")]), t
    )
    out = r.run("2+3")
    assert out["status"] == "FINISHED"
    assert out["answer"] == "5"
    assert r.journal.verify()
    assert [m["status"] for m in out["messages"] if m.get("role") == "tool"] == ["COMMITTED"]


def test_unknown_tool_not_applied_is_terminal_not_silent_success(tmp_path):
    t = ToolRegistry()
    r = runtime(
        tmp_path, ScriptedModel([ModelDecision(tool="missing", args={}), ModelDecision(final="unreachable")]), t
    )
    out = r.run("go")
    assert out["status"] == "TOOL_NOT_APPLIED"
    assert out["answer"] is None
    assert [m["status"] for m in out["messages"] if m.get("role") == "tool"] == ["NOT_APPLIED"]


def test_non_idempotent_timeout_is_unknown_and_never_retry_hint(tmp_path):
    @tool("write", idempotent=False)
    def write():
        raise TimeoutError("response lost")

    t = ToolRegistry()
    t.register(write)
    r = runtime(tmp_path, ScriptedModel([ModelDecision(tool="write", args={})]), t)
    out = r.run("go")
    msg = next(m for m in out["messages"] if m.get("role") == "tool")
    assert out["status"] == "NEEDS_RECONCILIATION"
    assert msg["status"] == "UNKNOWN"
    assert msg["retryable"] is False


def test_idempotent_timeout_can_expose_retry_hint_but_runtime_still_requires_reconciliation(tmp_path):
    @tool("read", idempotent=True)
    def read():
        raise TimeoutError("response lost")

    t = ToolRegistry()
    t.register(read)
    r = runtime(tmp_path, ScriptedModel([ModelDecision(tool="read", args={})]), t)
    out = r.run("go")
    msg = next(m for m in out["messages"] if m.get("role") == "tool")
    assert msg["status"] == "UNKNOWN" and msg["retryable"] is True
    assert out["status"] == "NEEDS_RECONCILIATION"


def test_hitl_approval_is_action_bound_and_executes_exact_pending_effect_once(tmp_path):
    effects = []

    @tool("write", risk="high", idempotent=True)
    def write(x: str):
        effects.append(x)
        return x

    t = ToolRegistry()
    t.register(write)
    r = runtime(
        tmp_path,
        ScriptedModel([ModelDecision(tool="write", args={"x": "a"}), ModelDecision(final="done")]),
        t,
        policy=PolicyEngine(approval_tools={"write"}),
    )
    first = r.run("write")
    assert first["status"] == "WAITING_APPROVAL" and effects == []
    action_id = first["pending_approval"]["action_id"]

    missing = r.run("ignored", resume=True, run_id=first["run_id"], approval="approve")
    assert missing["status"] == "WAITING_APPROVAL" and effects == []
    stale = r.run("ignored", resume=True, run_id=first["run_id"], approval="approve", approval_action_id="stale")
    assert stale["status"] == "WAITING_APPROVAL" and effects == []

    second = r.run("ignored", resume=True, run_id=first["run_id"], approval="approve", approval_action_id=action_id)
    assert second["status"] == "FINISHED"
    assert effects == ["a"]


def test_resume_transport_payload_does_not_reauthorize_original_run(tmp_path):
    effects = []

    @tool("write", risk="high", idempotent=True)
    def write(x: str):
        effects.append(x)
        return x

    t = ToolRegistry()
    t.register(write)
    r = runtime(
        tmp_path,
        ScriptedModel([ModelDecision(tool="write", args={"x": "approved"}), ModelDecision(final="done")]),
        t,
        policy=PolicyEngine(approval_tools={"write"}, blocked_prompt_tokens=["transport-block"]),
    )
    first = r.run("perform approved write")
    action_id = first["pending_approval"]["action_id"]
    # The resume payload is not a second user prompt.  The exact pending action,
    # already bound to the durable run, is what the approval authorizes.
    out = r.run(
        "transport-block", resume=True, run_id=first["run_id"], approval="approve", approval_action_id=action_id
    )
    assert out["status"] == "FINISHED"
    assert effects == ["approved"]


def test_hitl_reject_never_executes_effect(tmp_path):
    effects = []

    @tool("write", risk="high")
    def write(x: str):
        effects.append(x)
        return x

    t = ToolRegistry()
    t.register(write)
    r = runtime(
        tmp_path,
        ScriptedModel([ModelDecision(tool="write", args={"x": "a"})]),
        t,
        policy=PolicyEngine(approval_tools={"write"}),
    )
    first = r.run("write")
    action_id = first["pending_approval"]["action_id"]
    out = r.run("ignored", resume=True, run_id=first["run_id"], approval="reject", approval_action_id=action_id)
    assert out["status"] == "REJECTED" and effects == []


def test_hitl_expiry_fails_closed(tmp_path):
    effects = []
    now = [1000.0]

    @tool("write", risk="high")
    def write():
        effects.append(1)
        return 1

    t = ToolRegistry()
    t.register(write)
    r = runtime(
        tmp_path,
        ScriptedModel([ModelDecision(tool="write", args={})]),
        t,
        policy=PolicyEngine(approval_tools={"write"}),
        clock=lambda: now[0],
        approval_ttl_seconds=10,
    )
    first = r.run("write")
    now[0] = 1011.0
    out = r.run(
        "ignored",
        resume=True,
        run_id=first["run_id"],
        approval="approve",
        approval_action_id=first["pending_approval"]["action_id"],
    )
    assert out["status"] == "APPROVAL_EXPIRED" and effects == []


def test_crash_after_external_commit_before_local_result_never_blind_replays(tmp_path):
    external = []

    @tool("remote-write", risk="high", idempotent=False)
    def remote_write(value: str):
        external.append(value)  # external system committed
        raise SystemExit("process died before local result persistence")

    t = ToolRegistry()
    t.register(remote_write)
    r = runtime(tmp_path, ScriptedModel([ModelDecision(tool="remote_write", args={"value": "v"})]), t)
    with pytest.raises(SystemExit):
        r.run("go")
    assert external == ["v"]
    snap = r.checkpoint.load()
    assert snap["state"]["status"] == "EXECUTING_EFFECT"

    # A fresh process cannot know whether the external effect committed.  It
    # must surface UNKNOWN/reconciliation and must not invoke the adapter.
    replayed = []

    @tool("remote-write", risk="high", idempotent=False)
    def remote_write_again(value: str):
        replayed.append(value)
        return value

    t2 = ToolRegistry()
    t2.register(remote_write_again, name="remote_write")
    r2 = runtime(tmp_path, ScriptedModel([ModelDecision(final="must not be reached")]), t2)
    out = r2.run("ignored", resume=True, run_id=snap["run_id"])
    assert out["status"] == "NEEDS_RECONCILIATION"
    assert replayed == []


def test_checkpoint_namespaces_runs_and_rejects_stale_writer(tmp_path):
    cp = JsonCheckpointStore(tmp_path / "cp.json")
    v1 = cp.save("r1", {"status": "A"}, expected_version=0)
    cp.save("r2", {"status": "B"}, expected_version=0)
    assert cp.load("r1")["state"]["status"] == "A"
    assert cp.load("r2")["state"]["status"] == "B"
    cp.save("r1", {"status": "C"}, expected_version=v1)
    with pytest.raises(CheckpointConflictError):
        cp.save("r1", {"status": "STALE"}, expected_version=v1)


def test_checkpoint_corruption_fails_visibly(tmp_path):
    cp = JsonCheckpointStore(tmp_path / "cp.json")
    cp.save("r1", {"status": "A"})
    (cp.runs_dir / "r1.json").write_text("{broken", encoding="utf-8")
    with pytest.raises(CheckpointCorruptionError):
        cp.load("r1")


def test_journal_corruption_fails_closed_before_append(tmp_path):
    p = tmp_path / "j.jsonl"
    j = EffectJournal(p)
    j.append(Event("intent", "r", 1, {"x": 1}))
    p.write_text(p.read_text(encoding="utf-8") + "{broken\n", encoding="utf-8")
    assert j.verify() is False
    with pytest.raises(JournalCorruptionError):
        EffectJournal(p)


def test_journal_serializes_concurrent_appenders(tmp_path):
    p = tmp_path / "j.jsonl"
    EffectJournal(p)
    errors = []

    def writer(i):
        try:
            EffectJournal(p).append(Event("e", "r", i, {"i": i}))
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=writer, args=(i,)) for i in range(12)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    j = EffectJournal(p)
    assert errors == []
    assert j.verify() and len(j.read()) == 12


def test_default_runtime_state_honors_agentlab_home(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENTLAB_HOME", str(tmp_path / "isolated"))
    cp = JsonCheckpointStore()
    j = EffectJournal()
    assert cp.path == tmp_path / "isolated" / "checkpoint.json"
    assert j.path == tmp_path / "isolated" / "effect_journal.jsonl"
