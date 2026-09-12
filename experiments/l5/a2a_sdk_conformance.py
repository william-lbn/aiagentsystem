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

import uvicorn
from google.protobuf.json_format import MessageToDict, ParseDict, ParseError
from starlette.applications import Starlette

from a2a.client import ClientConfig, create_client
from a2a.helpers import new_text_message
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import create_agent_card_routes, create_jsonrpc_routes
from a2a.server.tasks import InMemoryTaskStore, TaskUpdater
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentInterface,
    AgentSkill,
    Part,
    Role,
    SendMessageRequest,
    Task,
    TaskState,
    TaskStatus,
)


PROTOCOL_VERSION = "1.0"


def agent_card(port: int) -> AgentCard:
    return AgentCard(
        name="agentlab-procurement-risk",
        description="Deterministic procurement policy review agent",
        supported_interfaces=[
            AgentInterface(
                url=f"http://127.0.0.1:{port}/a2a/jsonrpc",
                protocol_binding="JSONRPC",
                protocol_version=PROTOCOL_VERSION,
            )
        ],
        version="1.0.0",
        capabilities=AgentCapabilities(streaming=True),
        default_input_modes=["application/json"],
        default_output_modes=["application/json"],
        skills=[
            AgentSkill(
                id="procurement-risk-review",
                name="Procurement risk review",
                description="Evaluate a purchase order against amount and vendor-risk policy",
                tags=["procurement", "risk", "policy"],
                input_modes=["application/json"],
                output_modes=["application/json"],
            )
        ],
    )


