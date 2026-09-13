from __future__ import annotations
import datetime
import hashlib
import json
import os
import platform
import re
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


def digest_parts(parts) -> str:
    h = hashlib.sha256()
    for part in parts:
        h.update(len(part).to_bytes(8, "big"))
        h.update(part)
    return h.hexdigest()


def epub_payload_fingerprint(path: Path) -> str:
    """Hash the EPUB payload, not ZIP container metadata.

    Pandoc versions differ in whether ZIP entry timestamps and the EPUB
    modification field honor SOURCE_DATE_EPOCH.  Neither changes the document
    readers consume.  Member names, order-independent member bytes, and every
    other metadata field remain part of the comparison.
    """
    fixed = datetime.datetime.fromtimestamp(EPOCH, datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ").encode()
    modified = re.compile(
        rb'(<meta\b[^>]*\bproperty=["\']dcterms:modified["\'][^>]*>)[^<]*(</meta>)',
        re.IGNORECASE,
    )
    parts = []
    with zipfile.ZipFile(path) as archive:
        bad = archive.testzip()
        if bad:
            raise SystemExit(f"CLEAN_REBUILD_EPUB_CRC_FAILED path={path} member={bad}")
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise SystemExit(f"CLEAN_REBUILD_EPUB_DUPLICATE_MEMBER path={path}")
        for name in sorted(names):
            data = archive.read(name)
            if Path(name).suffix.lower() in {".html", ".opf", ".xhtml", ".xml"}:
                data = modified.sub(lambda match: match.group(1) + fixed + match.group(2), data)
            parts.extend((name.encode("utf-8"), data))
    return "epub-payload-v1:" + digest_parts(parts)


def pdf_semantic_fingerprint(path: Path) -> str:
    """Compare PDF structure, selectable text, and every rendered page.

    Raw PDF bytes can contain writer-private ordering or build-path data even
    after dates and trailer IDs are fixed.  The release's dedicated PDF QA
    validates book structure; this projection additionally makes two clean
    builds agree on public metadata, layout text, and a full-document raster.
    """
    info = subprocess.run(["pdfinfo", str(path)], capture_output=True, check=True).stdout
    stable_info = b"\n".join(
        line for line in info.splitlines() if not line.lower().startswith(b"file size:")
    )
    text = subprocess.run(["pdftotext", "-layout", str(path), "-"], capture_output=True, check=True).stdout
    with tempfile.TemporaryDirectory() as rendered:
        prefix = Path(rendered) / "page"
        subprocess.run(
            ["pdftoppm", "-gray", "-r", "24", str(path), str(prefix)],
            capture_output=True,
            check=True,
        )
        pages = sorted(Path(rendered).glob("page-*.pgm"))
        if not pages:
            raise SystemExit(f"CLEAN_REBUILD_PDF_RENDER_EMPTY path={path}")
        raster_parts = []
        for page in pages:
            raster_parts.extend((page.name.encode(), bytes.fromhex(sha(page))))
        raster = bytes.fromhex(digest_parts(raster_parts))
    return "pdf-semantic-v1:" + digest_parts((stable_info, text, raster))


def artifact_fingerprint(path: Path) -> str:
    if path.suffix.lower() == ".epub":
        return epub_payload_fingerprint(path)
    if path.suffix.lower() == ".pdf":
        return pdf_semantic_fingerprint(path)
    return "sha256:" + sha(path)


def tree_hash(root: Path, rel: Path) -> dict[str, str]:
    base = root / rel
    if not base.exists():
        return {}
    return {
        p.relative_to(root).as_posix(): artifact_fingerprint(p)
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
    # extraction therefore uses this verifier's exact interpreter, its own
    # virtual environment, and an isolated cache that is empty at the start of
    # the run.  In particular, do not inherit the publisher container's
    # UV_PROJECT_ENVIRONMENT: doing so would make both clean extractions share
    # the outer release environment instead of testing independent rebuilds.
    clean_venv = repo / ".venv"
    env["UV_PROJECT_ENVIRONMENT"] = str(clean_venv)
    env.pop("VIRTUAL_ENV", None)
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
    py = clean_venv / "bin/python"
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


def main():
    if not SOURCE.exists():
        raise SystemExit(f"MISSING_SOURCE_CLEAN {SOURCE}")
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
            "schema_version": 2,
            "status": "SAME_HOST_CLEAN_REBUILD_EQUIVALENCE_OK",
            "generated_at_utc": datetime.datetime.now(datetime.UTC).isoformat(),
            "claim_scope": "same_host_same_toolchain_two_cold_caches_format_aware",
            "comparison_policy": {
                "pdf": "pdfinfo_without_file_size_plus_layout_text_plus_all_pages_gray_24dpi",
                "epub": "sorted_member_names_and_payloads_with_dcterms_modified_pinned_to_source_date_epoch",
                "other": "byte_exact_sha256",
            },
            "source_archive": SOURCE.name,
            "source_archive_sha256": sha(SOURCE),
            "python": platform.python_version(),
            "platform": platform.platform(),
            "machine": platform.machine(),
            "artifact_count": len(da),
            "artifact_tree_sha256": hashlib.sha256(canonical).hexdigest(),
            "artifact_fingerprints": da,
        }
        evidence = ROOT / "validation_logs/same-host-clean-rebuild.json"
        evidence.parent.mkdir(parents=True, exist_ok=True)
        evidence.write_text(
            json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
        kinds = {"raw": 0, "pdf_semantic": 0, "epub_payload": 0}
        for value in da.values():
            if value.startswith("pdf-semantic-v1:"):
                kinds["pdf_semantic"] += 1
            elif value.startswith("epub-payload-v1:"):
                kinds["epub_payload"] += 1
            else:
                kinds["raw"] += 1
        print(
            f"SAME_HOST_CLEAN_REBUILD_EQUIVALENCE_OK artifacts={len(da)} "
            f"raw_sha256={kinds['raw']} pdf_semantic={kinds['pdf_semantic']} "
            f"epub_payload={kinds['epub_payload']} scope=format_aware_same_host "
            f"source={SOURCE.name}"
        )


if __name__ == "__main__":
    main()
