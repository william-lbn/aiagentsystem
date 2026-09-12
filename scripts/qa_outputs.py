from __future__ import annotations
import re
import subprocess
from html.parser import HTMLParser
from common import ROOT, course, build_cfg

meta = course()
cfg = build_cfg()
errors = []


def req(c, m):
    if not c:
        errors.append(m)


site = ROOT / "site"
req((site / "index.html").exists(), "site index missing")
htmls = list(site.rglob("*.html"))
req(len(htmls) == cfg["expected_site_pages"], f"site pages={len(htmls)} expected={cfg['expected_site_pages']}")
req(len(list((site / "chapters").glob("*.html"))) == cfg["expected_chapters"], "site chapter count")
req(len(list((site / "appendices").glob("*.html"))) == cfg["expected_appendices"], "site appendix count")
req(len(list((site / "labs").glob("*.html"))) == cfg["expected_core_labs"], "site lab count")


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.refs = []

    def handle_starttag(self, tag, attrs):
        for k, v in attrs:
            if k in ("href", "src") and v:
                self.refs.append(v)


for hp in htmls:
    parser = Links()
    parser.feed(hp.read_text(encoding="utf-8", errors="ignore"))
    for ref in parser.refs:
        if ref.startswith(("http://", "https://", "mailto:", "#", "data:", "javascript:")):
            continue
        clean = ref.split("#", 1)[0].split("?", 1)[0]
        if not clean:
            continue
        target = (hp.parent / clean).resolve()
        req(target.exists(), f"broken site ref {hp.relative_to(site)} -> {ref}")
wb = ROOT / "workbook/build"
for ext in ("pdf", "html", "epub"):
    p = wb / f"agent-systems-lab-workbook-{meta['version']}.{ext}"
    req(p.exists() and p.stat().st_size > 10000, f"workbook {ext} missing/small")
wbpdf = wb / f"agent-systems-lab-workbook-{meta['version']}.pdf"
wbp = 0
if wbpdf.exists():
    o = subprocess.run(["pdfinfo", str(wbpdf)], text=True, capture_output=True, check=True).stdout
    m = re.search(r"^Pages:\s+(\d+)", o, re.M)
    wbp = int(m.group(1)) if m else 0
    req(wbp >= 80, f"workbook pages={wbp}")
book = ROOT / "book/build" / f"ai-agent-systems-course-{meta['version']}.pdf"
pages = 0
if book.exists():
    out = subprocess.run(["pdfinfo", str(book)], text=True, capture_output=True, check=True).stdout
    m = re.search(r"^Pages:\s+(\d+)", out, re.M)
    pages = int(m.group(1)) if m else 0
    req(pages >= cfg["pdf_min_pages"], f"book pages={pages}")
else:
    req(False, "book pdf missing")
if errors:
    print("OUTPUT_QA_FAILED")
    [print("-", x) for x in errors]
    raise SystemExit(1)
print(f"OUTPUT_QA_OK site_pages={len(htmls)} book_pages={pages} workbook_pages={wbp}")
