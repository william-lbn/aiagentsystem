from agentlab import AgentRuntime, ModelDecision, ScriptedModel, ToolRegistry, tool


@tool("Add two integers")
def add(a: int, b: int) -> int:
    return a + b


tools = ToolRegistry()
tools.register(add)
model = ScriptedModel(
    [ModelDecision(tool="add", args={"a": 7, "b": 5}, rationale="Need an exact sum"), ModelDecision(final="12")]
)
print(AgentRuntime(model, tools).run("7+5 等于多少？"))
