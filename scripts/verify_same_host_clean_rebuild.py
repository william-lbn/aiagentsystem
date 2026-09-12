from __future__ import annotations
import datetime
import hashlib
import json
import os
import platform
import shutil
import subprocess
import tempfile
import time
import zipfile
import sys
from pathlib import Path
from common import ROOT, course, build_cfg

VERSION = course()["version"]
CFG = build_cfg()
EPOCH = int(CFG["source_date_epoch"])
SOURCE = ROOT / "dist/release" / f"AI-Agent-Systems-Course-{VERSION}-SOURCE-CLEAN.zip"
if not SOURCE.exists():
    raise SystemExit(f"MISSING_SOURCE_CLEAN {SOURCE}")

# Scope: two clean extractions of the exact SOURCE-CLEAN archive, rebuilt on
# this same host and installed toolchain.  This is stronger than packaging
# determinism but deliberately narrower than cross-host/hermetic reproducibility.
SURFACES = ("book", "site", "workbook", "slides")
ARTIFACT_DIRS = (Path("book/build"), Path("workbook/build"), Path("slides"), Path("site"))
SUFFIXES = (".pdf", ".html", ".epub", ".pptx", ".svg", ".png", ".css", ".js")


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def tree_hash(root: Path, rel: Path) -> dict[str, str]:
    base = root / rel
    if not base.exists():
        return {}
    return {
        p.relative_to(root).as_posix(): sha(p)
        for p in sorted(base.rglob("*"))
        if p.is_file() and p.suffix.lower() in SUFFIXES
    }


