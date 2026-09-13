from __future__ import annotations

import re
import subprocess
from pathlib import Path, PurePosixPath

from common import ROOT


FORBIDDEN_ROOTS = {
    ".agentlab",
    ".build",
    ".idea",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    ".vscode",
    "book/build",
    "dist",
    "htmlcov",
    "site",
    "validation_logs",
    "workbook/build",
}
FORBIDDEN_EXACT = {
    ".coverage",
    ".DS_Store",
    "MANIFEST.md",
    "book/zh/book.md",
}
FORBIDDEN_SUFFIXES = {".key", ".pem", ".pyc", ".pyo"}
GENERATED_PATTERNS = (
    re.compile(r"^book/assets/diagrams/.+\.png$"),
    re.compile(r"^book/assets/diagrams/pdf/"),
    re.compile(r"^slides/.+\.(?:pdf|pptx)$"),
)
SECRET_PATTERNS = {
    "private key material": re.compile(rb"-----BEGIN (?:[A-Z0-9 ]+ )?PRIVATE KEY-----"),
    "OpenAI-style live key": re.compile(rb"\bsk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{20,}\b"),
    "GitHub token": re.compile(rb"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})\b"),
    "AWS access key": re.compile(rb"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
}
TEXT_SCAN_LIMIT = 2 * 1024 * 1024
MAX_TRACKED_FILE = 10 * 1024 * 1024


def tracked_paths() -> list[Path]:
    proc = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=ROOT,
        check=False,
        capture_output=True,
    )
    if proc.returncode:
        raise SystemExit("GIT_INDEX_QA_FAILED: repository index is unavailable")
    return [Path(raw.decode("utf-8")) for raw in proc.stdout.split(b"\0") if raw]


def is_forbidden(path: Path) -> bool:
    value = path.as_posix()
    pure = PurePosixPath(value)
    if value in FORBIDDEN_EXACT or pure.suffix.lower() in FORBIDDEN_SUFFIXES:
        return True
    if pure.name == ".DS_Store" or pure.name == ".env" or pure.name.startswith(".env."):
        return value != ".env.example"
    if any(value == root or value.startswith(f"{root}/") for root in FORBIDDEN_ROOTS):
        return True
    return any(pattern.search(value) for pattern in GENERATED_PATTERNS)


def main() -> int:
    errors: list[str] = []
    paths = tracked_paths()
    for relative in paths:
        value = relative.as_posix()
        absolute = ROOT / relative
        if is_forbidden(relative):
            errors.append(f"forbidden tracked path: {value}")
            continue
        if not absolute.is_file():
            continue
        size = absolute.stat().st_size
        if size > MAX_TRACKED_FILE:
            errors.append(f"tracked file exceeds 10 MiB: {value} ({size} bytes)")
        if size > TEXT_SCAN_LIMIT or b"\0" in absolute.read_bytes()[:8192]:
            continue
        content = absolute.read_bytes()
        for label, pattern in SECRET_PATTERNS.items():
            if pattern.search(content):
                errors.append(f"possible {label}: {value}")
    if errors:
        print("GIT_INDEX_QA_FAILED")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"GIT_INDEX_QA_OK tracked_files={len(paths)} max_file_bytes={MAX_TRACKED_FILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
