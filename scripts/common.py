from __future__ import annotations
from pathlib import Path
import re
import tomllib

ROOT = Path(__file__).resolve().parents[1]


def config() -> dict:
    return tomllib.loads((ROOT / "course.toml").read_text(encoding="utf-8"))


def course() -> dict:
    return config()["course"]


def build_cfg() -> dict:
    return config()["build"]


def fonts_cfg() -> dict:
    return config().get("fonts", {})


def pdf_cfg() -> dict:
    return config().get("pdf", {})


def summary_parts() -> list[dict]:
    summary = (ROOT / "book/zh/SUMMARY.md").read_text(encoding="utf-8")
    parts: list[dict] = []
    current = None
    for line in summary.splitlines():
        if line.startswith("## ") and line[3:].strip() != "附录":
            current = {"title": line[3:].strip(), "chapters": []}
            parts.append(current)
        elif line.startswith("- [") and current:
            m = re.match(r"- \[(.+?)\]\((.+?)\)", line)
            if m and m.group(2).startswith("chapters/"):
                current["chapters"].append({"title": m.group(1), "path": m.group(2)})
    return parts


def chapter_paths() -> list[Path]:
    zh = ROOT / "book/zh"
    return [zh / c["path"] for p in summary_parts() for c in p["chapters"]]


def appendix_paths() -> list[Path]:
    zh = ROOT / "book/zh"
    summary = (zh / "SUMMARY.md").read_text(encoding="utf-8")
    out = []
    for line in summary.splitlines():
        m = re.match(r"- \[(.+?)\]\((appendix-[^)]+\.md)\)", line)
        if m:
            out.append(zh / m.group(2))
    return out


def lab_paths() -> list[Path]:
    return sorted((ROOT / "labs/core").glob("lab-*.md"))


def section_text(text: str, heading: str, next_heading: str | None = None) -> str:
    start = re.search(rf"^##\s+{re.escape(heading)}\s*$", text, re.M)
    if not start:
        return ""
    tail = text[start.end() :]
    if next_heading:
        end = re.search(rf"^##\s+{re.escape(next_heading)}\s*$", tail, re.M)
        if end:
            return tail[: end.start()]
    return tail
