from __future__ import annotations
import datetime
import re
import subprocess
import os
from common import ROOT, course, build_cfg, pdf_cfg

META = course()
CFG = build_cfg()
PDF = pdf_cfg()
errors = []
UTC_ENV = {**os.environ, "TZ": "UTC"}


def req(c, m):
    if not c:
        errors.append(m)


pdf = ROOT / "workbook/build" / f"agent-systems-lab-workbook-{META['version']}.pdf"
req(pdf.exists(), "workbook PDF missing")
pages_n = 0
if pdf.exists():
    # Poppler renders PDF dates in the caller's local timezone. Normalize the
    # inspection process before comparing with SOURCE_DATE_EPOCH.
    info = subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True, check=True, env=UTC_ENV).stdout
    m = re.search(r"^Pages:\s+(\d+)", info, re.M)
    pages_n = int(m.group(1)) if m else 0
    req(pages_n >= 80, f"workbook pages={pages_n} < 80")
    req("(A4)" in info, "workbook PDF must be A4")
    epoch = int(CFG["source_date_epoch"])
    expected = datetime.datetime.fromtimestamp(epoch, datetime.timezone.utc).strftime("%a %b %d %H:%M:%S %Y UTC")
    actual_creation = re.search(r"^CreationDate:\s+(.+)$", info, re.M)
    actual_creation_text = actual_creation.group(1).strip() if actual_creation else "MISSING"
    req(
        actual_creation_text == expected,
        f"workbook CreationDate={actual_creation_text!r} must derive from SOURCE_DATE_EPOCH ({expected})",
    )

    cp = subprocess.run(["pdftotext", "-layout", str(pdf), "-"], capture_output=True, check=True)
    text = cp.stdout.decode("utf-8", "replace")
    pages = text.split("\f")
    if pages and not pages[-1].strip():
        pages.pop()
    req(len(pages) == pages_n, f"pdftotext pages={len(pages)} pdfinfo={pages_n}")
    req("\ufffd" not in text, "workbook PDF contains Unicode replacement characters")
    req("目录" not in pages[0] and "Lab Workbook" in pages[0], "workbook page 1 must be dedicated title page")

    ids = [f"{n:02d}{s}" for n in range(1, 41) for s in "AB"]
    missing = [i for i in ids if f"Lab {i}" not in text]
    req(not missing, f"workbook PDF missing Lab IDs: {missing}")

    # Print TOC must distinguish A/B scenarios instead of repeating generic Lab titles.
    toc = "\n".join(pages[1:5])
    for i in ids:
        req(f"Lab {i}" in toc, f"workbook TOC missing Lab {i}")
    for n in range(1, 41):
        req(f"Lab {n:02d}A" in toc and f"Lab {n:02d}B" in toc, f"workbook TOC must distinguish Lab {n:02d}A/B")

    style = (ROOT / PDF["workbook_style"]).read_text(encoding="utf-8")
    req("breaklines=true" in style and "breakanywhere=true" in style, "workbook code blocks must wrap long lines")
    req(PDF.get("workbook_documentclass") == "ctexbook", "workbook documentclass must be ctexbook")

if errors:
    print("WORKBOOK_STRUCTURE_QA_FAILED")
    [print("-", e) for e in errors]
    raise SystemExit(1)
print(f"WORKBOOK_STRUCTURE_QA_OK pages={pages_n} labs=80 toc_ids=80")
