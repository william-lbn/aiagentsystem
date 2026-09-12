from __future__ import annotations
import argparse
import hashlib
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path
from common import ROOT, course, build_cfg, fonts_cfg, pdf_cfg, chapter_paths, appendix_paths, lab_paths
from prepare_quarto import prepare

META = course()
CFG = build_cfg()
FONTS = fonts_cfg()
PDF = pdf_cfg()
VERSION = META["version"]


def resolved_font_files() -> dict[str, Path]:
    """Resolve the locked font families to concrete files via fontconfig.

    Some macOS TeX Live installations ship an OSFONTDIR placeholder instead of
    consulting Homebrew fontconfig automatically.  Deriving the search path
    from the exact configured families avoids host-specific ctex presets and
    keeps Linux/container builds on the same family contract.
    """
    if not shutil.which("fc-match"):
        return {}
    files = {}
    for role, family in FONTS.items():
        if not family:
            continue
        match = subprocess.run(
            ["fc-match", "--format=%{file}\n", family],
            capture_output=True,
            text=True,
            check=False,
        )
        path = Path(match.stdout.splitlines()[0].strip()).expanduser() if match.stdout.strip() else None
        if path and path.is_file():
            files[role] = path
    return files


ENV = {
    **os.environ,
    "SOURCE_DATE_EPOCH": str(CFG["source_date_epoch"]),
    "FORCE_SOURCE_DATE": "1",
    "TZ": "UTC",
    "LC_ALL": os.environ.get("LC_ALL", "C.UTF-8"),
    "COURSE_BOOK_ROOT": str(ROOT / "book"),
}
FONT_FILES = resolved_font_files()
if FONT_FILES:
    ENV["OSFONTDIR"] = os.pathsep.join(dict.fromkeys(str(p.parent) for p in FONT_FILES.values()))


def xetex_font_ref(role: str, fallback: str) -> str:
    family = FONTS.get(role, fallback)
    # TeX Live on macOS can locate an OTF through OSFONTDIR while still failing
    # to resolve the same fontconfig family name. Linux/container XeTeX does
    # resolve the locked family and should retain that portable reference.
    if platform.system() == "Darwin" and role in FONT_FILES:
        return FONT_FILES[role].name
    return family


def run(cmd: list[str], cwd: Path | None = None):
    print("+", " ".join(str(x) for x in cmd), flush=True)
    subprocess.run(cmd, cwd=cwd or ROOT, env=ENV, check=True)


def require(cmd: str):
    if not shutil.which(cmd):
        raise SystemExit(f"MISSING_TOOL {cmd}")


def clean_dir(p: Path):
    if p.exists():
        shutil.rmtree(p)
    p.mkdir(parents=True)


def pandoc_common(toc_depth: int) -> list[str]:
    return [
        "--standalone",
        "--toc",
        f"--toc-depth={toc_depth}",
        "--number-sections",
        "--metadata",
        f"lang={META['lang']}",
    ]


def stable_identifier(kind: str) -> str:
    # Pandoc otherwise generates a random EPUB UUID on every build.  UUIDv5
    # keeps the identifier stable while namespacing it by course/version/artifact.
    name = f"{META['slug']}:{VERSION}:{kind}"
    return "urn:uuid:" + str(uuid.uuid5(uuid.NAMESPACE_URL, name))


def pdf_repro_header(src: Path, kind: str) -> Path:
    # xdvipdfmx supports pdf:trailerid.  Derive the 16-byte ID from source
    # content + version + artifact kind so two clean checkouts produce the same
    # trailer while a content change naturally changes the identifier.
    h = hashlib.sha256()
    h.update(src.read_bytes())
    h.update(VERSION.encode())
    h.update(kind.encode())
    ident = h.hexdigest()[:32]
    p = ROOT / ".build" / "latex" / f"{kind}-reproducible.tex"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\\AtBeginDocument{\\special{pdf:trailerid [ <" + ident + "> <" + ident + "> ]}}\n", encoding="utf-8")
    return p