class ProcurementRiskExecutor(AgentExecutor):
    def __init__(self, effect_path: Path) -> None:
        self.effect_path = effect_path

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        if not context.task_id or not context.context_id:
            return
        updater = TaskUpdater(event_queue, context.task_id, context.context_id)
        await updater.cancel()

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        message = context.message
        task_id = context.task_id
        context_id = context.context_id
        if message is None or not task_id or not context_id:
            raise ValueError("A2A request must carry message, task_id, and context_id")

        request = json.loads(context.get_user_input())
        amount_cents = int(request["amount_cents"])
        vendor_risk_bps = int(request["vendor_risk_bps"])
        decision = {
            "purchase_order_id": str(request["purchase_order_id"]),
            "approved": amount_cents <= 5_000_000 and vendor_risk_bps <= 3_500,
            "policy": {
                "max_amount_cents": 5_000_000,
                "max_vendor_risk_bps": 3_500,
            },
            "reason_codes": [],
        }
        if amount_cents > decision["policy"]["max_amount_cents"]:
            decision["reason_codes"].append("AMOUNT_LIMIT_EXCEEDED")
        if vendor_risk_bps > decision["policy"]["max_vendor_risk_bps"]:
            decision["reason_codes"].append("VENDOR_RISK_LIMIT_EXCEEDED")

        self.effect_path.write_text(
            json.dumps(
                {
                    "server_pid": os.getpid(),
                    "task_id": task_id,
                    "context_id": context_id,
                    "request": request,
                    "decision": decision,
                },
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

        await event_queue.enqueue_event(
            Task(
                id=task_id,
                context_id=context_id,
                status=TaskStatus(state=TaskState.TASK_STATE_SUBMITTED),
                history=[message],
            )
        )
        updater = TaskUpdater(event_queue, task_id, context_id)
        await updater.start_work()
        await updater.add_artifact(
            parts=[Part(text=json.dumps(decision, sort_keys=True))],
            artifact_id="risk-decision-v1",
            name="procurement-risk-decision",
            last_chunk=True,
        )
        await updater.complete()


def serve(port: int, effect_path: Path) -> int:
    card = agent_card(port)
    handler = DefaultRequestHandler(
        agent_executor=ProcurementRiskExecutor(effect_path),
        task_store=InMemoryTaskStore(),
        agent_card=card,
    )
    app = Starlette(
        routes=[
            *create_agent_card_routes(agent_card=card),
            *create_jsonrpc_routes(request_handler=handler, rpc_url="/a2a/jsonrpc"),
        ]
    )
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")
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
            raise RuntimeError(f"A2A server exited early: stdout={stdout!r} stderr={stderr!r}")
        with contextlib.suppress(OSError):
            with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                return
        time.sleep(0.05)
    raise TimeoutError("A2A server did not become reachable")


async def exercise(output: Path) -> tuple[dict[str, Any], dict[str, bool]]:
    effect_path = output / "server-effect.json"
    port = free_port()
    process = subprocess.Popen(
        [sys.executable, __file__, str(output), "--server", str(port), str(effect_path)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    request_payload = {
        "purchase_order_id": "PO-2026-0911-017",
        "amount_cents": 4_500_000,
        "vendor_risk_bps": 2_100,
    }
    try:
        wait_for_port(port, process)
        client = await create_client(
            f"http://127.0.0.1:{port}",
            ClientConfig(
                streaming=True,
                supported_protocol_bindings=["JSONRPC"],
                accepted_output_modes=["application/json"],
            ),
        )
        message = new_text_message(
            json.dumps(request_payload, sort_keys=True),
            media_type="application/json",
            context_id="procurement-context-017",
            role=Role.ROLE_USER,
        )
        events: list[dict[str, Any]] = []
        async with client:
            async for event in client.send_message(SendMessageRequest(message=message)):
                events.append(MessageToDict(event, preserving_proto_field_name=False))
    finally:
        process.terminate()
        try:
            server_stdout, server_stderr = process.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            server_stdout, server_stderr = process.communicate(timeout=5)

    effect = json.loads(effect_path.read_text(encoding="utf-8"))
    card = agent_card(port)
    card_wire = MessageToDict(card, preserving_proto_field_name=False)
    round_trip_card = MessageToDict(ParseDict(card_wire, AgentCard()), preserving_proto_field_name=False)
    legacy_card = dict(card_wire)
    legacy_card["url"] = legacy_card["supportedInterfaces"][0]["url"]
    legacy_card["protocolVersion"] = "0.3"
    legacy_card.pop("supportedInterfaces")
    legacy_error = None
    try:
        ParseDict(legacy_card, AgentCard(), ignore_unknown_fields=False)
    except ParseError as exc:
        legacy_error = str(exc)

    payload_kinds = [next(iter(event)) for event in events]
    status_states = [event["statusUpdate"]["status"]["state"] for event in events if "statusUpdate" in event]
    artifact_events = [event["artifactUpdate"] for event in events if "artifactUpdate" in event]
    artifact_decision = json.loads(artifact_events[0]["artifact"]["parts"][0]["text"])
    streamed_task_id = events[0]["task"]["id"]
    descriptor_fields = sorted(field.name for field in AgentCard.DESCRIPTOR.fields)
    observations = {
        "packages": {"a2a-sdk": importlib.metadata.version("a2a-sdk")},
        "agent_card": card_wire,
        "request": request_payload,
        "events": events,
        "payload_kinds": payload_kinds,
        "status_states": status_states,
        "artifact_decision": artifact_decision,
        "server_effect": effect,
        "client_pid": os.getpid(),
        "server_process": {
            "pid": process.pid,
            "returncode_after_termination": process.returncode,
            "stdout": server_stdout,
            "stderr": server_stderr,
        },
        "agent_card_descriptor_fields": descriptor_fields,
        "legacy_card": legacy_card,
        "legacy_rejection": legacy_error,
    }
    assertions = {
        "official_package_exact": observations["packages"] == {"a2a-sdk": "1.1.2"},
        "agent_card_discovered_and_round_trips": round_trip_card == card_wire,
        "client_and_server_are_distinct_processes": os.getpid() != process.pid,
        "effect_executed_by_server_process": effect["server_pid"] == process.pid,
        "request_identity_reaches_server": effect["request"] == request_payload
        and effect["task_id"] == streamed_task_id
        and effect["context_id"] == "procurement-context-017"
        and all(
            event.get("statusUpdate", event.get("artifactUpdate", {})).get("taskId", streamed_task_id)
            == streamed_task_id
            for event in events
        ),
        "task_lifecycle_streamed": payload_kinds == ["task", "statusUpdate", "artifactUpdate", "statusUpdate"]
        and status_states == ["TASK_STATE_WORKING", "TASK_STATE_COMPLETED"],
        "artifact_matches_server_effect": artifact_decision == effect["decision"]
        and artifact_decision["approved"] is True,
        "supported_interfaces_on_wire": card_wire["supportedInterfaces"][0]["protocolBinding"] == "JSONRPC"
        and card_wire["supportedInterfaces"][0]["protocolVersion"] == PROTOCOL_VERSION,
        "no_legacy_top_level_url": "url" not in card_wire and "protocolVersion" not in card_wire,
        "legacy_shape_rejected": legacy_error is not None,
        "descriptor_uses_v1_shape": "supported_interfaces" in descriptor_fields and "url" not in descriptor_fields,
    }
    return observations, assertions


def main() -> int:
    if len(sys.argv) == 5 and sys.argv[2] == "--server":
        return serve(int(sys.argv[3]), Path(sys.argv[4]))
    if len(sys.argv) != 2:
        raise SystemExit("usage: a2a_sdk_conformance.py OUTPUT_DIR [--server PORT EFFECT_PATH]")
    output = Path(sys.argv[1])
    output.mkdir(parents=True, exist_ok=True)
    observations, assertions = asyncio.run(exercise(output))
    (output / "observations.json").write_text(
        json.dumps(observations, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output / "wire.json").write_text(
        json.dumps(
            {"agentCard": observations["agent_card"], "events": observations["events"]},
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    verifier = {
        "schema_version": 1,
        "experiment": "a2a-sdk-conformance",
        "assertions": assertions,
        "all_passed": all(assertions.values()),
        "claim_scope": "official_sdk_jsonrpc_interoperability",
    }
    (output / "verifier.json").write_text(
        json.dumps(verifier, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(verifier, sort_keys=True))
    return 0 if verifier["all_passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
