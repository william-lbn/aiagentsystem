from __future__ import annotations
from pathlib import Path
import hashlib
import re
import json
import subprocess
import tempfile
import tomllib
from xml.etree import ElementTree as ET
from common import ROOT, chapter_paths, appendix_paths, lab_paths, build_cfg, course, summary_parts
from build_diagrams import render_dot

cfg = build_cfg()
meta = course()
errors = []


def req(cond, msg):
    if not cond:
        errors.append(msg)


def prose_without_code(text: str) -> str:
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    text = re.sub(r"`[^`\n]*`", "", text)
    return text


def headings(text: str):
    return [(len(m.group(1)), m.group(2).strip()) for m in re.finditer(r"^(#{1,6})\s+(.+?)\s*$", text, re.M)]


chapters = chapter_paths()
apps = appendix_paths()
labs = lab_paths()
req(len(chapters) == cfg["expected_chapters"], f"chapter count {len(chapters)}")
req(len(apps) == cfg["expected_appendices"], f"appendices={len(apps)}")
req(len(labs) == cfg["expected_core_labs"], f"core labs={len(labs)}")

# Canonical book structure: one H1 per chapter, no hierarchy jumps, no manual numbers.
summary_titles = [ch["title"] for part in summary_parts() for ch in part["chapters"]]
for i, p in enumerate(chapters):
    text = p.read_text(encoding="utf-8")
    scan = prose_without_code(text)
    hs = headings(scan)
    req(sum(1 for lvl, _ in hs if lvl == 1) == 1, f"{p}: expected exactly one H1")
    if hs:
        req(hs[0][0] == 1, f"{p}: first heading must be H1")
        req(hs[0][1] == summary_titles[i], f"{p}: H1 differs from SUMMARY title")
        prev = hs[0][0]
        for lvl, title in hs[1:]:
            req(lvl <= prev + 1, f"{p}: heading level jump before {title!r}")
            prev = lvl
    req(not re.search(r"^#{2,6}\s+\d+(?:\.\d+)*\.?\s+", scan, re.M), f"{p}: manual heading number")
    req(" 的证据链" not in scan, f"{p}: duplicated evidence-chain wording")
    for rel in re.findall(r"!?\[[^\]]*\]\(([^)]+)\)", scan):
        rel = rel.strip().split()[0]
        if rel.startswith(("http://", "https://", "mailto:", "data:", "#")):
            continue
        target = (p.parent / rel.split("#", 1)[0]).resolve()
        req(target.exists(), f"{p}: broken local link {rel} -> {target}")

# Appendix labels remain explicit in canonical Markdown for website/EPUB readability.
for i, p in enumerate(apps):
    text = p.read_text(encoding="utf-8")
    hs = headings(prose_without_code(text))
    label = chr(ord("A") + i)
    req(
        bool(hs) and hs[0][0] == 1 and hs[0][1].startswith(f"附录 {label}："),
        f"{p}: appendix H1 must start 附录 {label}：",
    )

# Each A/B lab must have a unique visible title matching its filename ID and scenario.
lab_titles = []
for p in labs:
    m = re.match(r"lab-(\d{2})([AB])-", p.name)
    req(bool(m), f"{p}: invalid lab filename")
    text = p.read_text(encoding="utf-8")
    hs = headings(prose_without_code(text))
    title = hs[0][1] if hs else ""
    if m:
        labid = m.group(1) + m.group(2)
        mode = "正常路径" if m.group(2) == "A" else "故障注入"
        req(title.startswith(f"Lab {labid} — "), f"{p}: H1 must expose Lab {labid}")
        req(title.endswith(f"｜{mode}"), f"{p}: H1 must end with ｜{mode}")
    lab_titles.append(title)
req(len(set(lab_titles)) == len(lab_titles), "lab H1 titles must be unique")

# Canonical diagram source is DOT; SVG is committed review evidence.
dots = sorted((ROOT / "book/assets/diagrams").glob("*.dot"))
svgs = sorted((ROOT / "book/assets/diagrams").glob("*.svg"))
req(len(dots) == cfg["expected_diagrams"], f"dot diagrams={len(dots)}")
req(len(svgs) == cfg["expected_diagrams"], f"svg diagrams={len(svgs)}")

GEOMETRY_ATTRS = {
    "width",
    "height",
    "viewBox",
    "transform",
    "d",
    "points",
    "x",
    "y",
    "x1",
    "y1",
    "x2",
    "y2",
    "cx",
    "cy",
    "rx",
    "ry",
}


def svg_semantics(path: Path):
    root = ET.parse(path).getroot()

    def visit(node):
        attrs = tuple(
            sorted((key, value) for key, value in node.attrib.items() if key.rsplit("}", 1)[-1] not in GEOMETRY_ATTRS)
        )
        return (node.tag.rsplit("}", 1)[-1], attrs, (node.text or "").strip(), tuple(visit(child) for child in node))

    return visit(root)


for dot in dots:
    svg = dot.with_suffix(".svg")
    expected_hash = hashlib.sha256(dot.read_bytes()).hexdigest()
    committed = svg.read_text(encoding="utf-8", errors="replace") if svg.exists() else ""
    req(
        f"<!-- DOT-SHA256: {expected_hash} -->" in committed,
        f"{svg.name}: DOT source hash missing/stale; run make diagrams",
    )
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td) / svg.name
        try:
            render_dot(dot, "svg", tmp)
            expected = svg_semantics(tmp)
            actual = svg_semantics(svg)
        except (subprocess.CalledProcessError, ET.ParseError, OSError) as e:
            req(False, f"{dot.name}: SVG semantic verification failed: {e}")
        else:
            req(expected == actual, f"{svg.name}: semantic preview mismatch; run make diagrams")

# Generated outputs must not become canonical source.
gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
for pattern in ["book/zh/book.md", "book/build/", "slides/*.pptx", "workbook/build/", "site/", "dist/", ".build/"]:
    req(pattern in gitignore, f".gitignore missing {pattern}")

# No release literal in build/QA implementation. course.toml is the single source.
release_literal = str(meta["version"]).lower()
for sp in (ROOT / "scripts").rglob("*"):
    if not sp.is_file() or sp.suffix not in {".py", ".lua"} or sp.name == "qa_source.py":
        continue
    txt = sp.read_text(encoding="utf-8", errors="ignore").lower()
    req(release_literal not in txt, f"{sp.relative_to(ROOT)}: hardcoded release version {meta['version']}")

req((ROOT / "uv.lock").exists(), "uv.lock missing")
try:
    tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
except Exception as e:
    req(False, f"pyproject.toml invalid: {e}")
locks = json.loads((ROOT / "integrations/SOURCE_LOCK.json").read_text(encoding="utf-8"))
req(len(locks) >= cfg["expected_source_locks"], f"source locks={len(locks)}")
if errors:
    print("SOURCE_QA_FAILED")
    [print("-", x) for x in errors]
    raise SystemExit(1)
print(
    f"SOURCE_QA_OK version={meta['version']} chapters={len(chapters)} appendices={len(apps)} labs={len(labs)} diagrams={len(dots)} source_locks={len(locks)}"
)