def run_one(dest: Path, label: str) -> dict[str, str]:
    with zipfile.ZipFile(SOURCE) as z:
        if z.testzip():
            raise SystemExit(f"SOURCE_CLEAN_CRC_FAILED {label}")
        z.extractall(dest)
    candidates = [p for p in dest.iterdir() if p.is_dir()]
    if len(candidates) != 1:
        raise RuntimeError(f"unexpected archive root: {candidates}")
    repo = candidates[0]
    env = os.environ.copy()
    env["SOURCE_DATE_EPOCH"] = str(EPOCH)
    env["PYTHONUNBUFFERED"] = "1"
    # Keep the dependency cache cold, but allow enough time for a public
    # package CDN to deliver larger wheels on slower or rate-limited links.
    # This changes transport tolerance only; package identities and hashes
    # remain fixed by uv.lock.
    env["UV_HTTP_TIMEOUT"] = "120"
    # A same-host comparison must not silently switch Python versions. Each
    # extraction therefore uses this verifier's exact interpreter and an
    # isolated cache that is empty at the start of the run.
    env["UV_CACHE_DIR"] = str(dest / "uv-cache")
    if platform.system() == "Darwin" and platform.machine() == "arm64":
        # A Rosetta-installed uv can otherwise launch native builds as x86_64
        # even when --python points at an arm64 interpreter.
        env["ARCHFLAGS"] = "-arch arm64"
    logdir = repo / "validation_logs"
    logdir.mkdir(exist_ok=True)
    sibling_uv = Path(sys.executable).with_name("uv")
    uv = str(sibling_uv) if sibling_uv.exists() else shutil.which("uv")
    if uv is None:
        raise SystemExit("CLEAN_REBUILD_MISSING_UV")
    bootstrap_log = logdir / f"clean-rebuild-{label}-bootstrap.log"
    command = [
        uv,
        "sync",
        "--locked",
        "--no-default-groups",
        "--group",
        "publish",
        "--no-install-project",
        "--python",
        sys.executable,
    ]
    bootstrap = None
    max_bootstrap_attempts = 3
    with bootstrap_log.open("w", encoding="utf-8") as out:
        for attempt in range(1, max_bootstrap_attempts + 1):
            out.write(f"CLEAN_REBUILD_BOOTSTRAP_ATTEMPT {attempt}/{max_bootstrap_attempts}\n")
            out.flush()
            try:
                bootstrap = subprocess.run(
                    command,
                    cwd=repo,
                    env=env,
                    text=True,
                    stdout=out,
                    stderr=subprocess.STDOUT,
                    timeout=900,
                )
            except subprocess.TimeoutExpired:
                out.write(f"CLEAN_REBUILD_BOOTSTRAP_ATTEMPT_TIMEOUT seconds=900 attempt={attempt}\n")
                out.flush()
                if attempt == max_bootstrap_attempts:
                    print(bootstrap_log.read_text(encoding="utf-8", errors="replace")[-12000:])
                    raise SystemExit(
                        f"CLEAN_REBUILD_BOOTSTRAP_TIMEOUT label={label} seconds=900 attempts={max_bootstrap_attempts}"
                    ) from None
                continue
            if bootstrap.returncode == 0:
                break
            out.write(f"CLEAN_REBUILD_BOOTSTRAP_ATTEMPT_FAILED rc={bootstrap.returncode} attempt={attempt}\n")
            out.flush()
    if bootstrap is None:
        raise SystemExit(f"CLEAN_REBUILD_BOOTSTRAP_NO_RESULT label={label}")
    print("CLEAN_REBUILD_DEPENDENCY_SCOPE groups=publish project=runtime cache=cold", flush=True)
    print(f"CLEAN_REBUILD_BOOTSTRAP label={label} rc={bootstrap.returncode}", flush=True)
    if bootstrap.returncode:
        print(bootstrap_log.read_text(encoding="utf-8", errors="replace")[-12000:])
        raise SystemExit(
            f"CLEAN_REBUILD_BOOTSTRAP_FAILED label={label} rc={bootstrap.returncode} attempts={max_bootstrap_attempts}"
        )
    py = repo / ".venv/bin/python"
    if not py.exists():
        raise SystemExit(f"CLEAN_REBUILD_PYTHON_MISSING label={label} path={py}")
    audit_code = (
        "import platform\n"
        "from lxml import etree\n"
        "from PIL import Image\n"
        "from pptx import Presentation\n"
        "from pydantic_core import __version__ as pydantic_core_version\n"
        'print("NATIVE_IMPORT_AUDIT_OK", platform.machine(), '
        "etree.LXML_VERSION, Image.__version__, pydantic_core_version)\n"
    )
    with bootstrap_log.open("a", encoding="utf-8") as out:
        audit = subprocess.run(
            [py, "-c", audit_code], cwd=repo, env=env, text=True, stdout=out, stderr=subprocess.STDOUT
        )
    print(f"CLEAN_REBUILD_NATIVE_AUDIT label={label} rc={audit.returncode}", flush=True)
    if audit.returncode:
        print(bootstrap_log.read_text(encoding="utf-8", errors="replace")[-12000:])
        raise SystemExit(f"CLEAN_REBUILD_NATIVE_AUDIT_FAILED label={label} rc={audit.returncode}")
    timing = []
    for surface in SURFACES:
        logfile = logdir / f"clean-rebuild-{label}-{surface}.log"
        start = time.monotonic()
        with logfile.open("w", encoding="utf-8") as out:
            proc = subprocess.run(
                ["make", f"PYTHON={py}", "PUBLISH_ENGINE=pandoc", surface],
                cwd=repo,
                env=env,
                text=True,
                stdout=out,
                stderr=subprocess.STDOUT,
                timeout=600,
            )
        elapsed = time.monotonic() - start
        timing.append((surface, elapsed, proc.returncode))
        print(
            f"CLEAN_REBUILD_STAGE label={label} surface={surface} rc={proc.returncode} seconds={elapsed:.2f}",
            flush=True,
        )
        if proc.returncode:
            print(logfile.read_text(encoding="utf-8", errors="replace")[-12000:])
            raise SystemExit(f"CLEAN_REBUILD_FAILED label={label} surface={surface} rc={proc.returncode}")
    artifacts = {}
    for rel in ARTIFACT_DIRS:
        artifacts.update(tree_hash(repo, rel))
    if not artifacts:
        raise SystemExit(f"CLEAN_REBUILD_NO_ARTIFACTS {label}")
    return artifacts


with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
    da = run_one(Path(a), "A")
    db = run_one(Path(b), "B")
    if da != db:
        print("SAME_HOST_CLEAN_REBUILD_EQUIVALENCE_FAILED")
        for k in sorted(set(da) | set(db)):
            if da.get(k) != db.get(k):
                print(k, da.get(k), db.get(k))
        raise SystemExit(1)
    canonical = json.dumps(da, sort_keys=True, separators=(",", ":")).encode()
    report = {
        "schema_version": 1,
        "status": "SAME_HOST_CLEAN_REBUILD_EQUIVALENCE_OK",
        "generated_at_utc": datetime.datetime.now(datetime.UTC).isoformat(),
        "claim_scope": "same_host_same_toolchain_two_cold_caches",
        "source_archive": SOURCE.name,
        "source_archive_sha256": sha(SOURCE),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "artifact_count": len(da),
        "artifact_tree_sha256": hashlib.sha256(canonical).hexdigest(),
        "artifact_hashes": da,
    }
    evidence = ROOT / "validation_logs/same-host-clean-rebuild.json"
    evidence.parent.mkdir(parents=True, exist_ok=True)
    evidence.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(f"SAME_HOST_CLEAN_REBUILD_EQUIVALENCE_OK files={len(da)} scope=same_host_same_toolchain source={SOURCE.name}")
