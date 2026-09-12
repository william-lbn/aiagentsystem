from __future__ import annotations

from pathlib import Path
from typing import Any
import hashlib
import json
import os

try:  # Linux/macOS course environments.
    import fcntl
except ImportError:  # pragma: no cover
    fcntl = None  # type: ignore[assignment]

from .events import Event


class JournalCorruptionError(RuntimeError):
    """The existing evidence history cannot be trusted; appends must stop."""


class EffectJournal:
    """Append-only teaching evidence journal with hash-chain verification.

    This remains deliberately smaller than a database WAL, but it now fails
    closed on malformed/tampered history and serializes appenders on
    Linux/macOS.  Every append re-reads and verifies the durable chain while
    holding the file lock, so concurrent writers cannot extend stale heads.
    """

    def __init__(self, path: str | Path | None = None, *, fsync: bool = True):
        if path is None:
            path = Path(os.environ.get("AGENTLAB_HOME", ".agentlab")) / "effect_journal.jsonl"
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.fsync = fsync
        self.last_hash = "GENESIS"
        if self.path.exists():
            records = self.read(verify=True)
            if records:
                self.last_hash = records[-1]["hash"]

    @staticmethod
    def _canonical(prev: str, event: dict[str, Any]) -> str:
        return json.dumps({"prev": prev, "event": event}, sort_keys=True, ensure_ascii=False, separators=(",", ":"))

    @classmethod
    def _verify_records(cls, records: list[dict[str, Any]]) -> str:
        prev = "GENESIS"
        for idx, record in enumerate(records, 1):
            if not isinstance(record, dict) or "event" not in record:
                raise JournalCorruptionError(f"record {idx} is malformed")
            if record.get("prev") != prev:
                raise JournalCorruptionError(f"record {idx} prev hash mismatch")
            digest = hashlib.sha256(cls._canonical(prev, record["event"]).encode()).hexdigest()
            if digest != record.get("hash"):
                raise JournalCorruptionError(f"record {idx} hash mismatch")
            prev = digest
        return prev

    @staticmethod
    def _parse_lines(text: str) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        for idx, line in enumerate(text.splitlines(), 1):
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as exc:
                raise JournalCorruptionError(f"record {idx} is not valid JSON: {exc}") from exc
            if not isinstance(obj, dict):
                raise JournalCorruptionError(f"record {idx} is not an object")
            records.append(obj)
        return records

    @staticmethod
    def _fsync_dir(path: Path) -> None:
        flags = getattr(os, "O_DIRECTORY", 0) | os.O_RDONLY
        fd = os.open(path, flags)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)

    def append(self, event: Event) -> str:
        existed = self.path.exists()
        with self.path.open("a+", encoding="utf-8") as f:
            if fcntl is not None:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                f.seek(0)
                records = self._parse_lines(f.read())
                prev = self._verify_records(records)
                payload = event.to_dict()
                digest = hashlib.sha256(self._canonical(prev, payload).encode()).hexdigest()
                record = {"prev": prev, "hash": digest, "event": payload}
                f.seek(0, os.SEEK_END)
                f.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
                f.flush()
                if self.fsync:
                    os.fsync(f.fileno())
                self.last_hash = digest
            finally:
                if fcntl is not None:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        if self.fsync and not existed:
            self._fsync_dir(self.path.parent)
        return self.last_hash

    def read(self, *, verify: bool = False) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        with self.path.open("r", encoding="utf-8") as f:
            if fcntl is not None:
                fcntl.flock(f.fileno(), fcntl.LOCK_SH)
            try:
                records = self._parse_lines(f.read())
            finally:
                if fcntl is not None:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        if verify:
            self._verify_records(records)
        return records

    def verify(self) -> bool:
        try:
            self.read(verify=True)
            return True
        except JournalCorruptionError:
            return False