def pdf_args(*, style: Path, documentclass: str, structure_filter: bool = False) -> list[str]:
    args = [
        "--pdf-engine=xelatex",
        "--top-level-division=chapter",
        "-M",
        "lang=false",
        "--lua-filter",
        str(ROOT / "scripts/filters/pdf_diagrams.lua"),
    ]
    if structure_filter:
        args += ["--lua-filter", str(ROOT / "scripts/filters/book_structure.lua")]
    args += ["-V", f"documentclass={documentclass}"]
    for opt in PDF.get("class_options", ["oneside", "openany"]):
        args += ["-V", f"classoption={opt}"]
    args += [
        "-V",
        f"mainfont={xetex_font_ref('main', 'Noto Serif CJK SC')}",
        "-V",
        f"sansfont={xetex_font_ref('sans', 'Noto Sans CJK SC')}",
        "-V",
        f"monofont={xetex_font_ref('mono', 'Noto Sans Mono CJK SC')}",
        "-V",
        f"papersize={PDF.get('paper_size', 'a4')}",
        "-V",
        f"geometry:margin={PDF.get('margin', '2.4cm')}",
        "--include-in-header",
        str(style),
    ]
    return args


def render_pdf(src: Path, out_pdf: Path, common: list[str], pdfopts: list[str], *, name: str):
    """Render PDF as an explicit Pandoc AST -> LaTeX -> XeLaTeX pipeline.

    Keeping XeLaTeX outside Pandoc's temporary tex2pdf wrapper makes resource
    resolution, reruns and failure logs deterministic and independently auditable.
    """
    build = ROOT / ".build" / "latex"
    build.mkdir(parents=True, exist_ok=True)
    tex = build / f"{name}.tex"
    aux = build / f"{name}-aux"
    clean_dir(aux)
    # pdfopts contains --pdf-engine for Pandoc's one-shot mode; it is not valid
    # when the target is raw LaTeX.  Keep the same filters/variables otherwise.
    opts = [x for x in pdfopts if x != "--pdf-engine=xelatex"]
    repro = pdf_repro_header(src, name)
    opts += ["--include-in-header", str(repro)]
    run(["pandoc", str(src), *common, *opts, "-o", str(tex)])
    require("xelatex")
    job = out_pdf.stem
    for pass_no in (1, 2):
        run(
            [
                "xelatex",
                "-interaction=nonstopmode",
                "-halt-on-error",
                f"-jobname={job}",
                f"-output-directory={aux}",
                str(tex),
            ]
        )
    built = aux / f"{job}.pdf"
    if not built.exists():
        raise SystemExit(f"PDF_NOT_CREATED {built}")
    out_pdf.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(built, out_pdf)


def compat_book():
    require("pandoc")
    require("xelatex")
    run([sys.executable, str(ROOT / "scripts/build_diagrams.py")])
    run([sys.executable, str(ROOT / "scripts/assemble_book.py")])
    out = ROOT / "book/build"
    clean_dir(out)
    src = ROOT / "book/zh/book.md"
    rp = str(ROOT / "book") + os.pathsep + str(ROOT / "book/zh") + os.pathsep + str(ROOT)
    html_common = ["pandoc", str(src), *pandoc_common(int(PDF.get("html_toc_depth", 3))), "--resource-path", rp]
    run(
        [
            *html_common,
            "--embed-resources",
            "--css",
            str(ROOT / "book/assets/book.css"),
            "-o",
            str(out / f"ai-agent-systems-course-{VERSION}.html"),
        ]
    )
    run(
        [
            *html_common,
            "--metadata",
            f"identifier={stable_identifier('book')}",
            "-o",
            str(out / f"ai-agent-systems-course-{VERSION}.epub"),
        ]
    )
    pdf_common = [*pandoc_common(int(PDF.get("toc_depth", 1))), "--resource-path", rp]
    render_pdf(
        src,
        out / f"ai-agent-systems-course-{VERSION}.pdf",
        pdf_common,
        pdf_args(
            style=ROOT / PDF["book_style"], documentclass=PDF.get("documentclass", "ctexbook"), structure_filter=True
        ),
        name="book",
    )
    print("BOOK_BUILT compatibility=pandoc", out)


