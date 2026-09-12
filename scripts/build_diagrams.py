from __future__ import annotations
from pathlib import Path
import argparse
import hashlib
import os
import shutil
import subprocess
from common import ROOT, build_cfg

SRC = ROOT / "book/assets/diagrams"
PDF = SRC / "pdf"
FONT_FAMILY = "Noto Sans CJK SC"


def graphviz_font_file() -> Path:
    if not shutil.which("fc-match"):
        raise SystemExit("fontconfig `fc-match` is required to resolve the diagram font.")
    cp = subprocess.run(
        ["fc-match", "--format=%{file}\n", FONT_FAMILY],
        capture_output=True,
        text=True,
        check=True,
    )
    path = Path(cp.stdout.splitlines()[0].strip()).expanduser() if cp.stdout.strip() else None
    if not path or not path.is_file():
        raise SystemExit(f"Unable to resolve diagram font file for {FONT_FAMILY!r}.")
    return path


def render_dot(dot: Path, fmt: str, out: Path, *extra: str) -> None:
    """Render with an explicit font file, independent of sandbox font lookup.

    Graphviz can resolve the same family to different metrics across macOS
    sandbox boundaries.  Feeding the resolved filename fixes layout geometry;
    SVG output is then restored to the portable family name for browsers.
    """
    if not shutil.which("dot"):
        raise SystemExit("Graphviz `dot` is required. Install graphviz before building diagrams.")
    font = graphviz_font_file()
    source = dot.read_text(encoding="utf-8")
    family_token = f'fontname="{FONT_FAMILY}"'
    if family_token not in source:
        raise SystemExit(f"{dot.name}: missing locked font token {family_token}")
    source = source.replace(family_token, f'fontname="{font.name}"')
    env = os.environ.copy()
    search = [str(font.parent)]
    if env.get("DOT_FONT_PATH"):
        search.append(env["DOT_FONT_PATH"])
    env["DOT_FONT_PATH"] = os.pathsep.join(search)
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["dot", f"-T{fmt}", *extra, "-o", str(out)],
        input=source,
        text=True,
        env=env,
        check=True,
    )
    if fmt == "svg":
        text = out.read_text(encoding="utf-8")
        text = text.replace(f'font-family="{font.name}"', f'font-family="{FONT_FAMILY}"')
        source_hash = hashlib.sha256(dot.read_bytes()).hexdigest()
        marker = f"<!-- DOT-SHA256: {source_hash} -->\n"
        text = text.replace("<!-- Title:", marker + "<!-- Title:", 1)
        out.write_text(text, encoding="utf-8")


def main(*, update_svg: bool = False) -> None:
    PDF.mkdir(parents=True, exist_ok=True)
    count = 0
    for dot in sorted(SRC.glob("*.dot")):
        stem = dot.stem
        # SVG is a committed review preview. Routine book/site/slide builds must
        # not rewrite it because Graphviz geometry can vary across host security
        # contexts even with an explicit font file. `--update-svg` is deliberate.
        svg = SRC / f"{stem}.svg"
        if update_svg:
            render_dot(dot, "svg", svg)
        elif not svg.exists():
            raise SystemExit(f"MISSING_COMMITTED_SVG {svg}")
        # PNG is for PPTX and quick previews. 180 dpi matches the existing visual scale.
        render_dot(dot, "png", SRC / f"{stem}.png", "-Gdpi=180")
        # PDF is a build-time vector derivative used by XeLaTeX.
        render_dot(dot, "pdf", PDF / f"{stem}.pdf")
        count += 1

    expected = int(build_cfg()["expected_diagrams"])
    if count != expected:
        raise SystemExit(f"DIAGRAM_COUNT_MISMATCH generated={count} expected={expected}")
    print(f"DIAGRAMS_BUILT count={count}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--update-svg", action="store_true")
    main(update_svg=ap.parse_args().update_svg)
