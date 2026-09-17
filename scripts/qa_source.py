from __future__ import annotations
from pathlib import Path
import ast
import hashlib
import re
import json
import tomllib
from xml.etree import ElementTree as ET
from common import ROOT, chapter_paths, appendix_paths, lab_paths, build_cfg, course, summary_parts

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
        # Chapters may deliberately name the rendered HTML peer so the same
        # link works in Quarto's multi-page site and Pandoc's compatibility
        # site.  In the source tree that peer is Markdown; require it to exist
        # rather than weakening local-link validation for arbitrary HTML.
        source_peer = target.with_suffix(".md") if target.suffix == ".html" else target
        req(source_peer.exists(), f"{p}: broken local link {rel} -> {target}")

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

NODE_RE = re.compile(r'^\s*([A-Za-z_][\w]*)\s*\[(.*?)\]\s*;\s*$', re.M)
EDGE_RE = re.compile(r'^\s*([A-Za-z_][\w]*)\s*->\s*([A-Za-z_][\w]*)\s*(?:\[(.*?)\])?\s*;\s*$', re.M)
LABEL_RE = re.compile(r'(?:^|,)\s*label="((?:\\.|[^"\\])*)"')


def normalize_diagram_text(value: str) -> str:
    # Graphviz may serialize ordinary spacing as NBSP entities and may split a
    # label into multiple text nodes; neither changes the visible semantics.
    return re.sub(r"\s+", " ", value.replace("\u00a0", " ")).strip()


def dot_semantics(path: Path):
    source = path.read_text(encoding="utf-8")
    nodes = {}
    for node_id, attrs in NODE_RE.findall(source):
        label = LABEL_RE.search(attrs)
        if label:
            nodes[node_id] = normalize_diagram_text(label.group(1).replace(r'\"', '"').replace(r"\n", "\n"))
    edges = []
    for src, dst, attrs in EDGE_RE.findall(source):
        label = LABEL_RE.search(attrs)
        edge_label = normalize_diagram_text(label.group(1).replace(r'\"', '"').replace(r"\n", "\n")) if label else ""
        edges.append((f"{src}->{dst}", edge_label))
    return nodes, sorted(edges)


def svg_semantics(path: Path):
    root = ET.parse(path).getroot()
    nodes = {}
    edges = []
    forbidden = []
    for element in root.iter():
        tag = element.tag.rsplit("}", 1)[-1]
        if tag in {"script", "foreignObject"}:
            forbidden.append(tag)
        for raw_key, value in element.attrib.items():
            key = raw_key.rsplit("}", 1)[-1].lower()
            if key.startswith("on") or (key == "href" and value.strip().lower().startswith(("http:", "https:", "//"))):
                forbidden.append(f"{tag}@{key}")
        if tag != "g":
            continue
        kind = element.attrib.get("class")
        titles = ["".join(child.itertext()).strip() for child in element if child.tag.rsplit("}", 1)[-1] == "title"]
        if len(titles) != 1 or kind not in {"node", "edge"}:
            continue
        visible = ["".join(child.itertext()).strip() for child in element.iter() if child.tag.rsplit("}", 1)[-1] == "text"]
        label = normalize_diagram_text("\n".join(part for part in visible if part))
        if kind == "node":
            nodes[titles[0]] = label
        else:
            edges.append((titles[0].replace("→", "->"), label))
    if forbidden:
        raise ValueError(f"unsafe SVG elements/attributes: {sorted(forbidden)}")
    return nodes, sorted(edges)


for dot in dots:
    svg = dot.with_suffix(".svg")
    expected_hash = hashlib.sha256(dot.read_bytes()).hexdigest()
    committed = svg.read_text(encoding="utf-8", errors="replace") if svg.exists() else ""
    req(
        f"<!-- DOT-SHA256: {expected_hash} -->" in committed,
        f"{svg.name}: DOT source hash missing/stale; run make diagrams",
    )
    try:
        expected = dot_semantics(dot)
        actual = svg_semantics(svg)
    except (ET.ParseError, OSError, ValueError) as e:
        req(False, f"{dot.name}: SVG semantic verification failed: {e}")
    else:
        req(expected == actual, f"{svg.name}: node/edge/label preview mismatch; run make diagrams")

# Generated outputs must not become canonical source.
gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
for pattern in ["book/zh/book.md", "book/build/", "slides/*.pptx", "workbook/build/", "site/", "dist/", ".build/"]:
    req(pattern in gitignore, f".gitignore missing {pattern}")

# A Python environment guarantees its current interpreter, not an unversioned
# ``python`` alias on PATH. Examples that spawn child Python processes must
# preserve the exact validated interpreter through sys.executable.
process_calls = {"run", "Popen", "check_call", "check_output", "check_returncode"}
for sp in (ROOT / "examples").rglob("*.py"):
    try:
        tree = ast.parse(sp.read_text(encoding="utf-8"), filename=str(sp))
    except SyntaxError as e:
        req(False, f"{sp.relative_to(ROOT)}: invalid Python syntax: {e}")
        continue
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute) or node.func.attr not in process_calls:
            continue
        if not node.args or not isinstance(node.args[0], (ast.List, ast.Tuple)) or not node.args[0].elts:
            continue
        executable = node.args[0].elts[0]
        if isinstance(executable, ast.Constant) and executable.value == "python":
            req(False, f"{sp.relative_to(ROOT)}:{node.lineno}: subprocess must use sys.executable, not bare python")

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
