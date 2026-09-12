from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator
import json
import os
import re
import tempfile

try:  # Linux/macOS: the supported course environments.
    import fcntl
except ImportError:  # pragma: no cover - explicit portability fallback.
    fcntl = None  # type: ignore[assignment]


class CheckpointConflictError(RuntimeError):
    """Raised when a writer attempts to overwrite a newer checkpoint version."""


class CheckpointCorruptionError(RuntimeError):
    """Raised when checkpoint metadata or a run snapshot is malformed."""


def _safe_run_id(run_id: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9._-]+", run_id):
        raise ValueError("run_id contains unsupported characters")
    return run_id


class JsonCheckpointStore:
    """Crash-conscious teaching checkpoint store.

    The constructor keeps the historical ``checkpoint.json`` API, but stores
    each run in ``checkpoint.d/<run_id>.json`` and uses ``checkpoint.json`` as
    an atomic pointer to the most recently saved run.  Every run snapshot has a
    monotonically increasing version and ``save`` supports compare-and-swap.

    Durability boundary (Linux/macOS): temporary file -> fsync(file) ->
    os.replace -> fsync(parent directory).  A process lock serializes writers.
    This is intentionally small and inspectable; it is not a distributed
    checkpoint database and does not provide cross-host consensus/fencing.
    """

    def __init__(self, path: str | Path | None = None):
        if path is None:
            path = Path(os.environ.get("AGENTLAB_HOME", ".agentlab")) / "checkpoint.json"
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.runs_dir = self.path.parent / f"{self.path.stem}.d"
        self.runs_dir.mkdir(parents=True, exist_ok=True)
        self.lock_path = self.path.parent / f".{self.path.name}.lock"

    @contextmanager
    def _lock(self) -> Iterator[None]:
        self.lock_path.touch(exist_ok=True)
        with self.lock_path.open("r+", encoding="utf-8") as lock_file:
            if fcntl is not None:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                if fcntl is not None:
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)

    @staticmethod
    def _fsync_dir(path: Path) -> None:
        flags = getattr(os, "O_DIRECTORY", 0) | os.O_RDONLY
        fd = os.open(path, flags)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)

    @classmethod
    def _atomic_write_json(cls, path: Path, obj: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2)
        fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(payload)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, path)
            cls._fsync_dir(path.parent)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)

    def _run_path(self, run_id: str) -> Path:
        return self.runs_dir / f"{_safe_run_id(run_id)}.json"

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        try:
            obj = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise CheckpointCorruptionError(f"invalid checkpoint {path}: {exc}") from exc
        if not isinstance(obj, dict):
            raise CheckpointCorruptionError(f"checkpoint {path} is not an object")
        return obj

    def save(self, run_id: str, state: dict[str, Any], *, expected_version: int | None = None) -> int:
        """Atomically persist one run and return its new checkpoint version.

        If ``expected_version`` is supplied, a stale writer fails closed instead
        of silently overwriting a newer state.
        """
        run_path = self._run_path(run_id)
        with self._lock():
            current = 0
            if run_path.exists():
                existing = self._read_json(run_path)
                current = int(existing.get("version", 0))
                if existing.get("run_id") != run_id:
                    raise CheckpointCorruptionError("run snapshot identity mismatch")
            if expected_version is not None and expected_version != current:
                raise CheckpointConflictError(
                    f"checkpoint CAS failed for {run_id}: expected={expected_version} current={current}"
                )
            version = current + 1
            snapshot = {"run_id": run_id, "version": version, "state": state}
            self._atomic_write_json(run_path, snapshot)
            self._atomic_write_json(self.path, {"latest_run_id": run_id, "version": version})
            return version

    def load(self, run_id: str | None = None) -> dict[str, Any] | None:
        """Load a specific run or, for compatibility, the latest saved run."""
        with self._lock():
            if run_id is None:
                if not self.path.exists():
                    return None
                pointer = self._read_json(self.path)
                # Read-only compatibility with the legacy single-file format.
                if "run_id" in pointer and "state" in pointer:
                    pointer.setdefault("version", 0)
                    return pointer
                run_id = pointer.get("latest_run_id")
                if not isinstance(run_id, str):
                    raise CheckpointCorruptionError("latest checkpoint pointer has no run id")
            run_path = self._run_path(run_id)
            if not run_path.exists():
                return None
            snapshot = self._read_json(run_path)
            if snapshot.get("run_id") != run_id or not isinstance(snapshot.get("state"), dict):
                raise CheckpointCorruptionError("run snapshot identity/state mismatch")
            if not isinstance(snapshot.get("version"), int):
                raise CheckpointCorruptionError("run snapshot version is missing")
            return snapshot
