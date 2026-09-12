from __future__ import annotations
import hashlib
import tempfile
from pathlib import Path
from build_release import build


def digest_dir(p: Path):
    return {x.name: hashlib.sha256(x.read_bytes()).hexdigest() for x in sorted(p.iterdir()) if x.is_file()}


with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
    pa = Path(a)
    pb = Path(b)
    build(pa)
    build(pb)
    da = digest_dir(pa)
    db = digest_dir(pb)
    if da != db:
        print("DETERMINISTIC_PACKAGING_FAILED")
        for k in sorted(set(da) | set(db)):
            if da.get(k) != db.get(k):
                print(k, da.get(k), db.get(k))
        raise SystemExit(1)
    print(f"DETERMINISTIC_PACKAGING_OK files={len(da)} scope=same_source_tree_packaging_only")
