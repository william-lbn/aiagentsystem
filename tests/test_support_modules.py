from __future__ import annotations

import asyncio

import pytest

from agentlab.eval import EvalCase, EvalHarness
from agentlab.memory import MemoryStore
from agentlab.retrieval import HybridRetriever
from agentlab.workflow import run_parallel, with_timeout


def test_eval_harness_preserves_case_evidence_and_pass_rate():
    cases = [
        EvalCase("exact", "agent", lambda output: output["answer"] == "AGENT"),
        EvalCase("budget", "ignored", lambda output: output["steps"] <= 1),
    ]

    result = EvalHarness().run(lambda value: {"answer": value.upper(), "steps": 2}, cases)

    assert result["pass_rate"] == 0.5
    assert [case["passed"] for case in result["cases"]] == [True, False]


def test_eval_harness_empty_suite_is_defined():
    assert EvalHarness().run(lambda value: value, []) == {"pass_rate": 0.0, "cases": []}


def test_memory_search_ranks_relevant_items_and_preserves_metadata():
    memory = MemoryStore()
    memory.add("python", "python debugging workflow", source="user")
    memory.add("database", "sqlite transaction recovery", source="run")

    results = memory.search("python debugging", k=1)

    assert [item.key for item in results] == ["python"]
    assert results[0].metadata == {"source": "user"}


def test_memory_search_does_not_invent_a_match():
    memory = MemoryStore()
    memory.add("known", "checkpoint recovery")

    assert memory.search("unrelated-token") == []


def test_hybrid_retriever_combines_lexical_overlap_and_freshness():
    retriever = HybridRetriever(
        [
            {"id": "relevant", "text": "agent checkpoint recovery", "freshness": 0.2},
            {"id": "fresh-only", "text": "unrelated release", "freshness": 1.0},
        ]
    )

    results = retriever.search("agent recovery", k=2)

    assert [row["id"] for row in results] == ["relevant", "fresh-only"]
    assert results[0]["score"] > results[1]["score"]


def test_parallel_workflow_preserves_success_and_failure_outcomes():
    async def successful():
        return {"status": "ok"}

    async def failed():
        raise ValueError("controlled failure")

    results = asyncio.run(run_parallel([successful, failed]))

    assert results[0] == {"status": "ok"}
    assert isinstance(results[1], ValueError)


def test_workflow_timeout_is_observable():
    async def slow():
        await asyncio.sleep(0.05)

    with pytest.raises(TimeoutError):
        asyncio.run(with_timeout(slow(), seconds=0.001))
