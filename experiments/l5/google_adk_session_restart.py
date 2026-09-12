from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from google.adk.events import Event, EventActions
from google.adk.sessions import DatabaseSessionService
from google.genai import types


EXPERIMENT = "google-adk-session-restart"
APP = "procurement_control"
USER = "reviewer-17"


def content(text: str) -> types.Content:
    return types.Content(role="model", parts=[types.Part(text=text)])


def event_view(event: Event) -> dict[str, Any]:
    return {
        "id": event.id,
        "invocation_id": event.invocation_id,
        "author": event.author,
        "text": event.content.parts[0].text if event.content and event.content.parts else None,
        "state_delta": dict(event.actions.state_delta),
        "error_code": event.error_code,
    }


async def phase(root: Path, scenario: str, phase_name: str) -> dict[str, Any]:
    scenario_root = root / scenario
    scenario_root.mkdir(parents=True, exist_ok=True)
    db_path = (scenario_root / "sessions.sqlite").absolute()
    session_id = f"session-{scenario}"
    service = DatabaseSessionService(db_url=f"sqlite+aiosqlite:///{db_path}")
    try:
        if phase_name == "persist":
            session = await service.create_session(
                app_name=APP,
                user_id=USER,
                session_id=session_id,
                state={"stage": "received", "pending_action_id": f"purchase-{scenario}"},
            )
            planned = Event(
                id=f"event-{scenario}-planned",
                invocation_id=f"invocation-{scenario}",
                author="procurement_planner",
                content=content("Validated vendor and prepared an approval-bound purchase intent."),
                actions=EventActions(state_delta={"stage": "awaiting_approval", "risk_tier": "high"}),
            )
            await service.append_event(session, planned)
            return {
                "phase": phase_name,
                "pid": os.getpid(),
                "session_id": session.id,
                "state": dict(session.state),
                "events": [event_view(item) for item in session.events],
            }

        session = await service.get_session(app_name=APP, user_id=USER, session_id=session_id)
        if session is None:
            raise RuntimeError("persisted session not found")
        if scenario == "approve":
            artifact = scenario_root / "purchase_receipt.json"
            artifact.write_text(
                json.dumps({"action_id": "purchase-approve", "status": "authorized"}, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            terminal = Event(
                id="event-approve-completed",
                invocation_id="invocation-approve-resume",
                author="approval_executor",
                content=content("Approval identity matched; the purchase receipt was committed."),
                actions=EventActions(state_delta={"stage": "completed", "decision": "approved"}),
            )
        else:
            terminal = Event(
                id="event-reject-denied",
                invocation_id="invocation-reject-resume",
                author="approval_executor",
                content=content("Policy denied the purchase; no receipt was committed."),
                error_code="POLICY_DENIED",
                error_message="approval rejected",
                actions=EventActions(state_delta={"stage": "denied", "decision": "rejected"}),
            )
        await service.append_event(session, terminal)
        reloaded = await service.get_session(app_name=APP, user_id=USER, session_id=session_id)
        assert reloaded is not None
        return {
            "phase": phase_name,
            "pid": os.getpid(),
            "session_id": reloaded.id,
            "state": dict(reloaded.state),
            "events": [event_view(item) for item in reloaded.events],
            "artifact_exists": (scenario_root / "purchase_receipt.json").exists(),
        }
    finally:
        await service.close()


def run_phase(root: Path, scenario: str, phase_name: str) -> int:
    print(json.dumps(asyncio.run(phase(root, scenario, phase_name)), sort_keys=True))
    return 0


def execute_phase(root: Path, scenario: str, phase_name: str) -> dict[str, Any]:
    proc = subprocess.run(
        [sys.executable, __file__, str(root), "--scenario", scenario, "--phase", phase_name],
        text=True,
        capture_output=True,
        timeout=90,
    )
    if proc.returncode:
        raise RuntimeError(f"{scenario}/{phase_name} failed: {proc.stderr}")
    return {
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "result": json.loads(proc.stdout),
    }


def orchestrate(root: Path) -> int:
    records: dict[str, Any] = {}
    for scenario in ("approve", "reject"):
        records[scenario] = {
            "persist": execute_phase(root, scenario, "persist"),
            "resume": execute_phase(root, scenario, "resume"),
        }

    approve = records["approve"]
    reject = records["reject"]
    assertions = {
        "persist_and_resume_are_distinct_processes": all(
            records[s]["persist"]["result"]["pid"] != records[s]["resume"]["result"]["pid"] for s in records
        ),
        "session_identity_survives_restart": all(
            records[s]["persist"]["result"]["session_id"] == records[s]["resume"]["result"]["session_id"]
            for s in records
        ),
        "planned_event_survives_restart": all(
            records[s]["resume"]["result"]["events"][0]["id"] == f"event-{s}-planned" for s in records
        ),
        "state_delta_is_materialized": approve["resume"]["result"]["state"]["stage"] == "completed"
        and reject["resume"]["result"]["state"]["stage"] == "denied",
        "approve_artifact_exists": approve["resume"]["result"]["artifact_exists"] is True,
        "reject_artifact_absent": reject["resume"]["result"]["artifact_exists"] is False,
        "failure_is_explicit_event": reject["resume"]["result"]["events"][-1]["error_code"] == "POLICY_DENIED",
        "two_event_trajectory_persisted": all(len(records[s]["resume"]["result"]["events"]) == 2 for s in records),
        "sqlite_database_persisted": all((root / s / "sessions.sqlite").stat().st_size > 0 for s in records),
    }
    observations = {"processes": records}
    wire = {
        scenario: {
            "session_id": records[scenario]["resume"]["result"]["session_id"],
            "event_ids": [event["id"] for event in records[scenario]["resume"]["result"]["events"]],
            "state": records[scenario]["resume"]["result"]["state"],
        }
        for scenario in records
    }
    verifier = {"experiment": EXPERIMENT, "assertions": assertions, "all_passed": all(assertions.values())}
    (root / "observations.json").write_text(json.dumps(observations, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (root / "wire.json").write_text(json.dumps(wire, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (root / "verifier.json").write_text(json.dumps(verifier, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(verifier, sort_keys=True))
    return 0 if verifier["all_passed"] else 2


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    parser.add_argument("--scenario", choices=("approve", "reject"))
    parser.add_argument("--phase", choices=("persist", "resume"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if bool(args.scenario) != bool(args.phase):
        raise SystemExit("--scenario and --phase must be provided together")
    return run_phase(args.output, args.scenario, args.phase) if args.phase else orchestrate(args.output)


if __name__ == "__main__":
    raise SystemExit(main())
