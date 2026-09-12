from __future__ import annotations
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class PolicyDecision:
    allowed: bool = True
    reason: str = "allowed"
    require_approval: bool = False


class PolicyEngine:
    def __init__(self, blocked_prompt_tokens=None, approval_tools=None, denied_tools=None):
        self.blocked_prompt_tokens = blocked_prompt_tokens or ["ignore previous instructions", "exfiltrate secret"]
        self.approval_tools = set(approval_tools or [])
        self.denied_tools = set(denied_tools or [])

    def check_prompt(self, text: str) -> PolicyDecision:
        low = text.lower()
        if any(x in low for x in self.blocked_prompt_tokens):
            return PolicyDecision(False, "prompt_policy")
        return PolicyDecision()

    def check_tool(self, name: str, args: dict[str, Any]) -> PolicyDecision:
        if name in self.denied_tools:
            return PolicyDecision(False, "tool_denied")
        if name in self.approval_tools:
            return PolicyDecision(True, "human_approval_required", True)
        return PolicyDecision()
