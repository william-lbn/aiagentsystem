"""Small protocol-conformance helpers used by deterministic Core Labs.

These types intentionally model only the fields exercised by this course. They
are aligned to the normative MCP 2026-07-28 and A2A 1.0 wire contracts, but are
*not* replacements for the official SDKs.  Official-SDK interoperability lives
in ``labs/upstream`` and is separately evidenced.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

MCP_PROTOCOL_VERSION = "2026-07-28"
MCP_PROTOCOL_VERSION_META_KEY = "io.modelcontextprotocol/protocolVersion"
MCP_CLIENT_INFO_META_KEY = "io.modelcontextprotocol/clientInfo"
MCP_CLIENT_CAPABILITIES_META_KEY = "io.modelcontextprotocol/clientCapabilities"
MCP_PROTOCOL_VERSION_HEADER = "mcp-protocol-version"
MCP_METHOD_HEADER = "mcp-method"
MCP_NAME_HEADER = "mcp-name"

MCP_NAME_BEARING_METHODS = {
    "tools/call": "name",
    "prompts/get": "name",
    "resources/read": "uri",
}

A2A_PROTOCOL_VERSION = "1.0"
A2A_TASK_STATES = {
    "TASK_STATE_UNSPECIFIED",
    "TASK_STATE_SUBMITTED",
    "TASK_STATE_WORKING",
    "TASK_STATE_COMPLETED",
    "TASK_STATE_FAILED",
    "TASK_STATE_CANCELED",
    "TASK_STATE_INPUT_REQUIRED",
    "TASK_STATE_REJECTED",
    "TASK_STATE_AUTH_REQUIRED",
}


@dataclass(slots=True)
class MCPTool:
    name: str
    description: str
    input_schema: dict[str, Any]


def validate_mcp_2026_request(
    request: dict[str, Any], *, headers: dict[str, str] | None = None
) -> tuple[bool, list[str]]:
    """Validate the modern MCP request subset exercised by this course.

    The normative 2026-07-28 schema requires protocolVersion and per-request
    clientCapabilities inside ``params._meta``. For Streamable HTTP, routing
    headers must mirror the body. Header names are case-insensitive; this helper
    normalizes them before comparison.

    This is deliberately not a full protocol implementation. In particular it
    omits the complete header-value codec and method registry; official-SDK
    conformance is exercised separately under ``experiments/l5``.
    """
    errors: list[str] = []
    if request.get("jsonrpc") != "2.0":
        errors.append("invalid_jsonrpc_version")
    if "id" not in request:
        errors.append("missing_request_id")
    method = request.get("method")
    if not isinstance(method, str) or not method:
        errors.append("invalid_method")
    params = request.get("params")
    if not isinstance(params, dict):
        return False, errors + ["missing_or_invalid_params"]
    meta = params.get("_meta")
    if not isinstance(meta, dict):
        return False, errors + ["missing_or_invalid_meta"]
    version = meta.get(MCP_PROTOCOL_VERSION_META_KEY)
    if version != MCP_PROTOCOL_VERSION:
        errors.append("invalid_protocol_version_meta")
    caps = meta.get(MCP_CLIENT_CAPABILITIES_META_KEY)
    if not isinstance(caps, dict):
        errors.append("missing_client_capabilities")
    info = meta.get(MCP_CLIENT_INFO_META_KEY)
    if info is not None:
        if (
            not isinstance(info, dict)
            or not isinstance(info.get("name"), str)
            or not isinstance(info.get("version"), str)
        ):
            errors.append("invalid_client_info")
    if headers is not None:
        normalized = {str(k).lower(): v for k, v in headers.items()}
        header_version = normalized.get(MCP_PROTOCOL_VERSION_HEADER)
        if header_version is None:
            errors.append("missing_protocol_version_header")
        elif header_version != version:
            errors.append("header_body_version_mismatch")
        header_method = normalized.get(MCP_METHOD_HEADER)
        if header_method is None:
            errors.append("missing_method_header")
        elif header_method != method:
            errors.append("header_body_method_mismatch")
        name_key = MCP_NAME_BEARING_METHODS.get(method)
        body_name = params.get(name_key) if name_key else None
        if body_name is not None:
            header_name = normalized.get(MCP_NAME_HEADER)
            if header_name is None:
                errors.append("missing_name_header")
            elif header_name != body_name:
                errors.append("header_body_name_mismatch")
    return not errors, errors


@dataclass(slots=True)
class AgentInterface:
    url: str
    protocol_binding: str
    protocol_version: str = A2A_PROTOCOL_VERSION

    def to_wire(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "protocolBinding": self.protocol_binding,
            "protocolVersion": self.protocol_version,
        }


@dataclass(slots=True)
class AgentSkill:
    id: str
    name: str
    description: str
    tags: list[str] = field(default_factory=list)

    def to_wire(self) -> dict[str, Any]:
        return {"id": self.id, "name": self.name, "description": self.description, "tags": self.tags}


@dataclass(slots=True)
class AgentCard:
    name: str
    description: str
    supported_interfaces: list[AgentInterface]
    version: str
    default_input_modes: list[str]
    default_output_modes: list[str]
    skills: list[AgentSkill]
    capabilities: dict[str, Any] = field(default_factory=dict)

    def to_wire(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "supportedInterfaces": [x.to_wire() for x in self.supported_interfaces],
            "version": self.version,
            "capabilities": self.capabilities,
            "defaultInputModes": self.default_input_modes,
            "defaultOutputModes": self.default_output_modes,
            "skills": [x.to_wire() for x in self.skills],
        }


@dataclass(slots=True)
class A2ATask:
    task_id: str
    context_id: str
    state: str = "TASK_STATE_SUBMITTED"
    artifacts: list[dict[str, Any]] = field(default_factory=list)
    history: list[dict[str, Any]] = field(default_factory=list)

    def to_wire(self) -> dict[str, Any]:
        return {
            "id": self.task_id,
            "contextId": self.context_id,
            "status": {"state": self.state},
            "artifacts": self.artifacts,
            "history": self.history,
        }


def validate_a2a_1_0(card: dict[str, Any], task: dict[str, Any]) -> tuple[bool, list[str]]:
    errors: list[str] = []
    for key in (
        "name",
        "description",
        "supportedInterfaces",
        "version",
        "capabilities",
        "defaultInputModes",
        "defaultOutputModes",
        "skills",
    ):
        if key not in card:
            errors.append(f"card_missing_{key}")
    interfaces = card.get("supportedInterfaces")
    if not isinstance(interfaces, list) or not interfaces:
        errors.append("card_interfaces_missing")
    else:
        for i, interface in enumerate(interfaces):
            if not isinstance(interface, dict):
                errors.append(f"interface_{i}_invalid")
                continue
            if not all(
                isinstance(interface.get(k), str) and interface.get(k)
                for k in ("url", "protocolBinding", "protocolVersion")
            ):
                errors.append(f"interface_{i}_required_fields")
    skills = card.get("skills")
    if not isinstance(skills, list) or not skills:
        errors.append("card_skills_missing")
    else:
        for i, skill in enumerate(skills):
            if not isinstance(skill, dict) or not all(
                isinstance(skill.get(k), str) and skill.get(k) for k in ("id", "name", "description")
            ):
                errors.append(f"skill_{i}_invalid")
    if not isinstance(task.get("id"), str) or not isinstance(task.get("contextId"), str):
        errors.append("task_identity_invalid")
    status = task.get("status")
    state = status.get("state") if isinstance(status, dict) else None
    if state not in A2A_TASK_STATES:
        errors.append("task_state_invalid")
    if "artifacts" in task and not isinstance(task.get("artifacts"), list):
        errors.append("task_artifacts_invalid")
    if "history" in task and not isinstance(task.get("history"), list):
        errors.append("task_history_invalid")
    return not errors, errors
