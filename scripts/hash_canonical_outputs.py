from __future__ import annotations

import argparse
import hashlib
import json
import platform
from pathlib import Path

from common import ROOT


ROOTS = (Path("book/build"), Path("workbook/build"), Path("slides"), Path("site"))
SUFFIXES = {".css", ".epub", ".html", ".js", ".pdf", ".png", ".pptx", ".svg"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


parser = argparse.ArgumentParser()
parser.add_argument("--producer", required=True)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()

artifacts: dict[str, str] = {}
for relative_root in ROOTS:
    absolute_root = ROOT / relative_root
    if not absolute_root.exists():
        continue
    for path in sorted(absolute_root.rglob("*")):
        if path.is_file() and path.suffix.lower() in SUFFIXES:
            artifacts[path.relative_to(ROOT).as_posix()] = sha256(path)
if not artifacts:
    raise SystemExit("CANONICAL_HASH_NO_ARTIFACTS")
report = {
    "schema_version": 1,
    "producer": args.producer,
    "host": {"platform": platform.platform(), "machine": platform.machine()},
    "artifacts": artifacts,
}
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(f"CANONICAL_HASH_OK producer={args.producer} files={len(artifacts)}")
