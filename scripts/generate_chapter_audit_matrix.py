"""Recompute structural chapter coverage without claiming scientific correctness.

`--check` is read-only and fails when the committed matrix drifts from source.
`--write` is an explicit bulk mechanical regeneration of the audit artifact.
"""

from __future__ import annotations

import argparse
import re

from common import ROOT, chapter_paths


TARGET = ROOT / "docs/CHAPTER_AUDIT_MATRIX.md"
REQUIRED_HEADINGS = (
    "问题背景与学习目标",
    "原理与理论基础",
    "从原理到实现",
    "可复现实验",
    "技术边界与设计取舍",
)


def render() -> str:
    lines = [
        "# 全书章节审计矩阵（源码结构核验）",
        "",
        "本表由 `python scripts/generate_chapter_audit_matrix.py --write` 从当前 canonical 章节和 Core Labs 机械生成；CI 使用 `--check` 防止陈旧数字。它**只核验结构、文件与链接入口**，不把章节长度、代码块数或存在实验等同于理论正确、模型效果、外部 SDK 互操作或 L5 证据。协议/研究事实的书内时间边界仍为 2026-09-11。",
        "",
        "全书实质性审计结论与未完成项见 [Full-Book Technical Audit](FULL_BOOK_TECHNICAL_AUDIT.md)。若新增理论主张、性能数字、外部兼容声明或训练结果，必须单独提交来源、执行日志、verifier 与环境身份。",
        "",
        "| 章 | Canonical 正文 | UTF-8 字节 | Python 块 | 图 | 外链 | A/B 实验入口 | 必备论证结构 |",
        "|---|---|---:|---:|---:|---:|---|---|",
    ]
    chapters = chapter_paths()
    if len(chapters) != 40:
        raise ValueError(f"expected 40 chapters, found {len(chapters)}")
    for index, path in enumerate(chapters, start=1):
        raw = path.read_bytes()
        source = raw.decode("utf-8")
        title = source.splitlines()[0].removeprefix("# ").replace("|", "\\|")
        python_blocks = len(re.findall(r"^```(?:python|py)\s*$", source, re.M))
        diagrams = len(re.findall(r"!\[[^]]*\]\([^)]*\)", source))
        external_links = len(set(re.findall(r"https?://[^\s)]+", source)))
        labs = sorted((ROOT / "labs/core").glob(f"lab-{index:02d}[AB]-*.md"))
        entries = []
        for letter in "AB":
            matches = [lab for lab in labs if lab.name.startswith(f"lab-{index:02d}{letter}-")]
            entries.append(
                f"[{letter}](../labs/core/{matches[0].name})" if len(matches) == 1 else f"{letter}:缺失/重复"
            )
        missing = [heading for heading in REQUIRED_HEADINGS if f"## {heading}" not in source]
        structure = "齐全" if not missing else "缺：" + "、".join(missing)
        lines.append(
            f"| {index:02d} | [{title}](../book/zh/chapters/{path.name}) | {len(raw)} | "
            f"{python_blocks} | {diagrams} | {external_links} | {' / '.join(entries)} | {structure} |"
        )
    lines += [
        "",
        "判读：A/B 表示正常路径与故障路径的教材入口存在；是否实际执行见 `VALIDATION_REPORT.md` 和对应 CI run。外链数仅统计 URL 的出现，不保证链接内容、日期或主张获验证。目录级 QA 无法代替逐条研究核证或外部可复现性。",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", action="store_true")
    group.add_argument("--check", action="store_true")
    args = parser.parse_args()
    expected = render()
    if args.write:
        TARGET.write_text(expected, encoding="utf-8")
        print(f"CHAPTER_AUDIT_MATRIX_UPDATED chapters=40 path={TARGET}")
        return 0
    actual = TARGET.read_text(encoding="utf-8") if TARGET.exists() else ""
    if actual != expected:
        print("CHAPTER_AUDIT_MATRIX_STALE: run python scripts/generate_chapter_audit_matrix.py --write")
        return 1
    print("CHAPTER_AUDIT_MATRIX_OK chapters=40")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
