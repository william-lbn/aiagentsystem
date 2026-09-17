from __future__ import annotations

from pathlib import Path
import asyncio
import sys

import pytest

from agentlab.runtime_system import (
    AsyncSupervisor,
    CodingWorkspace,
    GovernedLoop,
    LoopDecision,
    PathSandbox,
    Plugin,
    PluginManifest,
    PluginRuntime,
    SandboxPolicy,
    SandboxViolation,
)


def test_governed_loop_requires_external_verification():
    loop = GovernedLoop(max_steps=3)
    decisions = iter([LoopDecision("act", {"tool": "inspect"}), LoopDecision("finish")])
    report = loop.run(lambda _events: next(decisions), lambda _d: {"found": "target"}, lambda events: len(events) == 3)
    assert report.status == "FINISHED"
    assert report.verified is True
    assert report.steps == 2


def test_governed_loop_contains_no_progress():
    loop = GovernedLoop(max_steps=10, max_same_observation=2)
    report = loop.run(
        lambda _events: LoopDecision("act", {"tool": "inspect", "path": "same"}),
        lambda _decision: {"digest": "unchanged"},
        lambda _events: False,
    )
    assert report.status == "NO_PROGRESS"
    assert report.steps == 3
    assert report.events[-1]["reason"] == "no_progress"


def test_governed_loop_enforces_budget():
    loop = GovernedLoop(max_steps=2, max_same_observation=10)
    report = loop.run(
        lambda events: LoopDecision("act", {"step": len(events)}),
        lambda decision: {"step": decision.payload["step"]},
        lambda _events: False,
    )
    assert report.status == "BUDGET_EXCEEDED"


def test_async_supervisor_bounds_concurrency():
    async def scenario():
        supervisor = AsyncSupervisor(concurrency=2)

        def job(value: int):
            async def run():
                await asyncio.sleep(0.005)
                return value

            return run

        return await supervisor.run_all({f"j{i}": job(i) for i in range(4)})

    report = asyncio.run(scenario())
    assert report.max_active == 2
    assert set(report.states.values()) == {"SUCCEEDED"}
    assert report.results == {"j0": 0, "j1": 1, "j2": 2, "j3": 3}


def test_async_supervisor_cancels_and_accounts_for_loser():
    async def scenario():
        supervisor = AsyncSupervisor(concurrency=2)

        async def fast():
            await asyncio.sleep(0.001)
            return "evidence"

        async def slow():
            await asyncio.sleep(1)
            return "late"

        return await supervisor.first_success({"fast": fast, "slow": slow})

    report = asyncio.run(scenario())
    assert report.winner == "fast"
    assert report.states == {"fast": "SUCCEEDED", "slow": "CANCELLED"}


def test_async_first_success_bounds_concurrency_and_accounts_for_queued_jobs():
    async def scenario():
        supervisor = AsyncSupervisor(concurrency=1)

        async def fast():
            await asyncio.sleep(0.001)
            return "evidence"

        async def queued():
            await asyncio.sleep(1)
            return "late"

        return await supervisor.first_success({"fast": fast, "queued-a": queued, "queued-b": queued})

    report = asyncio.run(scenario())
    assert report.max_active == 1
    assert report.winner == "fast"
    assert report.states == {"fast": "SUCCEEDED", "queued-a": "CANCELLED", "queued-b": "CANCELLED"}


def test_path_sandbox_writes_and_reads_scoped_file(tmp_path: Path):
    sandbox = PathSandbox(SandboxPolicy(tmp_path, frozenset({"fs.read", "fs.write"})))
    sandbox.write_text("nested/result.txt", "verified")
    assert sandbox.read_text("nested/result.txt") == "verified"


@pytest.mark.parametrize("target", ["../escape.txt", "/tmp/absolute-escape.txt"])
def test_path_sandbox_rejects_escape(tmp_path: Path, target: str):
    sandbox = PathSandbox(SandboxPolicy(tmp_path, frozenset({"fs.write"})))
    with pytest.raises(SandboxViolation, match="path_outside_workspace"):
        sandbox.write_text(target, "blocked")


def test_path_sandbox_rejects_missing_capability(tmp_path: Path):
    sandbox = PathSandbox(SandboxPolicy(tmp_path, frozenset({"fs.read"})))
    with pytest.raises(SandboxViolation, match="capability_denied"):
        sandbox.write_text("x", "blocked")