def rewrite_site_links(text: str, src: Path) -> str:
    # Link-only normalization; Markdown interpretation stays entirely in Pandoc.
    text = re.sub(r"\]\(\.\./\.\./\.\./labs/core/(lab-[^)]+)\.md\)", r"](../labs/\1.html)", text)
    text = re.sub(r"\]\(\.\./(appendix-[^)]+)\.md\)", r"](../appendices/\1.html)", text)
    text = text.replace("](../../../evidence/", "](../evidence/")
    text = text.replace("](../../../experiments/", "](../experiments/")
    text = text.replace("](../../../.github/workflows/", "](../workflows/")
    return text


def export_site_support(out: Path):
    """Publish only the public, secret-scrubbed evidence referenced by chapters."""
    shutil.copytree(ROOT / "evidence/l5", out / "evidence/l5", dirs_exist_ok=True)
    shutil.copytree(ROOT / "evidence/benchmarks", out / "evidence/benchmarks", dirs_exist_ok=True)
    (out / "experiments/benchmarks").mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "experiments/benchmarks/catalog.json", out / "experiments/benchmarks/catalog.json")
    (out / "workflows").mkdir(parents=True, exist_ok=True)
    shutil.copy2(
        ROOT / ".github/workflows/external-agent-benchmarks.yml", out / "workflows/external-agent-benchmarks.yml"
    )

    # Quarto renders from a prepared tree and therefore does not pass through
    # rewrite_site_links(). Normalize the same repository-relative targets in
    # its final chapter HTML before output QA checks the self-contained site.
    replacements = {
        "../../../evidence/": "../evidence/",
        "../../../experiments/": "../experiments/",
        "../../../.github/workflows/": "../workflows/",
    }
    for html in (out / "chapters").glob("*.html"):
        source = html.read_text(encoding="utf-8")
        rendered = source
        for old, new in replacements.items():
            rendered = rendered.replace(old, new)
        if rendered != source:
            html.write_text(rendered, encoding="utf-8")


def render_html(text: str, out: Path, title: str, resource_paths: list[Path]):
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", suffix=".md", encoding="utf-8", delete=False, dir=ROOT / ".build") as f:
        f.write(text)
        tmp = Path(f.name)
    try:
        rp = os.pathsep.join(str(x) for x in resource_paths)
        run(
            [
                "pandoc",
                str(tmp),
                "--standalone",
                "--embed-resources",
                "--toc",
                f"--toc-depth={int(PDF.get('html_toc_depth', 3))}",
                "--metadata",
                f"title={title}",
                "--metadata",
                f"lang={META['lang']}",
                "--resource-path",
                rp,
                "-o",
                str(out),
            ]
        )
    finally:
        tmp.unlink(missing_ok=True)


def compat_site():
    require("pandoc")
    run([sys.executable, str(ROOT / "scripts/build_diagrams.py")])
    out = ROOT / "site"
    clean_dir(out)
    (ROOT / ".build").mkdir(exist_ok=True)
    for p in chapter_paths():
        txt = rewrite_site_links(p.read_text(encoding="utf-8"), p)
        render_html(txt, out / "chapters" / f"{p.stem}.html", p.stem, [p.parent, ROOT / "book", ROOT])
    for p in appendix_paths():
        render_html(
            p.read_text(encoding="utf-8"),
            out / "appendices" / f"{p.stem}.html",
            p.stem,
            [p.parent, ROOT / "book", ROOT],
        )
    for p in lab_paths():
        render_html(p.read_text(encoding="utf-8"), out / "labs" / f"{p.stem}.html", p.stem, [p.parent, ROOT])
    idx = [f"# {META['title']}", f"\n{META['subtitle']}\n", f"\n版本：`{VERSION}`\n"]
    for part in __import__("common").summary_parts():
        idx.append(f"\n## {part['title']}\n")
        for ch in part["chapters"]:
            idx.append(f"- [{ch['title']}](chapters/{Path(ch['path']).stem}.html)")
    idx.append("\n## 附录\n")
    idx += [f"- [{p.stem}](appendices/{p.stem}.html)" for p in appendix_paths()]
    idx.append("\n## 核心实验\n")
    idx += [f"- [{p.stem}](labs/{p.stem}.html)" for p in lab_paths()]
    render_html("\n".join(idx), out / "index.html", META["title"], [ROOT])
    export_site_support(out)
    print("SITE_BUILT compatibility=pandoc pages=", len(list(out.rglob("*.html"))))


