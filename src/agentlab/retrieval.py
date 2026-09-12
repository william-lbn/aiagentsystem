from __future__ import annotations
import re
import math
from collections import Counter


class HybridRetriever:
    def __init__(self, docs: list[dict]):
        self.docs = docs

    def search(self, query: str, k=4):
        q = set(_tokens(query))
        rows = []
        for d in self.docs:
            toks = _tokens(d["text"])
            c = Counter(toks)
            lexical = sum(c[t] for t in q)
            overlap = len(q & set(toks)) / (len(q) or 1)
            freshness = float(d.get("freshness", 0.5))
            score = 0.55 * math.log1p(lexical) + 0.35 * overlap + 0.10 * freshness
            rows.append({**d, "score": round(score, 4)})
        return sorted(rows, key=lambda x: x["score"], reverse=True)[:k]


def _tokens(s):
    return re.findall(r"[A-Za-z0-9_\u4e00-\u9fff]+", s.lower())
