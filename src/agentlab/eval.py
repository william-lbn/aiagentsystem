from __future__ import annotations
from dataclasses import dataclass
from statistics import mean


@dataclass(slots=True)
class EvalCase:
    name: str
    input: str
    verifier: callable


class EvalHarness:
    def run(self, fn, cases: list[EvalCase]):
        rows = []
        for c in cases:
            out = fn(c.input)
            passed = bool(c.verifier(out))
            rows.append({"name": c.name, "passed": passed, "output": out})
        return {"pass_rate": mean([r["passed"] for r in rows]) if rows else 0.0, "cases": rows}
