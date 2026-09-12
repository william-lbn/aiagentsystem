from __future__ import annotations
import re
import subprocess
import datetime
import unicodedata
import os
from common import ROOT, course, build_cfg, summary_parts, chapter_paths, appendix_paths, pdf_cfg

META = course()
CFG = build_cfg()
PDF = pdf_cfg()
errors = []
UTC_ENV = {**os.environ, "TZ": "UTC"}


def req(c, m):
    if not c:
        errors.append(m)


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKC", s)
    s = re.sub(r"[\u2010\u2011\u2012\u2013\u2014\u2015\u2212-]", "-", s)
    s = re.sub(r"[：:]", ":", s)
    return re.sub(r"\s+", "", s)


def zh_num(n: int) -> str:
    d = "零一二三四五六七八九"
    if n < 10:
        return d[n]
    if n == 10:
        return "十"
    if n < 20:
        return "十" + d[n % 10]
    if n % 10 == 0:
        return d[n // 10] + "十"
    return d[n // 10] + "十" + d[n % 10]


def first_lines(page: str, n=6) -> list[str]:
    return [x.strip() for x in page.splitlines() if x.strip()][:n]


pdf = ROOT / "book/build" / f"ai-agent-systems-course-{META['version']}.pdf"
req(pdf.exists(), "book PDF missing")
if pdf.exists():
    # Poppler renders PDF dates in the caller's local timezone. Normalize the
    # inspection process before comparing with SOURCE_DATE_EPOCH.
    info = subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True, check=True, env=UTC_ENV).stdout
    m = re.search(r"^Pages:\s+(\d+)", info, re.M)
    pages_n = int(m.group(1)) if m else 0
    req(pages_n >= CFG["pdf_min_pages"], f"PDF pages={pages_n} < {CFG['pdf_min_pages']}")
    req("Page size:       595.28 x 841.89 pts (A4)" in info or "(A4)" in info, "PDF must be A4")
    epoch = int(CFG["source_date_epoch"])
    expected = datetime.datetime.fromtimestamp(epoch, datetime.timezone.utc).strftime("%a %b %d %H:%M:%S %Y UTC")
    req(f"CreationDate:    {expected}" in info, f"CreationDate must derive from SOURCE_DATE_EPOCH ({expected})")

    cp = subprocess.run(["pdftotext", "-layout", str(pdf), "-"], capture_output=True, check=True)
    text = cp.stdout.decode("utf-8", "replace")
    pages = text.split("\f")
    if pages and not pages[-1].strip():
        pages.pop()
    req(len(pages) == pages_n, f"pdftotext pages={len(pages)} pdfinfo={pages_n}")
    req("\ufffd" not in text, "PDF contains Unicode replacement characters")

    # Separate title page and a compact print TOC.
    req(META["title"] in pages[0] and "目录" not in pages[0], "page 1 must be a dedicated title page")
    toc_pages = []
    for i, p in enumerate(pages, 1):
        fl = first_lines(p, 2)
        if fl and "目录" in fl[0]:
            toc_pages.append(i)
    req(1 <= len(toc_pages) <= 5, f"print TOC should occupy 1..5 pages, got {toc_pages}")
    if toc_pages:
        toc_text = "\n".join(pages[i - 1] for i in toc_pages)
        req(
            not re.search(r"\b\d+\.\d+\s+问题背景与学习目标", toc_text),
            "print TOC must not enumerate section-level entries",
        )

    # Every semantic part gets its own page; all 40 chapters start at page top on distinct pages.
    part_pages = []
    for part in summary_parts():
        wanted = norm(part["title"])
        hits = []
        for i, p in enumerate(pages, 1):
            head = norm("".join(first_lines(p, 4)))
            if wanted in head:
                hits.append(i)
        # TOC contains parts too; the standalone part page is the last early-page-top hit before its first chapter.
        req(bool(hits), f"part page missing: {part['title']}")
        if hits:
            part_pages.append(hits[-1])
    req(len(set(part_pages)) == len(summary_parts()), f"part pages must be distinct: {part_pages}")

    chapter_pages = []
    chapter_titles = []
    for idx, pth in enumerate(chapter_paths(), 1):
        title = next(
            (line[2:].strip() for line in pth.read_text(encoding="utf-8").splitlines() if line.startswith("# ")),
            "",
        )
        marker = f"第{zh_num(idx)}章"
        candidates = []
        for i, p in enumerate(pages, 1):
            head = norm("".join(first_lines(p, 5)))
            if norm(marker) in head and norm(title)[:12] in head:
                candidates.append(i)
        req(bool(candidates), f"chapter {idx} start page missing: {title}")
        if candidates:
            page = candidates[-1]  # excludes earlier TOC occurrence
            chapter_pages.append(page)
            chapter_titles.append(title)
    req(len(chapter_pages) == CFG["expected_chapters"], f"chapter start count={len(chapter_pages)}")
    req(len(set(chapter_pages)) == len(chapter_pages), "two chapters share the same physical page")
    req(chapter_pages == sorted(chapter_pages), "chapter pages not strictly ordered")

    # Native appendix lettering, one appendix per chapter page; never numeric chapters 41..44.
    appendix_pages = []
    for i, pth in enumerate(appendix_paths()):
        label = chr(ord("A") + i)
        title = next(
            (line[2:].strip() for line in pth.read_text(encoding="utf-8").splitlines() if line.startswith("# ")),
            "",
        )
        clean = re.sub(r"^附录\s+[A-Z]\s*[：:]\s*", "", title)
        hits = []
        for j, p in enumerate(pages, 1):
            head = norm("".join(first_lines(p, 5)))
            if norm(f"附录 {label}") in head and norm(clean)[:10] in head:
                hits.append(j)
        req(bool(hits), f"appendix {label} start page missing")
        if hits:
            appendix_pages.append(hits[-1])
    req(len(set(appendix_pages)) == CFG["expected_appendices"], f"appendix pages={appendix_pages}")
    req(not re.search(r"第四十[一二三四]章\s+附录", text), "appendices must not be numbered as chapters 41..44")

    # Build-policy guards that directly prevent previously observed layout regressions.
    style = (ROOT / PDF["book_style"]).read_text(encoding="utf-8")
    req("breaklines=true" in style and "breakanywhere=true" in style, "PDF code blocks must wrap long lines")
    req(PDF.get("documentclass") == "ctexbook", "PDF documentclass must be ctexbook")
    req(int(PDF.get("toc_depth", 99)) == 1, "print TOC depth must be 1")
else:
    pages_n = 0
    chapter_pages = []
    part_pages = []
    appendix_pages = []

if errors:
    print("PDF_STRUCTURE_QA_FAILED")
    [print("-", e) for e in errors]
    raise SystemExit(1)
print(
    f"PDF_STRUCTURE_QA_OK pages={pages_n} parts={len(part_pages)} chapters={len(chapter_pages)} appendices={len(appendix_pages)} toc_pages<=5"
)
