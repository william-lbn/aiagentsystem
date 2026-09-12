from __future__ import annotations
import argparse
import json
import platform
import re
import shutil
import subprocess
import sys
from common import course, build_cfg, fonts_cfg

ap = argparse.ArgumentParser()
ap.add_argument("--canonical", action="store_true")
a = ap.parse_args()
errors = []
info = {"python": platform.python_version()}
cfg = build_cfg()
fonts = fonts_cfg()
lo = tuple(map(int, str(cfg["min_python"]).split(".")))
hi = tuple(map(int, str(cfg["max_python_exclusive"]).split(".")))
if not (lo <= sys.version_info[:2] < hi):
    errors.append(f"Python {platform.python_version()} outside {cfg['min_python']}..<{cfg['max_python_exclusive']}")
required = ["xelatex", "dot", "fc-match", "pdfinfo", "pdftotext", "kpsewhich", "cargo", "rustc"]
required += ["quarto", "tlmgr"] if a.canonical else ["pandoc"]
for cmd in required:
    if not shutil.which(cmd):
        errors.append(f"missing command: {cmd}")

# Quarto deliberately bundles the Pandoc version against which it is tested.
# A distro's unrelated ``pandoc`` executable may be older and is not used by
# ``quarto render``. Compatibility builds continue to inspect plain Pandoc.
pandoc_cmd = ["quarto", "pandoc", "--version"] if a.canonical else ["pandoc", "--version"]
pandoc_available = shutil.which("quarto") if a.canonical else shutil.which("pandoc")
if pandoc_available:
    cp = subprocess.run(pandoc_cmd, text=True, capture_output=True)
    lines = cp.stdout.splitlines()
    out = lines[0] if lines else ""
    info["pandoc"] = out
    info["pandoc_provider"] = "quarto-embedded" if a.canonical else "system"
    if cp.returncode != 0 or not out:
        errors.append(f"unable to inspect {'Quarto-embedded' if a.canonical else 'system'} Pandoc")
    m = re.search(r"(\d+)\.(\d+)", out)
    if not m:
        errors.append(f"unparseable Pandoc version: {out!r}")
    elif (int(m.group(1)), int(m.group(2))) < (3, 1):
        errors.append("pandoc >=3.1 required")
if shutil.which("xelatex"):
    info["xelatex"] = subprocess.run(["xelatex", "--version"], text=True, capture_output=True).stdout.splitlines()[0]
if shutil.which("dot"):
    cp = subprocess.run(["dot", "-V"], text=True, capture_output=True)
    info["graphviz"] = (cp.stderr or cp.stdout).strip()
if shutil.which("fc-match"):
    for role, font in fonts.items():
        cp = subprocess.run(["fc-match", "-f", "%{family}", font], text=True, capture_output=True)
        out = cp.stdout.strip()
        info[f"font:{role}"] = out
        # fontconfig silently returns a fallback family for an unknown request.
        # An arbitrary non-empty result therefore cannot prove that XeLaTeX can
        # load the exact family declared in course.toml.
        matched_families = {part.strip().casefold() for part in out.split(",") if part.strip()}
        if font.casefold() not in matched_families:
            errors.append(f"font unavailable: requested {font!r}, resolved to {out!r}")

if shutil.which("kpsewhich"):
    for tex in ("ctexbook.cls", "fvextra.sty", "fancyhdr.sty", "needspace.sty"):
        out = subprocess.run(["kpsewhich", tex], text=True, capture_output=True).stdout.strip()
        info[f"tex:{tex}"] = out
        if not out:
            errors.append(f"missing TeX component: {tex}")
if a.canonical:
    if not shutil.which("quarto"):
        errors.append("canonical build requires quarto")
    else:
        q = subprocess.run(["quarto", "--version"], text=True, capture_output=True).stdout.strip()
        info["quarto"] = q
        if q != str(cfg["quarto_version"]):
            errors.append(f"quarto {q} != {cfg['quarto_version']}")
print(json.dumps(info, ensure_ascii=False, indent=2))
if errors:
    for e in errors:
        print("TOOLCHAIN_ERROR", e, file=sys.stderr)
    raise SystemExit(1)
print("TOOLCHAIN_OK", course()["version"], "canonical" if a.canonical else "compatibility")
