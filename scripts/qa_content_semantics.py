from __future__ import annotations
from collections import Counter, defaultdict
from difflib import SequenceMatcher
import json
import re
from common import ROOT, chapter_paths, course

errors = []
meta = course()


def req(c, m):
    if not c:
        errors.append(m)


required_docs = [
    "FULL_BOOK_TECHNICAL_AUDIT.md",
    "CHAPTER_AUDIT_MATRIX.md",
    "EXPERIMENT_REPRODUCTION_REPORT.md",
    "RESEARCH_REFRESH_2026-09-10.md",
    "SOURCE_VERIFICATION_2026-09-10.md",
    "CONTENT_CHANGELOG.md",
    "FINAL_VALIDATION_REPORT.md",
]
for name in required_docs:
    p = ROOT / "docs" / name
    req(p.exists() and p.stat().st_size > 1000, f"missing audit doc {name}")

paras = []
for p in chapter_paths():
    text = p.read_text(encoding="utf-8")
    req("深度审计与研究证据链" in text, f"{p.name}: missing version-neutral evidence block")
    req(
        not re.search(r"^###\s+V\d+\s+深度审计", text, re.M | re.I),
        f"{p.name}: versioned QA meta heading leaked into book",
    )
    for forbidden in ["如何写这本书", "AI 如何生成本章", "本章为什么这样安排"]:
        req(forbidden not in text, f"{p.name}: forbidden meta phrase {forbidden}")
    for para in re.split(r"\n\s*\n", text):
        s = " ".join(para.strip().split())
        structured_evidence = (
            (s.startswith("PASS：退出码") and "passed=true" in s and "完整手册" in s)
            or ("def main() -> int:" in s and "run_scenario(" in s)
            or s.startswith("**实验语义边界。**")
        )
        if (
            len(s) < 80
            or s.startswith(("-", "|", "```", "![", "#"))
            or "实验环境" in s
            or "source_locks" in s
            or structured_evidence
        ):
            continue
        paras.append((p.name, s))

# 1) Exact prose duplication. 80 chars is deliberate: the old 220-char gate
# missed templated paragraphs that were individually short but repeated 40x.
c = Counter(s for _, s in paras)
exact = [(n, t[:180]) for t, n in c.items() if n >= 3]
req(not exact, f"repeated prose >=80 chars groups={len(exact)} sample={exact[:3]}")


# 2) Normalized duplication: remove incidental version/lab/code/URL differences
# so a template cannot evade the gate by changing only chapter numbers/symbols.
def normalize(s: str) -> str:
    x = s.lower()
    x = re.sub(r"https?://\S+", "<url>", x)
    x = re.sub(r"`[^`]+`", "<code>", x)
    x = re.sub(r"\b\d+(?:\.\d+)*\b", "<n>", x)
    x = re.sub(r"第\s*\d+\s*章", "第<n>章", x)
    return re.sub(r"\s+", " ", x).strip()


ngroups = defaultdict(set)
nsample = {}
normalized = []
for fname, s in paras:
    n = normalize(s)
    if len(n) >= 100:
        ngroups[n].add(fname)
        nsample[n] = s
        normalized.append((fname, n, s))
normalized_repeated = [(len(fs), nsample[n][:180]) for n, fs in ngroups.items() if len(fs) >= 3]
req(not normalized_repeated, f"normalized template groups={len(normalized_repeated)} sample={normalized_repeated[:3]}")

# 3) Conservative fuzzy gate. Only compare paragraphs with similar length and a
# common opening; this catches lightly rewritten boilerplate without making QA
# quadratic over every unrelated paragraph. Connected components spanning >=3
# chapters are rejected.
parent = list(range(len(normalized)))


def find(x):
    while parent[x] != x:
        parent[x] = parent[parent[x]]
        x = parent[x]
    return x


def union(a, b):
    ra, rb = find(a), find(b)
    if ra != rb:
        parent[rb] = ra


by_prefix = defaultdict(list)
for i, (_, n, _) in enumerate(normalized):
    key = re.sub(r"<(?:code|url|n)>", "", n)[:24]
    if len(key) >= 12:
        by_prefix[key].append(i)
for ids in by_prefix.values():
    if len(ids) < 2:
        continue
    for pos, a in enumerate(ids):
        na = normalized[a][1]
        for b in ids[pos + 1 :]:
            nb = normalized[b][1]
            if min(len(na), len(nb)) / max(len(na), len(nb)) < 0.90:
                continue
            if SequenceMatcher(None, na, nb, autojunk=False).ratio() >= 0.94:
                union(a, b)
components = defaultdict(list)
for i, item in enumerate(normalized):
    components[find(i)].append(item)
fuzzy = []
for items in components.values():
    chapters = {x[0] for x in items}
    if len(chapters) >= 3:
        fuzzy.append((len(chapters), items[0][2][:180]))
req(not fuzzy, f"fuzzy template groups={len(fuzzy)} sample={fuzzy[:3]}")

locks = json.loads((ROOT / "integrations/SOURCE_LOCK.json").read_text(encoding="utf-8"))
for key in [
    "semantic-transactions",
    "aip-agent-identity",
    "ogx",
    "memora",
    "mem2actbench",
    "longmemeval-v2",
    "agentdyn",
    "aidev",
    "otel-genai",
    "owasp-agent-control-standard",
    "owasp-agentic-top10-2026",
    "mcp-spec-release-2026-07-28",
]:
    req(key in locks, f"missing refreshed source lock {key}")
if errors:
    print("CONTENT_SEMANTICS_QA_FAILED")
    [print("-", e) for e in errors]
    raise SystemExit(1)
print(
    f"CONTENT_SEMANTICS_QA_OK version={meta['version']} chapters={len(chapter_paths())} audit_docs={len(required_docs)} exact_repeat_max={max(c.values() or [0])} normalized_repeat_max={max([len(v) for v in ngroups.values()] or [0])} fuzzy_groups=0 source_locks={len(locks)}"
)
