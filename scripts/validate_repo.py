from __future__ import annotations

import json
import re
import subprocess

from common import ROOT, course, build_cfg

meta = course()
cfg = build_cfg()
version = meta["version"]
assert re.fullmatch(r"v\d+\.\d+\.\d+", version), version

required = [
    "README.md",
    "LICENSE",
    "LICENSING.md",
    "THIRD_PARTY_NOTICES.md",
    "AUTHORS.md",
    "CITATION.cff",
    "DCO",
    "CODE_OF_CONDUCT.md",
    "CONTRIBUTING.md",
    "GOVERNANCE.md",
    "SECURITY.md",
    "SUPPORT.md",
    "RELEASING.md",
    "EXPERIMENT_STATUS.md",
    "course.toml",
    "pyproject.toml",
    "uv.lock",
    "Dockerfile.builder",
    ".github/CODEOWNERS",
    ".github/PULL_REQUEST_TEMPLATE.md",
    ".github/dependabot.yml",
    ".github/workflows/ci.yml",
    ".github/workflows/codeql.yml",
    ".github/workflows/release.yml",
    "book/zh/SUMMARY.md",
    "book/zh/book.md",
    f"book/build/ai-agent-systems-course-{version}.pdf",
    f"book/build/ai-agent-systems-course-{version}.html",
    f"book/build/ai-agent-systems-course-{version}.epub",
    f"slides/AI-Agent-Systems-Course-{version}.pptx",
    f"workbook/build/agent-systems-lab-workbook-{version}.pdf",
    "site/index.html",
    "integrations/SOURCE_LOCK.json",
]
for required_path in required:
    path = ROOT / required_path
    assert path.exists() and path.stat().st_size > 0, required_path

assert len(list((ROOT / "book/zh/chapters").glob("*.md"))) == cfg["expected_chapters"]
assert len(list((ROOT / "labs/core").glob("*.md"))) == cfg["expected_core_labs"]
assert len(list((ROOT / "examples/chapters").glob("ch*.py"))) == cfg["expected_chapter_examples"]
assert len(list((ROOT / "examples").glob("*.py"))) >= cfg["expected_support_examples"]
assert len(list((ROOT / "book/assets/diagrams").glob("*.svg"))) == cfg["expected_diagrams"]

pdf = ROOT / f"book/build/ai-agent-systems-course-{version}.pdf"
output = subprocess.run(["pdfinfo", str(pdf)], text=True, capture_output=True, check=True).stdout
match = re.search(r"^Pages:\s+(\d+)", output, re.MULTILINE)
assert match is not None
pages = int(match.group(1))
assert pages >= cfg["pdf_min_pages"], pages

locks = json.loads((ROOT / "integrations/SOURCE_LOCK.json").read_text(encoding="utf-8"))
assert len(locks) >= cfg["expected_source_locks"], len(locks)
assert len(list((ROOT / "site").rglob("*.html"))) == cfg["expected_site_pages"]
print(
    f"VALIDATION_OK version={version} build_system={cfg['system_version']} "
    f"chapters={cfg['expected_chapters']} labs={cfg['expected_core_labs']} "
    f"chapter_examples={cfg['expected_chapter_examples']} pdf_pages={pages} source_locks={len(locks)}"
)
