from __future__ import annotations
import subprocess
import sys
from common import ROOT, build_cfg, pdf_cfg, summary_parts

cfg = build_cfg()
pdf = pdf_cfg()
subprocess.run([sys.executable, str(ROOT / "scripts/prepare_quarto.py"), "all"], check=True)
errors = []


def req(c, m):
    if not c:
        errors.append(m)


base = ROOT / ".build/quarto"
book = (base / "book/_quarto.yml").read_text(encoding="utf-8")
site = (base / "site/_quarto.yml").read_text(encoding="utf-8")
wb = (base / "workbook/_quarto.yml").read_text(encoding="utf-8")
req(book.count("book/zh/chapters/") == cfg["expected_chapters"], f"book chapter refs={book.count('book/zh/chapters/')}")
req(book.count("book/zh/appendix-") == cfg["expected_appendices"], f"book appendices={book.count('book/zh/appendix-')}")
req(book.count("    - part:") == len(summary_parts()), f"book part refs={book.count('    - part:')}")
req('    - "preface.qmd"' in book, "book preface missing")
req(f'documentclass: "{pdf.get("documentclass", "ctexbook")}"' in book, "book PDF documentclass mismatch")
req(f"    toc-depth: {int(pdf.get('toc_depth', 1))}" in book, "book PDF toc-depth mismatch")
req("book/assets/latex/book-style.tex" in book, "book style include missing")
req("scripts/filters/book_structure.lua" in book, "book structure filter missing")
req(site.count("book/zh/chapters/") == cfg["expected_chapters"], f"site chapter refs={site.count('book/zh/chapters/')}")
req(
    site.count("book/zh/appendix-") == cfg["expected_appendices"],
    f"site appendix refs={site.count('book/zh/appendix-')}",
)
req(site.count("labs/core/lab-") == cfg["expected_core_labs"], f"site lab refs={site.count('labs/core/lab-')}")
req(wb.count("labs/core/lab-") == cfg["expected_core_labs"], f"workbook lab refs={wb.count('labs/core/lab-')}")
req("book/assets/latex/workbook-style.tex" in wb, "workbook style include missing")
req(str(cfg["quarto_version"]) not in book, "generated Quarto project must not duplicate tool version")
if errors:
    print("QUARTO_CONFIG_QA_FAILED")
    [print("-", e) for e in errors]
    raise SystemExit(1)
print(
    "QUARTO_CONFIG_QA_OK chapters=",
    cfg["expected_chapters"],
    "parts=",
    len(summary_parts()),
    "labs=",
    cfg["expected_core_labs"],
)
