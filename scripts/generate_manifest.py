from __future__ import annotations
from common import ROOT, course

META = course()
OUT = ROOT / "MANIFEST.md"
IGNORE_PARTS = {".git", ".venv", ".build", ".pytest_cache", "__pycache__", ".agentlab", "dist"}
IGNORE_NAMES = {"MANIFEST.md", "FILE_SHA256SUMS.txt", "agentops.db", ".DS_Store"}
rows = []
for p in sorted(ROOT.rglob("*")):
    if not p.is_file():
        continue
    rel = p.relative_to(ROOT)
    if any(part in IGNORE_PARTS for part in rel.parts) or p.name in IGNORE_NAMES:
        continue
    rows.append((str(rel), p.stat().st_size))
lines = [
    f"# {META['title']} {META['version']} 文件清单",
    "",
    "> 本清单由 `python scripts/generate_manifest.py` 生成。缓存、数据库运行态和 Python bytecode 不进入统计。",
    "",
    f"- 文件数：**{len(rows)}**",
    f"- 总字节数：**{sum(size for _, size in rows):,}**",
    "",
    "| 路径 | 大小(bytes) |",
    "|---|---:|",
]
lines += [f"| `{rel}` | {size} |" for rel, size in rows]
OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"MANIFEST_OK files={len(rows)} bytes={sum(size for _, size in rows)}")
