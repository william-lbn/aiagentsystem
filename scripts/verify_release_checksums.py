from __future__ import annotations

import argparse
import hashlib
import re
from pathlib import Path, PurePath

from common import ROOT


LINE = re.compile(r"^([0-9a-f]{64})  ([^/\\]+)$")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify(dist: Path) -> int:
    manifest = dist / "SHA256SUMS.txt"
    if not manifest.is_file():
        print(f"RELEASE_CHECKSUMS_FAILED missing={manifest}")
        return 1
    errors = []
    records = {}
    for number, line in enumerate(manifest.read_text(encoding="utf-8").splitlines(), 1):
        match = LINE.fullmatch(line)
        if not match:
            errors.append(f"line {number}: expected SHA-256 and basename only")
            continue
        expected, name = match.groups()
        if PurePath(name).name != name:
            errors.append(f"line {number}: path components are forbidden: {name}")
        elif name in records:
            errors.append(f"line {number}: duplicate entry: {name}")
        else:
            records[name] = expected
    assets = {path.name: path for path in dist.iterdir() if path.is_file() and path != manifest}
    missing = sorted(set(assets) - set(records))
    extra = sorted(set(records) - set(assets))
    if missing:
        errors.append(f"uncovered release assets: {missing}")
    if extra:
        errors.append(f"manifest entries without assets: {extra}")
    for name in sorted(set(records) & set(assets)):
        actual = sha256(assets[name])
        if actual != records[name]:
            errors.append(f"digest mismatch: {name} expected={records[name]} actual={actual}")
    if errors:
        print("RELEASE_CHECKSUMS_FAILED")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"RELEASE_CHECKSUMS_OK assets={len(assets)} manifest_entries={len(records)} basenames_only=true")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("dist", type=Path, nargs="?", default=ROOT / "dist/release")
    args = parser.parse_args()
    return verify(args.dist)


if __name__ == "__main__":
    raise SystemExit(main())
