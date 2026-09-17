"""Deterministic runtime mechanisms for Part III of the course.

The classes in this module are deliberately provider-independent.  They execute
real scheduling, filesystem, lifecycle and subprocess-verification behavior,
while keeping the fixtures small enough to run on Linux/macOS and arm64/x86_64
without a model API key.  Provider-backed model decisions are an optional input
to these mechanisms; they are never used as the correctness oracle.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import asyncio
import difflib
import hashlib
import json
import os
import subprocess


def canonical_digest(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class LoopDecision:
    kind: str
    payload: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.kind not in {"act", "finish", "needs_input", "fail"}:
            raise ValueError(f"unsupported loop decision: {self.kind}")


@dataclass(frozen=True, slots=True)
class LoopReport:
    status: str
    steps: int
    verified: bool
    stop_reason: str
    events: tuple[dict[str, Any], ...]


class GovernedLoop:
    """A finite loop whose terminal success is owned by an external verifier."""

    def __init__(self, *, max_steps: int, max_same_observation: int = 2):
        if max_steps < 1 or max_same_observation < 1:
            raise ValueError("loop limits must be positive")
        self.max_steps = max_steps
        self.max_same_observation = max_same_observation

    def run(
        self,
        decide: Callable[[tuple[dict[str, Any], ...]], LoopDecision],
        act: Callable[[LoopDecision], dict[str, Any]],
        verify: Callable[[tuple[dict[str, Any], ...]], bool],
    ) -> LoopReport:
        events: list[dict[str, Any]] = []
        previous_progress: str | None = None
        same_observation = 0
        steps = 0
        while steps < self.max_steps:
            decision = decide(tuple(events))
            steps += 1
            decision_event = {
                "type": "decision",
                "step": steps,
                "kind": decision.kind,
                "payload": decision.payload,
            }
            events.append(decision_event)
            if decision.kind == "finish":
                verified = bool(verify(tuple(events)))
                return LoopReport(
                    status="FINISHED" if verified else "VERIFICATION_FAILED",
                    steps=steps,
                    verified=verified,
                    stop_reason="goal_verified" if verified else "goal_not_verified",
                    events=tuple(events),
                )
            if decision.kind == "needs_input":
                return LoopReport("NEEDS_INPUT", steps, False, "input_required", tuple(events))
            if decision.kind == "fail":
                return LoopReport("FAILED", steps, False, "model_declared_failure", tuple(events))

            observation = act(decision)
            progress = canonical_digest({"decision": decision.payload, "observation": observation})
            events.append(
                {
                    "type": "observation",
                    "step": steps,
                    "value": observation,
                    "progress_digest": progress,
                }
            )
            if progress == previous_progress:
                same_observation += 1
            else:
                previous_progress = progress
                same_observation = 1
            if same_observation > self.max_same_observation:
                events.append({"type": "stop", "step": steps, "reason": "no_progress"})
                return LoopReport("NO_PROGRESS", steps, False, "no_progress", tuple(events))

        events.append({"type": "stop", "step": steps, "reason": "step_budget_exhausted"})
        return LoopReport("BUDGET_EXCEEDED", steps, False, "step_budget_exhausted", tuple(events))


@dataclass(frozen=True, slots=True)
class AsyncReport:
    winner: str | None
    results: dict[str, Any]
    states: dict[str, str]
    max_active: int


class AsyncSupervisor:
    """Own task lifetime, a concurrency bound, and cancellation accounting."""

    def __init__(self, *, concurrency: int):
        if concurrency < 1:
            raise ValueError("concurrency must be positive")
        self.concurrency = concurrency

    async def run_all(self, jobs: dict[str, Callable[[], Awaitable[Any]]]) -> AsyncReport:
        semaphore = asyncio.Semaphore(self.concurrency)
        states = {name: "QUEUED" for name in jobs}
        results: dict[str, Any] = {}
        active = 0
        max_active = 0
        lock = asyncio.Lock()

        async def run_one(name: str, job: Callable[[], Awaitable[Any]]) -> None:
            nonlocal active, max_active
            async with semaphore:
                async with lock:
                    active += 1
                    max_active = max(max_active, active)
                    states[name] = "RUNNING"
                try:
                    results[name] = await job()
                    states[name] = "SUCCEEDED"
                except asyncio.CancelledError:
                    states[name] = "CANCELLED"
                    raise
                except Exception as exc:  # explicit evidence, not silent loss
                    states[name] = "FAILED"
                    results[name] = {"error": type(exc).__name__, "message": str(exc)}
                finally:
                    async with lock:
                        active -= 1

        await asyncio.gather(*(run_one(name, job) for name, job in jobs.items()))
        return AsyncReport(None, results, states, max_active)

    async def first_success(self, jobs: dict[str, Callable[[], Awaitable[Any]]]) -> AsyncReport:
        semaphore = asyncio.Semaphore(self.concurrency)
        states = {name: "QUEUED" for name in jobs}
        results: dict[str, Any] = {}
        active = 0
        max_active = 0
        lock = asyncio.Lock()

        async def run_one(name: str, job: Callable[[], Awaitable[Any]]) -> tuple[str, Any]:
            nonlocal active, max_active
            entered = False
            try:
                async with semaphore:
                    async with lock:
                        active += 1
                        max_active = max(max_active, active)
                        states[name] = "RUNNING"
                        entered = True
                    value = await job()
                    states[name] = "SUCCEEDED"
                    results[name] = value
                    return name, value
            except asyncio.CancelledError:
                states[name] = "CANCELLED"
                raise
            except Exception as exc:
                states[name] = "FAILED"
                results[name] = {"error": type(exc).__name__, "message": str(exc)}
                raise
            finally:
                if entered:
                    async with lock:
                        active -= 1

        tasks = {asyncio.create_task(run_one(name, job), name=name): name for name, job in jobs.items()}
        winner: str | None = None
        try:
            pending = set(tasks)
            while pending and winner is None:
                done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
                for task in sorted(done, key=lambda item: tasks[item]):
                    try:
                        winner, _ = task.result()
                        break
                    except Exception:
                        continue
            for task in pending:
                task.cancel()
            await asyncio.gather(*pending, return_exceptions=True)
        finally:
            orphaned = [task for task in tasks if not task.done()]
            for task in orphaned:
                task.cancel()
            await asyncio.gather(*orphaned, return_exceptions=True)
        return AsyncReport(winner, results, states, max_active)


class SandboxViolation(PermissionError):
    pass


@dataclass(frozen=True, slots=True)
class SandboxPolicy:
    root: Path
    capabilities: frozenset[str]
    max_write_bytes: int = 1_000_000
    allow_symlinks: bool = False


class PathSandbox:
    """Capability and path gate for teaching filesystem tools.

    This is not an OS sandbox.  It prevents traversal/symlink escapes for the
    operations routed through this object; arbitrary native code still needs a
    container/namespace/seccomp-style boundary.
    """

    def __init__(self, policy: SandboxPolicy):
        self.policy = policy
        self.root = policy.root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _resolve(self, relative: str, capability: str) -> Path:
        if capability not in self.policy.capabilities:
            raise SandboxViolation(f"capability_denied:{capability}")
        candidate = self.root / relative
        resolved = candidate.resolve(strict=False)
        if resolved != self.root and self.root not in resolved.parents:
            raise SandboxViolation("path_outside_workspace")
        if not self.policy.allow_symlinks:
            current = self.root
            for part in candidate.relative_to(self.root).parts:
                current = current / part
                if current.exists() and current.is_symlink():
                    raise SandboxViolation("symlink_not_allowed")
        return resolved

    def write_text(self, relative: str, text: str) -> Path:
        payload = text.encode()
        if len(payload) > self.policy.max_write_bytes:
            raise SandboxViolation("write_size_exceeded")
        target = self._resolve(relative, "fs.write")
        target.parent.mkdir(parents=True, exist_ok=True)
        flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            fd = os.open(target, flags, 0o600)
        except OSError as exc:
            raise SandboxViolation(f"open_rejected:{type(exc).__name__}") from exc
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        return target

    def read_text(self, relative: str) -> str:
        return self._resolve(relative, "fs.read").read_text(encoding="utf-8")


@dataclass(frozen=True, slots=True)
class PluginManifest:
    name: str
    dependencies: tuple[str, ...] = ()


@dataclass(slots=True)
class Plugin:
    manifest: PluginManifest
    activate: Callable[[], Any]
    dispose: Callable[[Any], None]


@dataclass(frozen=True, slots=True)
class PluginRunReport:
    status: str
    order: tuple[str, ...]
    active: tuple[str, ...]
    disposed: tuple[str, ...]
    error: str | None


class PluginRuntime:
    """Validate a plugin DAG, activate deterministically, rollback in reverse."""

    @staticmethod
    def _order(plugins: dict[str, Plugin]) -> tuple[str, ...]:
        for name, plugin in plugins.items():
            if plugin.manifest.name != name:
                raise ValueError(f"plugin_identity_mismatch:{name}")
            missing = sorted(set(plugin.manifest.dependencies) - set(plugins))
            if missing:
                raise ValueError(f"missing_dependencies:{name}:{','.join(missing)}")
        indegree = {name: 0 for name in plugins}
        edges = {name: [] for name in plugins}
        for name, plugin in plugins.items():
            for dependency in plugin.manifest.dependencies:
                indegree[name] += 1
                edges[dependency].append(name)
        ready = sorted(name for name, degree in indegree.items() if degree == 0)
        order: list[str] = []
        while ready:
            name = ready.pop(0)
            order.append(name)
            for child in sorted(edges[name]):
                indegree[child] -= 1
                if indegree[child] == 0:
                    ready.append(child)
                    ready.sort()
        if len(order) != len(plugins):
            raise ValueError("plugin_dependency_cycle")
        return tuple(order)

    def activate_all(self, plugins: Iterable[Plugin]) -> PluginRunReport:
        by_name: dict[str, Plugin] = {}
        for plugin in plugins:
            if plugin.manifest.name in by_name:
                return PluginRunReport("INVALID", (), (), (), "duplicate_plugin")
            by_name[plugin.manifest.name] = plugin
        try:
            order = self._order(by_name)
        except ValueError as exc:
            return PluginRunReport("INVALID", (), (), (), str(exc))
        handles: dict[str, Any] = {}
        disposed: list[str] = []
        try:
            for name in order:
                handles[name] = by_name[name].activate()
        except Exception as exc:
            for active_name in reversed(tuple(handles)):
                by_name[active_name].dispose(handles[active_name])
                disposed.append(active_name)
            return PluginRunReport(
                "ROLLED_BACK",
                order,
                (),
                tuple(disposed),
                f"activation_failed:{name}:{type(exc).__name__}",
            )
        return PluginRunReport("ACTIVE", order, tuple(handles), (), None)


@dataclass(frozen=True, slots=True)
class PatchVerification:
    accepted: bool
    returncode: int
    stdout: str
    stderr: str
    diff: str
    diff_sha256: str
    changed_files: tuple[str, ...]
    rolled_back: bool


class CodingWorkspace:
    """Apply a scoped text patch and accept it only after a child-process oracle."""

    def __init__(self, root: Path, *, allowed_files: Iterable[str]):
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.allowed_files = frozenset(allowed_files)
        self.sandbox = PathSandbox(
            SandboxPolicy(self.root, frozenset({"fs.read", "fs.write"}), max_write_bytes=100_000)
        )

    def apply_and_verify(
        self,
        relative: str,
        *,
        old: str,
        new: str,
        verifier: list[str],
        timeout_seconds: float = 5.0,
    ) -> PatchVerification:
        if relative not in self.allowed_files:
            raise SandboxViolation("patch_scope_denied")
        original = self.sandbox.read_text(relative)
        if original.count(old) != 1:
            raise ValueError("patch_preimage_mismatch")
        patched = original.replace(old, new, 1)
        diff = "".join(
            difflib.unified_diff(
                original.splitlines(keepends=True),
                patched.splitlines(keepends=True),
                fromfile=f"a/{relative}",
                tofile=f"b/{relative}",
            )
        )
        self.sandbox.write_text(relative, patched)
        env = {
            "PATH": os.environ.get("PATH", ""),
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONHASHSEED": "0",
        }
        try:
            completed = subprocess.run(
                verifier,
                cwd=self.root,
                env=env,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                check=False,
            )
            returncode = completed.returncode
            stdout = completed.stdout.strip()
            stderr = completed.stderr.strip()
        except subprocess.TimeoutExpired as exc:
            returncode = 124
            stdout = (exc.stdout or "").strip()
            stderr = "verifier_timeout"
        accepted = returncode == 0
        rolled_back = False
        if not accepted:
            self.sandbox.write_text(relative, original)
            rolled_back = True
        return PatchVerification(
            accepted=accepted,
            returncode=returncode,
            stdout=stdout,
            stderr=stderr,
            diff=diff,
            diff_sha256=hashlib.sha256(diff.encode()).hexdigest(),
            changed_files=(relative,),
            rolled_back=rolled_back,
        )
