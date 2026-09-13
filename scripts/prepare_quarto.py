from __future__ import annotations
import argparse
import datetime
import hashlib
import shutil
from pathlib import Path
from common import ROOT, course, build_cfg, fonts_cfg, pdf_cfg, summary_parts, chapter_paths, appendix_paths, lab_paths

META = course()
CFG = build_cfg()
FONTS = fonts_cfg()
PDF = pdf_cfg()
BASE = ROOT / ".build/quarto"


def q(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def reset(path: Path):
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)


def copy_sources(dst: Path):
    # Mirror paths used by canonical Markdown links.
    shutil.copytree(ROOT / "book/zh", dst / "book/zh", dirs_exist_ok=True)
    shutil.copytree(ROOT / "book/assets", dst / "book/assets", dirs_exist_ok=True)
    shutil.copytree(ROOT / "labs/core", dst / "labs/core", dirs_exist_ok=True)
    (dst / "scripts/filters").mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "scripts/filters/pdf_diagrams.lua", dst / "scripts/filters/pdf_diagrams.lua")
    shutil.copy2(ROOT / "scripts/filters/book_structure.lua", dst / "scripts/filters/book_structure.lua")


def annotate_appendix_titles(dst: Path):
    for src in appendix_paths():
        p = dst / "book/zh" / src.name
        text = p.read_text(encoding="utf-8")
        lines = text.splitlines()
        for i, line in enumerate(lines):
            if line.startswith("# "):
                title = line[2:].strip()
                lines[i] = f"# {title} {{.appendix-title}}"
                break
        p.write_text("\n".join(lines) + "\n", encoding="utf-8")


def preface_text() -> str:
    return """# 导言：把 Agent 当作系统，而不是一次模型调用 {.unnumbered}\n\nAI Agent 的工程难点并不止于模型能否生成正确答案。当模型开始调用工具、修改环境、跨会话保持状态、与其他 Agent 协作并运行数分钟甚至数小时，问题会自然进入系统软件领域：状态在哪里、权限如何约束、副作用是否真的完成、进程崩溃怎样恢复、结果由谁验证、怎样评价一条长 trajectory、怎样证明优化没有破坏安全边界。\n\n本书沿着一条连续技术链展开：从模型输入输出接口开始，逐步加入 Context、Tool、RAG、Memory、MCP、Agent Runtime、Async、HITL、Sandbox、Checkpoint、Harness，再进入 Coding/Browser/Data/Research Agent、Workflow/Multi-Agent/A2A，最后落到 Evaluation、Security、Recovery、Performance、Production、Post-training 与 Self-improvement。每个核心机制都要求能在代码、实验、故障与主流开源实现中找到同构对象。\n"""


def write_pdf_repro_header(dst: Path, target: str):
    """Pin XeLaTeX dates and trailer identity for canonical PDFs."""
    if target == "book":
        inputs = [
            ROOT / "book/zh/SUMMARY.md",
            *chapter_paths(),
            *appendix_paths(),
            ROOT / PDF["book_style"],
            ROOT / "scripts/filters/pdf_diagrams.lua",
            ROOT / "scripts/filters/book_structure.lua",
        ]
    elif target == "workbook":
        inputs = [*lab_paths(), ROOT / PDF["workbook_style"]]
    else:
        return
    digest = hashlib.sha256()
    digest.update(f"{META['slug']}:{META['version']}:{target}".encode())
    for path in inputs:
        digest.update(path.relative_to(ROOT).as_posix().encode())
        digest.update(path.read_bytes())
    ident = digest.hexdigest()[:32]
    stamp = datetime.datetime.fromtimestamp(
        int(CFG["source_date_epoch"]), datetime.timezone.utc
    ).strftime("%Y%m%d%H%M%S")
    (dst / "reproducible-pdf.tex").write_text(
        "\\AtBeginDocument{\\special{pdf:docinfo << /CreationDate (D:"
        + stamp
        + "Z) /ModDate (D:"
        + stamp
        + "Z) >>}}\n"
        + "\\AtBeginDocument{\\special{pdf:trailerid [ <"
        + ident
        + "> <"
        + ident
        + "> ]}}\n",
        encoding="utf-8",
    )


def book_yaml() -> str:
    lines = [
        "project:",
        "  type: book",
        "  output-dir: _output",
        "book:",
        f"  title: {q(META['title'])}",
        f"  subtitle: {q(META['subtitle'])}",
        f"  author: {q(META['author'])}",
        f"  date: {q(META['version'] + ' · ' + META['release_date'])}",
        f"  output-file: {q('ai-agent-systems-course-' + META['version'])}",
        "  chapters:",
        '    - "index.qmd"',
    ]
    for part in summary_parts():
        lines += [f"    - part: {q(part['title'])}", "      chapters:"]
        lines += [f"        - {q('book/zh/' + ch['path'])}" for ch in part["chapters"]]
    lines += ["  appendices:"] + [f"    - {q('book/zh/' + p.name)}" for p in appendix_paths()]
    lines += [
        "format:",
        "  epub:",
        "    toc: true",
        "    toc-depth: 2",
        "    number-sections: true",
        "  pdf:",
        f"    documentclass: {q(PDF.get('documentclass', 'ctexbook'))}",
        "    classoption:",
    ]
    lines += [f"      - {q(x)}" for x in PDF.get("class_options", ["oneside", "openany"])]
    lines += [
        "    toc: true",
        f"    toc-depth: {int(PDF.get('toc_depth', 1))}",
        "    number-sections: true",
        "    pdf-engine: xelatex",
        "    latex-auto-install: false",
        '    babel-lang: "chinese"',
        f"    papersize: {q(PDF.get('paper_size', 'a4'))}",
        f"    geometry: {q('margin=' + PDF.get('margin', '2.4cm'))}",
        f"    mainfont: {q(FONTS.get('main', 'Noto Serif CJK SC'))}",
        f"    sansfont: {q(FONTS.get('sans', 'Noto Sans CJK SC'))}",
        f"    monofont: {q(FONTS.get('mono', 'Noto Sans Mono CJK SC'))}",
        "    include-in-header:",
        f"      - {q(PDF.get('book_style', 'book/assets/latex/book-style.tex'))}",
        '      - "reproducible-pdf.tex"',
        "filters:",
        "  - scripts/filters/book_structure.lua",
        "  - scripts/filters/pdf_diagrams.lua",
        f"lang: {q(META['lang'])}",
        "execute:",
        "  enabled: false",
    ]
    return "\n".join(lines) + "\n"


