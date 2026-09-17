from __future__ import annotations

from pathlib import Path
import sqlite3

import pytest

from agentlab.specialized_system import (
    AgentEventStore,
    BoundaryViolation,
    BrowserActionRejected,
    DurableGraph,
    EvidenceBinder,
    EvidenceViolation,
    GraphRecoveryError,
    LocalBrowserTask,
    QueryRejected,
    ReadOnlyDataAgent,
    SessionIntegrityError,
    SessionLedger,
)


def test_session_ledger_reopens_and_compacts_typed_facts(tmp_path: Path):
    path = tmp_path / "sessions.sqlite"
    ledger = SessionLedger(path)
    ledger.create("root", goal="fix parser", baseline="abc", workspace="w-root")
    ledger.record("root", "constraint", "scope", ["parser.py"])
    ledger.record("root", "failure", "test", "test_empty failed")
    ledger.create("branch", parent_id="root", goal="fix parser", baseline="abc", workspace="w-branch")
    ledger.record("branch", "decision", "patch", "guard empty input")
    ledger.close()

    reopened = SessionLedger(path)
    snapshot = reopened.compact("branch")
    reopened.close()
    assert snapshot.ancestry == ("root", "branch")
    assert [fact["kind"] for fact in snapshot.facts] == ["constraint", "failure", "decision"]
    assert len(snapshot.digest) == 64


def test_session_ledger_rejects_orphan_branch(tmp_path: Path):
    ledger = SessionLedger(tmp_path / "sessions.sqlite")
    with pytest.raises(SessionIntegrityError, match="parent_session_missing"):
        ledger.create("orphan", parent_id="missing", goal="x", baseline="a", workspace="w")
    ledger.close()


def test_agent_event_store_persists_ordered_events(tmp_path: Path):
    path = tmp_path / "events.sqlite"
    store = AgentEventStore(path)
    store.create_conversation("c1", "w1")
    store.append("c1", "w1", "r1", "tool.started", {"tool": "shell"}, expected_sequence=1)
    store.append("c1", "w1", "r2", "tool.finished", {"exit_code": 0}, expected_sequence=2)
    store.close()
    reopened = AgentEventStore(path)
    assert [event["sequence"] for event in reopened.events("c1")] == [1, 2]
    reopened.close()


def test_agent_event_store_rejects_workspace_mixup(tmp_path: Path):
    store = AgentEventStore(tmp_path / "events.sqlite")
    store.create_conversation("c1", "w1")
    with pytest.raises(BoundaryViolation, match="workspace_binding_mismatch"):
        store.append("c1", "w2", "r1", "tool.started", {}, expected_sequence=1)
    assert store.events("c1") == ()
    store.close()


def test_loopback_browser_task_executes_observed_action():
    with LocalBrowserTask() as task:
        observation = task.observe()
        result = task.act(observation, "approve")
        assert result["status"] == "APPROVED"
        assert task.effect_count == 1


def test_loopback_browser_task_rejects_stale_observation():
    with LocalBrowserTask() as task:
        observation = task.observe()
        task.mutate_environment("CHANGED")
        with pytest.raises(BrowserActionRejected, match="stale_observation"):
            task.act(observation, "approve")
        assert task.effect_count == 0


def _database(path: Path) -> None:
    connection = sqlite3.connect(path)
    connection.executescript(
        "create table invoices(id integer primary key, amount integer, status text);"
        "insert into invoices(amount,status) values(42,'open'),(58,'open'),(10,'paid');"
    )
    connection.close()


def test_data_agent_returns_plan_bounded_rows_and_digest(tmp_path: Path):
    path = tmp_path / "data.sqlite"
    _database(path)
    agent = ReadOnlyDataAgent(path, max_rows=10)
    result = agent.execute("select status,sum(amount) as total from invoices group by status order by status")
    agent.close()
    assert result.columns == ("status", "total")
    assert result.rows == (("open", 100), ("paid", 10))
    assert result.plan
    assert len(result.digest) == 64


def test_data_agent_denies_mutation_and_preserves_database(tmp_path: Path):
    path = tmp_path / "data.sqlite"
    _database(path)
    agent = ReadOnlyDataAgent(path)
    with pytest.raises(QueryRejected):
        agent.execute("delete from invoices")
    agent.close()
    connection = sqlite3.connect(path)
    assert connection.execute("select count(*) from invoices").fetchone()[0] == 3
    connection.close()


def test_evidence_binder_verifies_exact_source_span(tmp_path: Path):
    path = tmp_path / "source.txt"
    path.write_text("Agent success requires an independent verifier.", encoding="utf-8")
    binder = EvidenceBinder()
    binder.ingest_file("s1", path)
    claim = binder.bind("success needs verification", "s1", 26, 46, "independent verifier")
    assert claim.quote == "independent verifier"
    assert len(claim.source_sha256) == 64


def test_evidence_binder_rejects_quote_drift(tmp_path: Path):
    path = tmp_path / "source.txt"
    path.write_text("Durable evidence is versioned.", encoding="utf-8")
    binder = EvidenceBinder()
    binder.ingest_file("s1", path)
    with pytest.raises(EvidenceViolation, match="quote_mismatch"):
        binder.bind("evidence is versioned", "s1", 8, 16, "outdated")


def test_durable_graph_resumes_across_instances_and_applies_once(tmp_path: Path):
    path = tmp_path / "graph.sqlite"
    nodes = ("collect", "approve", "apply", "verify")
    first = DurableGraph(path, nodes)
    first.start("r1", {"history": []})
    state = first.step("r1", expected_version=1)
    state = first.step("r1", expected_version=state["version"])
    first.close()

    second = DurableGraph(path, nodes)
    while state["node"] != "FINISHED":
        state = second.step("r1", expected_version=state["version"])
    assert state["state"]["history"] == list(nodes)
    assert second.effect_count("r1") == 1
    second.close()


def test_durable_graph_rejects_changed_topology(tmp_path: Path):
    path = tmp_path / "graph.sqlite"
    graph = DurableGraph(path, ("collect", "apply", "verify"))
    graph.start("r1", {"history": []})
    graph.close()
    changed = DurableGraph(path, ("collect", "approve", "apply", "verify"))
    with pytest.raises(GraphRecoveryError, match="graph_signature_mismatch"):
        changed.resume("r1")
    assert changed.effect_count("r1") == 0
    changed.close()
