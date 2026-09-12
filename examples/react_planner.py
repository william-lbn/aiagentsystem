from agentlab import AgentRuntime, ModelDecision, ScriptedModel, ToolRegistry, tool


@tool("Search a tiny deterministic corpus")
def search(query: str) -> str:
    data = {"mcp": "MCP standardizes tools/resources/prompts", "a2a": "A2A standardizes agent-to-agent tasks"}
    return data.get(query.lower(), "not found")


tools = ToolRegistry()
tools.register(search)
model = ScriptedModel(
    [
        ModelDecision(tool="search", args={"query": "mcp"}, rationale="Need protocol definition"),
        ModelDecision(tool="search", args={"query": "a2a"}, rationale="Need contrast"),
        ModelDecision(final="MCP 面向工具/资源互操作；A2A 面向 Agent 之间的任务协作。"),
    ]
)
print(AgentRuntime(model, tools).run("比较 MCP 和 A2A"))
