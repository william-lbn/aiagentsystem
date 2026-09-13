from __future__ import annotations
import zipfile
import re
from common import ROOT, course

v = course()["version"]
p = ROOT / "dist/release" / f"AI-Agent-Systems-Course-{v}-SOURCE-CLEAN.zip"
if not p.exists():
    raise SystemExit(f"MISSING {p}")
forbidden = [
    r"/book/build/",
    r"/workbook/build/",
    r"/site/",
    r"/dist/",
    r"/validation_logs/",
    r"/\.build/",
    r"/\.venv/",
    r"/\.ruff_cache/",
    r"/\.mypy_cache/",
    r"/\.hypothesis/",
    r"/\.(?:nox|tox|idea|vscode|codex|agents)/",
    r"/node_modules/",
    r"/htmlcov/",
    r"/__pycache__/",
    r"/\.coverage(?:\.[^/]*)?$",
    r"/\.DS_Store$",
    r"/\.env$",
    r"/\.env\.(?!example$)[^/]+$",
    r"/book/zh/book\.md$",
    r"/slides/.*\.(pptx|pdf)$",
    r"/book/assets/diagrams/pdf/",
    r"/book/assets/diagrams/.*\.png$",
]
with zipfile.ZipFile(p) as z:
    names = z.namelist()
    bad = [n for n in names if any(re.search(x, n) for x in forbidden)]
    crc = z.testzip()
if crc or bad:
    print("SOURCE_CLEAN_FAILED", crc, bad[:20])
    raise SystemExit(1)
print(f"SOURCE_CLEAN_OK files={len(names)}")