def workbook_source() -> Path:
    b = ROOT / ".build"
    b.mkdir(exist_ok=True)
    p = b / "workbook.md"
    chunks = [
        f'---\ntitle: "{META["title"]} · Lab Workbook"\nsubtitle: "80 个可复现实验：正常路径与故障注入"\nauthor: "{META["author"]}"\ndate: "{META["version"]} · {META["release_date"]}"\nlang: {META["lang"]}\n---\n'
    ]
    for lab in lab_paths():
        chunks.append(lab.read_text(encoding="utf-8"))
        chunks.append("\n\n")
    p.write_text("\n".join(chunks), encoding="utf-8")
    return p


def compat_workbook():
    require("pandoc")
    require("xelatex")
    src = workbook_source()
    out = ROOT / "workbook/build"
    clean_dir(out)
    rp = os.pathsep.join([str(ROOT), str(ROOT / "labs/core")])
    name = f"agent-systems-lab-workbook-{VERSION}"
    html_base = ["pandoc", str(src), *pandoc_common(1), "--resource-path", rp]
    run([*html_base, "--embed-resources", "-o", str(out / f"{name}.html")])
    run([*html_base, "--metadata", f"identifier={stable_identifier('workbook')}", "-o", str(out / f"{name}.epub")])
    pdf_base = [*pandoc_common(1), "--resource-path", rp]
    render_pdf(
        src,
        out / f"{name}.pdf",
        pdf_base,
        pdf_args(style=ROOT / PDF["workbook_style"], documentclass=PDF.get("workbook_documentclass", "ctexbook")),
        name="workbook",
    )
    print("WORKBOOK_BUILT compatibility=pandoc", out)


def canonical(target: str):
    require("quarto")
    cp = subprocess.run(["quarto", "--version"], capture_output=True, text=True, check=True).stdout.strip()
    if cp != str(CFG["quarto_version"]):
        raise SystemExit(f"QUARTO_VERSION_MISMATCH actual={cp} expected={CFG['quarto_version']}")
    project = prepare(target)
    run(["quarto", "render"], cwd=project)
    qout = project / "_output"
    if target == "site":
        out = ROOT / "site"
        clean_dir(out)
        shutil.copytree(qout, out, dirs_exist_ok=True)
        export_site_support(out)
    elif target == "book":
        out = ROOT / "book/build"
        clean_dir(out)
        for p in qout.iterdir():
            if p.suffix.lower() in {".pdf", ".epub", ".html"}:
                shutil.copy2(p, out / f"ai-agent-systems-course-{VERSION}{p.suffix.lower()}")
    else:
        out = ROOT / "workbook/build"
        clean_dir(out)
        for p in qout.iterdir():
            if p.suffix.lower() in {".pdf", ".epub", ".html"}:
                shutil.copy2(p, out / f"agent-systems-lab-workbook-{VERSION}{p.suffix.lower()}")
    print("CANONICAL_QUARTO_BUILT", target)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("target", choices=["book", "site", "workbook", "all"])
    ap.add_argument("--engine", choices=["auto", "quarto", "pandoc"], default="auto")
    a = ap.parse_args()
    targets = ["book", "site", "workbook"] if a.target == "all" else [a.target]
    engine = a.engine
    if engine == "auto":
        engine = "quarto" if shutil.which("quarto") else "pandoc"
    if engine == "quarto":
        for t in targets:
            canonical(t)
    else:
        funcs = {"book": compat_book, "site": compat_site, "workbook": compat_workbook}
        for t in targets:
            funcs[t]()


if __name__ == "__main__":
    main()