def site_yaml() -> str:
    ch = [f"book/zh/{p.relative_to(ROOT / 'book/zh').as_posix()}" for p in chapter_paths()]
    apps = [f"book/zh/{p.name}" for p in appendix_paths()]
    labs = [f"labs/core/{p.name}" for p in lab_paths()]
    lines = [
        "project:",
        "  type: website",
        "  output-dir: _output",
        "website:",
        f"  title: {q(META['title'])}",
        "  navbar:",
        "    left:",
        "      - href: index.qmd",
        "        text: 首页",
        "  sidebar:",
        "    style: docked",
        "    contents:",
    ]
    lines += [f"      - {q(x)}" for x in ch + apps + labs]
    lines += [
        "format:",
        "  html:",
        "    toc: true",
        f"    toc-depth: {int(PDF.get('html_toc_depth', 3))}",
        "    number-sections: true",
        "    theme: cosmo",
        "    code-copy: true",
        f"lang: {q(META['lang'])}",
        "execute:",
        "  enabled: false",
    ]
    return "\n".join(lines) + "\n"


def workbook_yaml() -> str:
    labs = [f"labs/core/{p.name}" for p in lab_paths()]
    lines = (
        [
            "project:",
            "  type: book",
            "  output-dir: _output",
            "book:",
            f"  title: {q(META['title'] + ' · Lab Workbook')}",
            f"  subtitle: {q('80 个可复现实验：正常路径与故障注入')}",
            f"  author: {q(META['author'])}",
            f"  date: {q(META['version'] + ' · ' + META['release_date'])}",
            f"  output-file: {q('agent-systems-lab-workbook-' + META['version'])}",
            "  chapters:",
            '    - "index.qmd"',
        ]
        + [f"    - {q(x)}" for x in labs]
        + [
            "format:",
            "  epub:",
            "    toc: true",
            "    toc-depth: 1",
            "  pdf:",
            f"    documentclass: {q(PDF.get('workbook_documentclass', 'ctexbook'))}",
            "    classoption:",
        ]
    )
    lines += [f"      - {q(x)}" for x in PDF.get("class_options", ["oneside", "openany"])]
    lines += [
        "    pdf-engine: xelatex",
        "    latex-auto-install: false",
        '    babel-lang: "chinese"',
        "    toc: true",
        "    toc-depth: 1",
        f"    papersize: {q(PDF.get('paper_size', 'a4'))}",
        f"    geometry: {q('margin=' + PDF.get('margin', '2.4cm'))}",
        f"    mainfont: {q(FONTS.get('main', 'Noto Serif CJK SC'))}",
        f"    sansfont: {q(FONTS.get('sans', 'Noto Sans CJK SC'))}",
        f"    monofont: {q(FONTS.get('mono', 'Noto Sans Mono CJK SC'))}",
        "    include-in-header:",
        f"      - {q(PDF.get('workbook_style', 'book/assets/latex/workbook-style.tex'))}",
        '      - "reproducible-pdf.tex"',
        f"lang: {q(META['lang'])}",
        "execute:",
        "  enabled: false",
    ]
    return "\n".join(lines) + "\n"


def prepare(target: str) -> Path:
    dst = BASE / target
    reset(dst)
    copy_sources(dst)
    if target == "book":
        annotate_appendix_titles(dst)
        (dst / "index.qmd").write_text(preface_text(), encoding="utf-8")
        y = book_yaml()
    elif target == "site":
        y = site_yaml()
        (dst / "index.qmd").write_text(
            f"# {META['title']}\n\n{META['subtitle']}\n\n版本：`{META['version']}`\n", encoding="utf-8"
        )
    elif target == "workbook":
        y = workbook_yaml()
        (dst / "index.qmd").write_text(
            "# Lab Workbook 使用说明 {.unnumbered}\n\n"
            "本册把 40 个主题拆成 80 个可执行实验：A 验证正常路径，B 注入故障并按证据等级判断检测、约束或恢复。"
            "每个 Lab 都给出运行命令、独立 oracle、预期不变量和证据边界。\n",
            encoding="utf-8",
        )
    else:
        raise ValueError(target)
    write_pdf_repro_header(dst, target)
    (dst / "_quarto.yml").write_text(y, encoding="utf-8")
    return dst


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("target", choices=["book", "site", "workbook", "all"], nargs="?", default="all")
    a = ap.parse_args()
    ts = ["book", "site", "workbook"] if a.target == "all" else [a.target]
    for t in ts:
        print("QUARTO_PROJECT_READY", t, prepare(t))
