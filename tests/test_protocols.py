from agentlab.protocols import (
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


def test_mcp_2026_per_request_version_metadata_and_header_agree():
    req = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "lookup",
            "arguments": {},
            "_meta": {
                MCP_PROTOCOL_VERSION_META_KEY: MCP_PROTOCOL_VERSION,
                MCP_CLIENT_CAPABILITIES_META_KEY: {},
            },
        },
    }
    ok, errors = validate_mcp_2026_request(
        req,
        headers={
            MCP_PROTOCOL_VERSION_HEADER: MCP_PROTOCOL_VERSION,
            MCP_METHOD_HEADER: "tools/call",
            MCP_NAME_HEADER: "lookup",
        },
    )
    assert ok and errors == []


def test_mcp_header_body_mismatch_is_rejected():
    req = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "lookup",
            "arguments": {},
            "_meta": {
                MCP_PROTOCOL_VERSION_META_KEY: MCP_PROTOCOL_VERSION,
                MCP_CLIENT_CAPABILITIES_META_KEY: {},
            },
        },
    }
    ok, errors = validate_mcp_2026_request(
        req,
        headers={
            MCP_PROTOCOL_VERSION_HEADER: "2025-11-25",
            MCP_METHOD_HEADER: "tools/call",
            MCP_NAME_HEADER: "lookup",
        },
    )
    assert not ok and "header_body_version_mismatch" in errors


def test_mcp_top_level_meta_is_not_a_modern_request_envelope():
    req = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/list",
        "params": {},
        "_meta": {
            MCP_PROTOCOL_VERSION_META_KEY: MCP_PROTOCOL_VERSION,
            MCP_CLIENT_CAPABILITIES_META_KEY: {},
        },
    }
    ok, errors = validate_mcp_2026_request(req)
    assert not ok and errors == ["missing_or_invalid_meta"]


def test_mcp_http_method_and_name_headers_are_checked():
    req = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "lookup",
            "arguments": {},
            "_meta": {
                MCP_PROTOCOL_VERSION_META_KEY: MCP_PROTOCOL_VERSION,
                MCP_CLIENT_CAPABILITIES_META_KEY: {},
            },
        },
    }
    ok, errors = validate_mcp_2026_request(
        req,
        headers={
            MCP_PROTOCOL_VERSION_HEADER: MCP_PROTOCOL_VERSION,
            MCP_METHOD_HEADER: "tools/list",
            MCP_NAME_HEADER: "other",
        },
    )
    assert not ok
    assert "header_body_method_mismatch" in errors
    assert "header_body_name_mismatch" in errors


def test_a2a_1_0_card_and_task_use_current_wire_shape():
    card = AgentCard(
        name="agent",
        description="demo",
        supported_interfaces=[AgentInterface("https://example.invalid/a2a", "JSONRPC")],
        version="1.0.0",
        default_input_modes=["text/plain"],
        default_output_modes=["text/plain"],
        skills=[AgentSkill("s1", "search", "Search evidence", ["research"])],
        capabilities={},
    ).to_wire()
    task = A2ATask("t1", "c1", "TASK_STATE_WORKING").to_wire()
    ok, errors = validate_a2a_1_0(card, task)
    assert ok and errors == []
    assert "supportedInterfaces" in card and "endpoint" not in card
    assert task["status"]["state"] == "TASK_STATE_WORKING" and "state" not in task


def test_a2a_old_flat_task_state_is_rejected():
    card = AgentCard(
        name="agent",
        description="demo",
        supported_interfaces=[AgentInterface("https://example.invalid/a2a", "JSONRPC")],
        version="1.0.0",
        default_input_modes=["text/plain"],
        default_output_modes=["text/plain"],
        skills=[AgentSkill("s1", "search", "Search evidence")],
        capabilities={},
    ).to_wire()
    ok, errors = validate_a2a_1_0(card, {"id": "t1", "contextId": "c1", "state": "working"})
    assert not ok and "task_state_invalid" in errors
