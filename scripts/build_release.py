from __future__ import annotations
import argparse
import hashlib
import json
import os
import time
import zipfile
from pathlib import Path
from common import ROOT, course, build_cfg

META = course()
CFG = build_cfg()
VERSION = META["version"]
EPOCH = int(CFG["source_date_epoch"])
DT = time.gmtime(EPOCH)[:6]
CACHE_PARTS = {
    ".agentlab",
    ".agents",
    ".build",
    ".codex",
    ".git",
    ".hypothesis",
    ".idea",
    ".mypy_cache",
    ".nox",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    ".vscode",
    "__pycache__",
    "dist",
    "htmlcov",
    "node_modules",
}
RUNTIME_NAMES = {"agentops.db", ".coverage", ".DS_Store"}
CURRENT_PUBLICATION_FILES = {
    f"book/build/ai-agent-systems-course-{VERSION}.epub",
    f"book/build/ai-agent-systems-course-{VERSION}.html",
    f"book/build/ai-agent-systems-course-{VERSION}.pdf",
    f"slides/AI-Agent-Systems-Course-{VERSION}.pdf",
    f"slides/AI-Agent-Systems-Course-{VERSION}.pptx",
    f"workbook/build/agent-systems-lab-workbook-{VERSION}.epub",
    f"workbook/build/agent-systems-lab-workbook-{VERSION}.html",
    f"workbook/build/agent-systems-lab-workbook-{VERSION}.pdf",
}


def skip_common(rel: Path) -> bool:
    private_env = rel.name == ".env" or (rel.name.startswith(".env.") and rel.name != ".env.example")
    coverage_shard = rel.name.startswith(".coverage.")
    return (
        any(part in CACHE_PARTS for part in rel.parts)
        or rel.name in RUNTIME_NAMES
        or private_env
        or coverage_shard
        or rel.suffix in {".pyc", ".pyo"}
    )


def skip_stale_publication(rel: Path) -> bool:
    value = rel.as_posix()
    if value.startswith(("book/build/", "workbook/build/")):
        return value not in CURRENT_PUBLICATION_FILES
    if value.startswith("slides/") and rel.suffix.lower() in {".pdf", ".pptx"}:
        return value not in CURRENT_PUBLICATION_FILES
    return False


def full_release_skip(rel: Path) -> bool:
    return skip_common(rel) or skip_stale_publication(rel)


def source_clean_skip(rel: Path) -> bool:
    s = rel.as_posix()
    if skip_common(rel):
        return True
    if s in {"book/zh/book.md", "MANIFEST.md"}:
        return True
    if s.startswith(
        ("book/build/", "workbook/build/", "site/", "validation_logs/", "qa/", "book/assets/diagrams/pdf/")
    ):
        return True
    if s.startswith("slides/") and rel.suffix.lower() in {".pptx", ".pdf"}:
        return True
    if s.startswith("book/assets/diagrams/") and rel.suffix.lower() == ".png":
        return True
    return False


def zi(name: str) -> zipfile.ZipInfo:
    z = zipfile.ZipInfo(name, DT)
    z.create_system = 3
    z.external_attr = 0o100644 << 16
    z.compress_type = zipfile.ZIP_DEFLATED
    return z


def add_file(z: zipfile.ZipFile, p: Path, arc: str):
    z.writestr(zi(arc), p.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)


def zip_tree(target: Path, predicate, prefix="AI-Agent-Systems-Course"):
    with zipfile.ZipFile(target, "w") as z:
        for p in sorted(ROOT.rglob("*"), key=lambda x: x.relative_to(ROOT).as_posix()):
            if not p.is_file():
                continue
            rel = p.relative_to(ROOT)
            if predicate(rel):
                continue
            add_file(z, p, f"{prefix}/{rel.as_posix()}")
    with zipfile.ZipFile(target) as z:
        bad = z.testzip()
        if bad:
            raise SystemExit(f"ZIP_CRC_FAIL {target.name} {bad}")


