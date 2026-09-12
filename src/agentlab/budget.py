from dataclasses import dataclass


@dataclass
class RuntimeBudget:
    max_steps: int = 12
    max_model_calls: int = 12
    max_tool_calls: int = 20
    model_calls: int = 0
    tool_calls: int = 0

    def check(self, next_step: int):
        if next_step > self.max_steps:
            return False, "max_steps"
        if self.model_calls >= self.max_model_calls:
            return False, "max_model_calls"
        if self.tool_calls >= self.max_tool_calls:
            return False, "max_tool_calls"
        return True, "ok"

    def charge_model(self):
        self.model_calls += 1

    def charge_tool(self):
        self.tool_calls += 1
