from __future__ import annotations
from pathlib import Path
from collections import Counter
import base64
import re
import subprocess
import zipfile
from common import course, build_cfg

ROOT = Path(__file__).resolve().parents[1]
CH = ROOT / "book/zh/chapters"
LAB = ROOT / "labs/core"
EX = ROOT / "examples/chapters"
DIA = ROOT / "book/assets/diagrams"
BUILD = ROOT / "book/build"
BOOK = ROOT / "book/zh/book.md"
META = course()
CFG = build_cfg()
V = META["version"]
errors = []


def req(c, m):
    if not c:
        errors.append(m)


chapters = sorted(CH.glob("*.md"))
labs = sorted(LAB.glob("*.md"))
examples = sorted(EX.glob("ch*.py"))
req(len(chapters) == CFG["expected_chapters"], f"chapters={len(chapters)} expected {CFG['expected_chapters']}")
req(len(labs) == CFG["expected_core_labs"], f"labs={len(labs)} expected {CFG['expected_core_labs']}")
req(
    len(examples) == CFG["expected_chapter_examples"],
    f"examples={len(examples)} expected {CFG['expected_chapter_examples']}",
)
sections = [
    "问题背景与学习目标",
    "核心概念与系统直觉",
    "原理与理论基础",
    "关键机制与执行流程",
    "从原理到实现",
    "主流系统实现对照与源码阅读入口",
    "设计方案与方法对比",
    "可复现实验",
    "工程场景与系统设计",
    "故障模型、失败模式与排错",
    "性能、可靠性与工程化",
    "技术边界与设计取舍",
    "前沿研究与演进方向",
    "本章总结与进阶实践",
]
long = []
for ch in chapters:
    text = ch.read_text(encoding="utf-8")
    for sec in sections:
        req(f"## {sec}" in text, f"{ch.name}: missing {sec}")
    req(not re.search(r"^#{2,6}\s+\d+(?:\.\d+)*\.?\s+", text, re.M), f"{ch.name}: manual numeric heading prefix found")
    stem = ch.stem
    for kind in ("architecture", "flow"):
        for ext in ("dot", "svg", "png"):
            req((DIA / f"{stem}-{kind}.{ext}").exists(), f"missing {stem}-{kind}.{ext}")
        req((DIA / "pdf" / f"{stem}-{kind}.pdf").exists(), f"missing PDF {stem}-{kind}")
    req(text.count("```python") >= 2, f"{ch.name}: expected implementation code")
    req("实际输出" in text and "验收" in text and "关键断点" in text, f"{ch.name}: experiment details incomplete")
    for p in re.split(r"\n\s*\n", text):
        t = " ".join(p.strip().split())
        if len(t) >= 180 and not t.startswith(("-", "|", "```", "![")):
            long.append(t)
for lab in labs:
    s = lab.read_text(encoding="utf-8")
    for marker in ["实验目标", "环境与版本", "环境准备", "实验代码", "调试断点", "验收标准"]:
        req(marker in s, f"{lab.name}: missing {marker}")
# exact long-prose duplication should be low; standardized env/lists excluded
c = Counter(long)
bad = [(n, t) for t, n in c.items() if n >= 3]
req(not bad, f"repeated long prose >=3 occurrences: {len(bad)}; sample={bad[:2]}")
book = BOOK.read_text(encoding="utf-8") if BOOK.exists() else ""
for badword in [
    "如何写这本书",
    "如何组织本书仓库",
    "AI 如何生成本章",
    "TBD_PLACEHOLDER",
    "TODO_PLACEHOLDER",
    "file not found in package",
    "Could not load image",
]:
    req(badword not in book, f"forbidden/broken marker {badword}")
# local images
for rel in re.findall(r"!\[[^\]]*\]\(([^)]+)\)", book):
    if rel.startswith(("http://", "https://", "data:")):
        continue
    req((ROOT / "book" / rel).exists(), f"broken image {rel}")
# artifacts
pdf = BUILD / f"ai-agent-systems-course-{V}.pdf"
html = BUILD / f"ai-agent-systems-course-{V}.html"
epub = BUILD / f"ai-agent-systems-course-{V}.epub"
for p in (pdf, html, epub):
    req(p.exists() and p.stat().st_size > 10000, f"missing artifact {p.name}")
pages = 0
if pdf.exists():
    info = subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True, check=True).stdout
    m = re.search(r"^Pages:\s+(\d+)", info, re.M)
    pages = int(m.group(1)) if m else 0
    req(pages >= CFG["pdf_min_pages"], f"PDF pages {pages}<{CFG['pdf_min_pages']}")
    txt = BUILD / "_qa.txt"
    subprocess.run(["pdftotext", "-layout", str(pdf), str(txt)], check=True)
    pt = txt.read_text(encoding="utf-8", errors="ignore")
    txt.unlink(missing_ok=True)
    for marker in ["file not found in package", "Could not load image"]:
        req(marker not in pt, f"PDF has {marker}")
    # Prevent a source/manual section number from being printed after Pandoc's automatic number.
    req(
        not re.search(r"\b\d+\.\d+(?:\.\d+)?\s+\d+(?:\.\d+)+\s+", pt),
        "PDF appears to contain duplicated section numbering",
    )
if html.exists():
    h = html.read_text(encoding="utf-8", errors="ignore")
    inline_svg = h.count("<svg")
    embedded_svg = re.findall(r"data:image/svg\+xml;base64,([A-Za-z0-9+/=]+)", h)
    invalid_embedded = []
    for i, payload in enumerate(embedded_svg):
        try:
            decoded = base64.b64decode(payload, validate=True).decode("utf-8")
        except (ValueError, UnicodeDecodeError) as exc:
            invalid_embedded.append(f"{i}:{type(exc).__name__}")
            continue
        if "<svg" not in decoded or "</svg>" not in decoded:
            invalid_embedded.append(f"{i}:not-complete-svg")
    req(not invalid_embedded, f"HTML invalid embedded SVG payloads: {invalid_embedded[:5]}")
    svg_count = inline_svg + len(embedded_svg)
    req(
        svg_count >= CFG["expected_diagrams"],
        f"HTML svg count {svg_count} <{CFG['expected_diagrams']} (inline={inline_svg}, embedded={len(embedded_svg)})",
    )
if epub.exists():
    with zipfile.ZipFile(epub) as z:
        imgs = [x for x in z.namelist() if x.lower().endswith((".svg", ".png", ".jpg", ".jpeg"))]
        req(len(imgs) >= CFG["expected_diagrams"], f"EPUB image count {len(imgs)}<{CFG['expected_diagrams']}")
if errors:
    print("BOOK_QA_FAILED")
    [print("-", x) for x in errors]
    raise SystemExit(1)
print(
    f"BOOK_QA_OK chapters={len(chapters)} labs={len(labs)} examples={len(examples)} pdf_pages={pages} long_repeat_max={max(c.values() or [0])}"
)