def zip_selected(target: Path, paths: list[Path]):
    files = []
    for base in paths:
        if not base.exists():
            continue
        if base.is_file():
            files.append(base)
        else:
            files.extend(p for p in base.rglob("*") if p.is_file())
    unique = sorted(set(files), key=lambda x: x.relative_to(ROOT).as_posix())
    with zipfile.ZipFile(target, "w") as z:
        for p in unique:
            rel = p.relative_to(ROOT)
            if skip_common(rel) or skip_stale_publication(rel):
                continue
            add_file(z, p, rel.as_posix())
    if zipfile.ZipFile(target).testzip():
        raise SystemExit(f"ZIP_CRC_FAIL {target.name}")


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def write_sums(path: Path, files: list[Path]):
    path.write_text("".join(f"{sha(p)}  {p.name}\n" for p in files), encoding="utf-8")


def build(dist: Path):
    dist.mkdir(parents=True, exist_ok=True)
    for p in dist.iterdir():
        if p.is_file():
            p.unlink()
    full = dist / f"AI-Agent-Systems-Course-{VERSION}-FULL.zip"
    zip_tree(full, full_release_skip)
    source = dist / f"AI-Agent-Systems-Course-{VERSION}-SOURCE-CLEAN.zip"
    zip_tree(source, source_clean_skip)
    book = dist / f"AI-Agent-Systems-Course-{VERSION}-BOOK.zip"
    zip_selected(
        book, [ROOT / "book/zh", ROOT / "book/assets", ROOT / "book/build", ROOT / "workbook/build", ROOT / "site"]
    )
    code = dist / f"AI-Agent-Systems-Course-{VERSION}-CODE-LABS.zip"
    zip_selected(
        code,
        [ROOT / "src", ROOT / "examples", ROOT / "labs", ROOT / "integrations", ROOT / "production", ROOT / "tests"],
    )
    slides = dist / f"AI-Agent-Systems-Course-{VERSION}-SLIDES.zip"
    zip_selected(slides, [ROOT / "slides"])
    qa = dist / f"AI-Agent-Systems-Course-{VERSION}-QA-EVIDENCE.zip"
    zip_selected(
        qa,
        [
            ROOT / "VALIDATION_REPORT.md",
            ROOT / "BASELINE_AUDIT.md",
            ROOT / "EXPERIMENT_STATUS.md",
            ROOT / "MANIFEST.md",
            ROOT / "validation_logs",
            ROOT / "toolchain.lock.json",
            ROOT / "builder.lock.json",
        ],
    )
    files = [full, source, book, code, slides, qa]
    metadata = {
        "course_version": VERSION,
        "build_system": CFG["system_version"],
        "source_date_epoch": EPOCH,
        "canonical_publisher": CFG["canonical_publisher"],
        "compatibility_publisher": CFG["compatibility_publisher"],
        "release_engine": os.environ.get("RELEASE_ENGINE", "pandoc-compatibility"),
        "artifacts": {p.name: sha(p) for p in files},
    }
    metadata_path = dist / "BUILD-METADATA.json"
    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    # ALL-DELIVERABLES cannot contain a checksum of itself.  Give the bundle a
    # component-only manifest, then create the external release manifest after
    # the bundle is complete so every other downloadable asset is covered.
    component_sums = dist / "COMPONENT-SHA256SUMS.txt"
    write_sums(component_sums, [*files, metadata_path])
    allzip = dist / f"AI-Agent-Systems-Course-{VERSION}-ALL-DELIVERABLES.zip"
    with zipfile.ZipFile(allzip, "w") as z:
        for p in sorted([*files, metadata_path, component_sums], key=lambda x: x.name):
            add_file(z, p, p.name)
    if zipfile.ZipFile(allzip).testzip():
        raise SystemExit("ALL_DELIVERABLES_CRC_FAIL")
    component_sums.unlink()
    sums_path = dist / "SHA256SUMS.txt"
    write_sums(sums_path, [*files, metadata_path, allzip])
    print("RELEASE_OK", allzip)
    return files + [sums_path, metadata_path, allzip]


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dist-dir", type=Path, default=ROOT / "dist/release")
    args = ap.parse_args()
    build(args.dist_dir)
