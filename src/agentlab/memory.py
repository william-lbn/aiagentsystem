from __future__ import annotations
from dataclasses import dataclass
import math
import re
from collections import Counter


@dataclass(slots=True)
class MemoryItem:
    key: str
    text: str
    metadata: dict


class MemoryStore:
    def __init__(self):
        self.items: list[MemoryItem] = []

    def add(self, key, text, **metadata):
        self.items.append(MemoryItem(key, text, metadata))

    def search(self, query, k=3):
        q = Counter(_tokens(query))
        scored = []
        for item in self.items:
            d = Counter(_tokens(item.text))
            dot = sum(q[t] * d[t] for t in q)
            nq = math.sqrt(sum(v * v for v in q.values())) or 1
            nd = math.sqrt(sum(v * v for v in d.values())) or 1
            scored.append((dot / (nq * nd), item))
        return [x[1] for x in sorted(scored, key=lambda x: x[0], reverse=True)[:k] if x[0] > 0]


def _tokens(s):
    return re.findall(r"[A-Za-z0-9_\u4e00-\u9fff]+", s.lower())
