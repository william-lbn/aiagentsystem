from agentlab.protocols import (
    MCPTool,
    MCP_PROTOCOL_VERSION,
    MCP_PROTOCOL_VERSION_META_KEY,
    MCP_CLIENT_CAPABILITIES_META_KEY,
    MCP_PROTOCOL_VERSION_HEADER,
    MCP_METHOD_HEADER,
    MCP_NAME_HEADER,
    validate_mcp_2026_request,
    AgentInterface,
    AgentSkill,
    AgentCard,
    A2ATask,
    validate_a2a_1_0,
)

mcp_tool = MCPTool("search_docs", "Search local docs", {"type": "object", "properties": {"q": {"type": "string"}}})
mcp_request = {
    "jsonrpc": "2.0",
    "id": "example-request",
    "method": "tools/call",
    "params": {
        "name": mcp_tool.name,
        "arguments": {"q": "MCP"},
        "_meta": {
            MCP_PROTOCOL_VERSION_META_KEY: MCP_PROTOCOL_VERSION,
            MCP_CLIENT_CAPABILITIES_META_KEY: {},
        },
    },
}
mcp_ok, mcp_errors = validate_mcp_2026_request(
    mcp_request,
    headers={
        MCP_PROTOCOL_VERSION_HEADER: MCP_PROTOCOL_VERSION,
        MCP_METHOD_HEADER: "tools/call",
        MCP_NAME_HEADER: mcp_tool.name,
    },
)

card = AgentCard(
    name="research-agent",
    description="Research with citations",
    supported_interfaces=[AgentInterface("http://localhost:9001/a2a", "JSONRPC")],
    version="1.0.0",
    default_input_modes=["text/plain"],
    default_output_modes=["text/markdown"],
    skills=[AgentSkill("research", "Research", "Search and synthesize cited evidence", ["research", "citation"])],
    capabilities={},
).to_wire()
task = A2ATask(
    "task-001",
    "ctx-001",
    "TASK_STATE_COMPLETED",
    artifacts=[{"artifactId": "report-1", "name": "report.md", "parts": []}],
).to_wire()
a2a_ok, a2a_errors = validate_a2a_1_0(card, task)
print({"mcp_tool": mcp_tool, "mcp_valid": mcp_ok, "mcp_errors": mcp_errors})
print({"agent_card": card, "task": task, "a2a_valid": a2a_ok, "a2a_errors": a2a_errors})
raise SystemExit(0 if mcp_ok and a2a_ok else 1)