def test_plugin_runtime_activates_dependency_order():
    activated: list[str] = []

    def plugin(name: str, dependencies: tuple[str, ...] = ()) -> Plugin:
        return Plugin(
            PluginManifest(name, dependencies),
            lambda: activated.append(name) or f"handle:{name}",
            lambda _handle: None,
        )

    report = PluginRuntime().activate_all([plugin("ui", ("loop",)), plugin("tools"), plugin("loop", ("tools",))])
    assert report.status == "ACTIVE"
    assert report.order == ("tools", "loop", "ui")
    assert activated == ["tools", "loop", "ui"]


def test_plugin_runtime_rolls_back_reverse_order():
    disposed: list[str] = []

    def ok(name: str, dependencies: tuple[str, ...] = ()) -> Plugin:
        return Plugin(PluginManifest(name, dependencies), lambda: name, lambda _handle: disposed.append(name))

    broken = Plugin(
        PluginManifest("ui", ("loop",)),
        lambda: (_ for _ in ()).throw(RuntimeError("activation failed")),
        lambda _handle: disposed.append("ui"),
    )
    report = PluginRuntime().activate_all([ok("tools"), ok("loop", ("tools",)), broken])
    assert report.status == "ROLLED_BACK"
    assert report.active == ()
    assert report.disposed == ("loop", "tools")
    assert disposed == ["loop", "tools"]


def test_plugin_runtime_rejects_missing_dependency():
    plugin = Plugin(PluginManifest("ui", ("missing",)), lambda: object(), lambda _handle: None)
    report = PluginRuntime().activate_all([plugin])
    assert report.status == "INVALID"
    assert report.error == "missing_dependencies:ui:missing"


def _workspace(tmp_path: Path) -> CodingWorkspace:
    (tmp_path / "calc.py").write_text("def add(a, b):\n    return a - b\n", encoding="utf-8")
    return CodingWorkspace(tmp_path, allowed_files={"calc.py"})


def test_coding_workspace_accepts_only_child_process_verified_patch(tmp_path: Path):
    workspace = _workspace(tmp_path)
    report = workspace.apply_and_verify(
        "calc.py",
        old="return a - b",
        new="return a + b",
        verifier=[
            sys.executable,
            "-I",
            "-c",
            "import runpy; ns=runpy.run_path('calc.py'); assert ns['add'](2, 3) == 5; "
            "assert ns['add'](-4, 1) == -3; print('2 passed')",
        ],
    )
    assert report.accepted is True
    assert report.stdout == "2 passed"
    assert report.rolled_back is False
    assert "return a + b" in (tmp_path / "calc.py").read_text(encoding="utf-8")


def test_coding_workspace_rolls_back_failed_patch(tmp_path: Path):
    workspace = _workspace(tmp_path)
    report = workspace.apply_and_verify(
        "calc.py",
        old="return a - b",
        new="return a * b",
        verifier=[
            sys.executable,
            "-I",
            "-c",
            "import runpy; ns=runpy.run_path('calc.py'); assert ns['add'](2, 3) == 5",
        ],
    )
    assert report.accepted is False
    assert report.returncode != 0
    assert report.rolled_back is True
    assert "return a - b" in (tmp_path / "calc.py").read_text(encoding="utf-8")


def test_coding_workspace_rolls_back_timed_out_verifier(tmp_path: Path):
    workspace = _workspace(tmp_path)
    report = workspace.apply_and_verify(
        "calc.py",
        old="return a - b",
        new="return a + b",
        verifier=[sys.executable, "-I", "-c", "import time; time.sleep(1)"],
        timeout_seconds=0.01,
    )
    assert report.accepted is False
    assert report.returncode == 124
    assert report.stderr == "verifier_timeout"
    assert report.rolled_back is True
    assert "return a - b" in (tmp_path / "calc.py").read_text(encoding="utf-8")


def test_coding_workspace_rejects_scope_violation(tmp_path: Path):
    workspace = _workspace(tmp_path)
    with pytest.raises(SandboxViolation, match="patch_scope_denied"):
        workspace.apply_and_verify(
            "secrets.txt",
            old="a",
            new="b",
            verifier=[sys.executable, "-c", "pass"],
        )
