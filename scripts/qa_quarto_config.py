from __future__ import annotations
import datetime
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
req('    - "index.qmd"' in book, "book index/home page missing")
req((base / "book/index.qmd").is_file(), "book index/home page was not generated")
req(f'documentclass: "{pdf.get("documentclass", "ctexbook")}"' in book, "book PDF documentclass mismatch")
req(f"    toc-depth: {int(pdf.get('toc_depth', 1))}" in book, "book PDF toc-depth mismatch")
req("    latex-auto-install: false" in book, "book must fail closed instead of mutating TeX during render")
req('    babel-lang: "chinese"' in book, "book PDF must override Babel's invalid chinese-hans control name")
req("book/assets/latex/book-style.tex" in book, "book style include missing")
req('      - "reproducible-pdf.tex"' in book, "book reproducible PDF header missing")
req((base / "book/reproducible-pdf.tex").is_file(), "book reproducible PDF header was not generated")
req("scripts/filters/book_structure.lua" in book, "book structure filter missing")
site_lines = site.splitlines()
site_chapter_refs = sum(line.startswith('      - "book/zh/chapters/') for line in site_lines)
site_appendix_refs = sum(line.startswith('      - "book/zh/appendix-') for line in site_lines)
site_lab_refs = sum(line.startswith('      - "labs/core/lab-') for line in site_lines)
req(site_chapter_refs == cfg["expected_chapters"], f"site chapter refs={site_chapter_refs}")
req(
    site_appendix_refs == cfg["expected_appendices"],
    f"site appendix refs={site_appendix_refs}",
)
req(site_lab_refs == cfg["expected_core_labs"], f"site lab refs={site_lab_refs}")
for render_target in (
    '    - "index.qmd"',
    '    - "book/zh/chapters/*.md"',
    '    - "book/zh/appendix-*.md"',
    '    - "labs/core/*.md"',
):
    req(render_target in site, f"site explicit render target missing: {render_target.strip()}")
req(wb.count("labs/core/lab-") == cfg["expected_core_labs"], f"workbook lab refs={wb.count('labs/core/lab-')}")
req('    - "index.qmd"' in wb, "workbook index/home page missing")
req((base / "workbook/index.qmd").is_file(), "workbook index/home page was not generated")
req("book/assets/latex/workbook-style.tex" in wb, "workbook style include missing")
req('      - "reproducible-pdf.tex"' in wb, "workbook reproducible PDF header missing")
req((base / "workbook/reproducible-pdf.tex").is_file(), "workbook reproducible PDF header was not generated")
req("    latex-auto-install: false" in wb, "workbook must fail closed instead of mutating TeX during render")
req('    babel-lang: "chinese"' in wb, "workbook PDF must override Babel's invalid chinese-hans control name")
req(str(cfg["quarto_version"]) not in book, "generated Quarto project must not duplicate tool version")
stamp = datetime.datetime.fromtimestamp(int(cfg["source_date_epoch"]), datetime.timezone.utc).strftime("D:%Y%m%d%H%M%SZ")
for target in ("book", "workbook"):
    header = (base / target / "reproducible-pdf.tex").read_text(encoding="utf-8")
    req("pdfcreationdate={" + stamp + "}" in header, f"{target} Hyperref date does not derive from SOURCE_DATE_EPOCH")
    req("/CreationDate (" + stamp + ")" in header, f"{target} PDF Info date does not derive from SOURCE_DATE_EPOCH")
    req("pdf:trailerid" in header, f"{target} deterministic PDF trailer ID missing")
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
