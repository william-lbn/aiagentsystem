from __future__ import annotations
from common import ROOT, course, summary_parts, appendix_paths

ZH = ROOT / "book/zh"
META = course()

front = f'''---
title: "{META["title"]}"
subtitle: "{META["subtitle"]}"
author: "{META["author"]}"
date: "{META["version"]} · {META["release_date"]}"
lang: {META["lang"]}
---

# 导言：把 Agent 当作系统，而不是一次模型调用 {{.unnumbered}}

AI Agent 的工程难点并不止于模型能否生成正确答案。当模型开始调用工具、修改环境、跨会话保持状态、与其他 Agent 协作并运行数分钟甚至数小时，问题会自然进入系统软件领域：状态在哪里、权限如何约束、副作用是否真的完成、进程崩溃怎样恢复、结果由谁验证、怎样评价一条长 trajectory、怎样证明优化没有破坏安全边界。

本书沿着一条连续技术链展开：从模型输入输出接口开始，逐步加入 Context、Tool、RAG、Memory、MCP、Agent Runtime、Async、HITL、Sandbox、Checkpoint、Harness，再进入 Coding/Browser/Data/Research Agent、Workflow/Multi-Agent/A2A，最后落到 Evaluation、Security、Recovery、Performance、Production、Post-training 与 Self-improvement。每个核心机制都要求能在代码、实验、故障与主流开源实现中找到同构对象。

'''


def normalize_for_assembled(text: str) -> str:
    # Chapter files remain independently readable from book/zh/chapters.
    # Only the generated aggregate adjusts relative resource paths.
    text = text.replace("](../../assets/diagrams/", "](assets/diagrams/")
    text = text.replace("](../../../labs/", "](../../labs/")
    return text


def mark_appendix_heading(text: str) -> str:
    # Keep explicit A/B/C/D labels in HTML/EPUB, while the LaTeX AST filter
    # removes the prefix and lets ctexbook generate native appendix lettering.
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if line.startswith("# "):
            title = line[2:].strip()
            lines[i] = f"# {title} {{.unnumbered .appendix-title}}"
            break
    return "\n".join(lines) + ("\n" if text.endswith("\n") else "")


out = [front]
for part in summary_parts():
    if not part["chapters"]:
        continue
    out.append(f"\n# {part['title']} {{.unnumbered .part}}\n")
    for ch in part["chapters"]:
        out.append(normalize_for_assembled((ZH / ch["path"]).read_text(encoding="utf-8")))
        out.append("\n\n")

out.append("\n# 附录 {.unnumbered .appendices-start}\n")
for path in appendix_paths():
    out.append(mark_appendix_heading(path.read_text(encoding="utf-8")))
    out.append("\n\n")

book = ZH / "book.md"
book.write_text("".join(out), encoding="utf-8")
print("ASSEMBLED", book)
