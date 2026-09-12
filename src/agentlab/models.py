from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(slots=True)
class ModelDecision:
    final: str | None = None
    tool: str | None = None
    args: dict[str, Any] | None = None
    rationale: str | None = None


class Model(Protocol):
    def complete(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> ModelDecision: ...


class ScriptedModel:
    """Deterministic model for teaching and regression tests.

    Each call returns the next predeclared ModelDecision. It intentionally
    removes provider/network randomness so students can single-step the runtime.
    """

    def __init__(self, decisions: list[ModelDecision]):
        self.decisions = list(decisions)
        self.index = 0

    def complete(self, messages, tools):
        if self.index >= len(self.decisions):
            return ModelDecision(final="script exhausted")
        decision = self.decisions[self.index]
        self.index += 1
        return decision
