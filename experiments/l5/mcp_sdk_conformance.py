from __future__ import annotations

import asyncio
import contextlib
import importlib.metadata
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from mcp import Client
from mcp.server.mcpserver import MCPServer
from mcp.shared.inbound import (
    MCP_METHOD_HEADER,
    MCP_NAME_HEADER,
    MCP_PROTOCOL_VERSION_HEADER,
    InboundLadderRejection,
    InboundModernRoute,
    classify_inbound_request,
)
from mcp_types import (
    CLIENT_CAPABILITIES_META_KEY,
    CLIENT_INFO_META_KEY,
    PROTOCOL_VERSION_META_KEY,
    Implementation,
)
from mcp_types.jsonrpc import HEADER_MISMATCH


PROTOCOL_VERSION = "2026-07-28"


def _jsonable(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json", by_alias=True)
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    return repr(value)


def serve(port: int, effect_path: Path) -> int:
    server = MCPServer("agentlab-l5", version="1.0.0")

    @server.tool(structured_output=False)
    def price_purchase_order(quantity: int, unit_price_cents: int, tax_bps: int) -> int:
        subtotal = quantity * unit_price_cents
        total = subtotal + subtotal * tax_bps // 10_000
        effect_path.write_text(
            json.dumps(
                {
                    "quantity": quantity,
                    "unit_price_cents": unit_price_cents,
                    "tax_bps": tax_bps,
                    "total_cents": total,
                    "server_pid": os.getpid(),
                },
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        return total

    server.run(
        "streamable-http",
        host="127.0.0.1",
        port=port,
        streamable_http_path="/mcp",
        stateless_http=True,
        json_response=True,
    )
    return 0


def free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def wait_for_port(port: int, process: subprocess.Popen[str]) -> None:
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        if process.poll() is not None:
            stdout, stderr = process.communicate()
            raise RuntimeError(f"MCP server exited early: stdout={stdout!r} stderr={stderr!r}")
        with contextlib.suppress(OSError):
            with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                return
        time.sleep(0.05)
    raise TimeoutError("MCP server did not become reachable")


async def exercise(output: Path) -> tuple[dict[str, Any], dict[str, bool]]:
    effect_path = output / "server-effect.json"
    port = free_port()
    server_process = subprocess.Popen(
        [sys.executable, __file__, str(output), "--server", str(port), str(effect_path)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        wait_for_port(port, server_process)
        async with Client(
            f"http://127.0.0.1:{port}/mcp",
            mode=PROTOCOL_VERSION,
            client_info=Implementation(name="agentlab-l5", version="1.0.0"),
        ) as client:
            result = await client.call_tool(
                "price_purchase_order",
                {"quantity": 12, "unit_price_cents": 2599, "tax_bps": 825},
            )
            negotiated = client.session.protocol_version
    finally:
        server_process.terminate()
        try:
            server_stdout, server_stderr = server_process.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            server_process.kill()
            server_stdout, server_stderr = server_process.communicate(timeout=5)

    effect = json.loads(effect_path.read_text(encoding="utf-8"))

    body = {
        "jsonrpc": "2.0",
        "id": "mcp-l5-1",
        "method": "tools/call",
        "params": {
            "name": "price_purchase_order",
            "arguments": {"quantity": 12, "unit_price_cents": 2599, "tax_bps": 825},
            "_meta": {
                PROTOCOL_VERSION_META_KEY: PROTOCOL_VERSION,
                CLIENT_CAPABILITIES_META_KEY: {},
                CLIENT_INFO_META_KEY: {"name": "agentlab-l5", "version": "1.0.0"},
            },
        },
    }
    headers = {
        MCP_PROTOCOL_VERSION_HEADER: PROTOCOL_VERSION,
        MCP_METHOD_HEADER: "tools/call",
        MCP_NAME_HEADER: "price_purchase_order",
    }
    valid_route = classify_inbound_request(body, headers=headers)
    bad_headers = dict(headers)
    bad_headers[MCP_PROTOCOL_VERSION_HEADER] = "2025-11-25"
    rejected_route = classify_inbound_request(body, headers=bad_headers)

    result_dump = _jsonable(result)
    observations = {
        "packages": {
            "mcp": importlib.metadata.version("mcp"),
            "mcp-types": importlib.metadata.version("mcp-types"),
        },
        "negotiated_protocol": negotiated,
        "tool_result": result_dump,
        "server_effect": effect,
        "client_pid": os.getpid(),
        "server_process": {
            "pid": server_process.pid,
            "returncode_after_termination": server_process.returncode,
            "stdout": server_stdout,
            "stderr": server_stderr,
        },
        "modern_route": _jsonable(valid_route),
        "rejection": _jsonable(rejected_route),
        "wire": {"request": body, "headers": headers, "fault_headers": bad_headers},
    }
    assertions = {
        "official_packages_exact": observations["packages"] == {"mcp": "2.2.0", "mcp-types": "2.2.0"},
        "modern_protocol_negotiated": negotiated == PROTOCOL_VERSION,
        "client_and_server_are_distinct_processes": os.getpid() != server_process.pid,
        "streamable_http_effect_matches_request": effect["quantity"] == 12
        and effect["unit_price_cents"] == 2599
        and effect["tax_bps"] == 825
        and effect["total_cents"] == 33761,
        "effect_executed_by_server_process": effect["server_pid"] == server_process.pid,
        "valid_request_classified_modern": isinstance(valid_route, InboundModernRoute),
        "header_body_mismatch_rejected": isinstance(rejected_route, InboundLadderRejection),
        "header_mismatch_error_code": isinstance(rejected_route, InboundLadderRejection)
        and rejected_route.code == HEADER_MISMATCH,
        "meta_is_nested_under_params": "_meta" in body["params"] and "_meta" not in body,
        "routing_headers_present": all(
            k in headers for k in (MCP_PROTOCOL_VERSION_HEADER, MCP_METHOD_HEADER, MCP_NAME_HEADER)
        ),
    }
    return observations, assertions


def main() -> int:
    if len(sys.argv) == 5 and sys.argv[2] == "--server":
        return serve(int(sys.argv[3]), Path(sys.argv[4]))
    if len(sys.argv) != 2:
        raise SystemExit("usage: mcp_sdk_conformance.py OUTPUT_DIR [--server PORT EFFECT_PATH]")
    output = Path(sys.argv[1])
    output.mkdir(parents=True, exist_ok=True)
    observations, assertions = asyncio.run(exercise(output))
    (output / "observations.json").write_text(
        json.dumps(observations, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output / "wire.json").write_text(
        json.dumps(observations["wire"], ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    verifier = {
        "schema_version": 1,
        "experiment": "mcp-sdk-conformance",
        "assertions": assertions,
        "all_passed": all(assertions.values()),
        "claim_scope": "official_sdk_conformance",
    }
    (output / "verifier.json").write_text(
        json.dumps(verifier, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(verifier, sort_keys=True))
    return 0 if verifier["all_passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
