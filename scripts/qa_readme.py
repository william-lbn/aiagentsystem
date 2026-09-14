from __future__ import annotations

import re
from pathlib import Path

from common import ROOT, appendix_paths, chapter_paths, course, lab_paths


LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")


def relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def main() -> int:
    readme_path = ROOT / "README.md"
    text = readme_path.read_text(encoding="utf-8")
    targets = [match.strip().split()[0] for match in LINK_RE.findall(text)]
    errors: list[str] = []

    local_targets: list[str] = []
    for target in targets:
        if target.startswith(("http://", "https://", "mailto:", "#")):
            continue
        path_part = target.split("#", 1)[0]
        if not path_part:
            continue
        local_targets.append(path_part)
        if not (ROOT / path_part).exists():
            errors.append(f"broken local link: {target}")

    expected_chapters = {relative(path) for path in chapter_paths()}
    expected_appendices = {relative(path) for path in appendix_paths()}
    expected_labs = {relative(path) for path in lab_paths()}
    actual_chapters = {target for target in local_targets if target.startswith("book/zh/chapters/")}
    actual_appendices = {target for target in local_targets if target.startswith("book/zh/appendix-")}
    actual_labs = {target for target in local_targets if target.startswith("labs/core/lab-")}

    for label, expected, actual in (
        ("chapter", expected_chapters, actual_chapters),
        ("appendix", expected_appendices, actual_appendices),
        ("lab", expected_labs, actual_labs),
    ):
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        if missing:
            errors.append(f"missing {label} links: {missing}")
        if extra:
            errors.append(f"unexpected {label} links: {extra}")

    version = str(course()["version"])
    base = f"https://github.com/william-lbn/aiagentsystem/releases/download/{version}"
    required_assets = {
        f"{base}/AI-Agent-Systems-Course-{version}-BOOK.zip",
        f"{base}/AI-Agent-Systems-Course-{version}-CODE-LABS.zip",
        f"{base}/AI-Agent-Systems-Course-{version}-SLIDES.zip",
        f"{base}/AI-Agent-Systems-Course-{version}-ALL-DELIVERABLES.zip",
        f"{base}/AI-Agent-Systems-Course-{version}-PYTHON-SBOM.cdx.json",
        f"{base}/SHA256SUMS.txt",
    }
    missing_assets = sorted(required_assets - set(targets))
    if missing_assets:
        errors.append(f"missing versioned release links: {missing_assets}")

    required_phrases = (
        "下载主书 PDF / EPUB / HTML",
        "本项目目前只维护简体中文",
        "四十章正文与实验导航",
        "从教学 fixture 到真实外部证据",
    )
    for phrase in required_phrases:
        if phrase not in text:
            errors.append(f"missing README contract phrase: {phrase}")

    if errors:
        print("README_QA_FAILED")
        for error in errors:
            print(f"- {error}")
        return 1

    print(
        "README_QA_OK "
        f"local_links={len(local_targets)} chapters={len(actual_chapters)} "
        f"appendices={len(actual_appendices)} labs={len(actual_labs)} "
        f"release_assets={len(required_assets)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
