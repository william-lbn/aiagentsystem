from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from agents import Agent, RunState, Runner, function_tool, set_tracing_disabled
from agents.testing import ScriptedModel, assistant_message, function_call


EXPERIMENT = "openai-agents-runstate-restart"
CALL_IDS = {"approve": "call-approve-001", "reject": "call-reject-001"}


def read_effects(path: Path) -> list[dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else []


def make_agent(counter_path: Path, phase: str, scenario: str) -> Agent:
    @function_tool(needs_approval=True)
    def apply_effect(action_id: str) -> str:
        """Apply one externally observable effect for an approved action."""
        effects = read_effects(counter_path)
        effects.append({"action_id": action_id, "applied_by_pid": os.getpid()})
        counter_path.write_text(json.dumps(effects, sort_keys=True) + "\n", encoding="utf-8")
        return f"applied:{action_id}"

    if phase == "pause":
        model = ScriptedModel(
            [[function_call("apply_effect", {"action_id": f"action-{scenario}"}, call_id=CALL_IDS[scenario])]]
        )
    else:
        model = ScriptedModel([[assistant_message(f"terminal:{scenario}")]])
    return Agent(name="durable-approval-agent", model=model, tools=[apply_effect])


def run_phase(root: Path, scenario: str, phase: str) -> int:
    set_tracing_disabled(True)
    scenario_root = root / scenario
    scenario_root.mkdir(parents=True, exist_ok=True)
    counter_path = scenario_root / "side_effect_counter.json"
    state_path = scenario_root / "run_state.json"
    agent = make_agent(counter_path, phase, scenario)

    if phase == "pause":
        result = Runner.run_sync(agent, f"Execute action-{scenario}")
        state = result.to_state()
        state_path.write_text(json.dumps(state.to_json(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
        interruptions = state.get_interruptions()
        output = {
            "phase": phase,
            "pid": os.getpid(),
            "interruptions": [
                {"call_id": item.call_id, "tool_name": item.tool_name, "arguments": item.arguments}
                for item in interruptions
            ],
            "effect_count": len(read_effects(counter_path)),
        }
    else:
        serialized = json.loads(state_path.read_text(encoding="utf-8"))
        restored = asyncio.run(RunState.from_json(agent, serialized))
        interruptions = restored.get_interruptions()
        if len(interruptions) != 1:
            raise RuntimeError(f"expected one restored interruption, got {len(interruptions)}")
        if scenario == "approve":
            restored.approve(interruptions[0])
        else:
            restored.reject(interruptions[0], rejection_message="policy denied")
        result = Runner.run_sync(agent, restored)
        output = {
            "phase": phase,
            "pid": os.getpid(),
            "decision": scenario,
            "restored_call_id": interruptions[0].call_id,
            "restored_tool_name": interruptions[0].tool_name,
            "effect_count": len(read_effects(counter_path)),
            "final_output": result.final_output,
            "remaining_interruptions": len(result.interruptions),
        }
    print(json.dumps(output, sort_keys=True))
    return 0


def execute_phase(root: Path, scenario: str, phase: str) -> dict[str, Any]:
    proc = subprocess.run(
        [sys.executable, __file__, str(root), "--scenario", scenario, "--phase", phase],
        text=True,
        capture_output=True,
        timeout=60,
    )
    if proc.returncode:
        raise RuntimeError(f"{scenario}/{phase} failed: {proc.stderr}")
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
            "pause": execute_phase(root, scenario, "pause"),
            "resume": execute_phase(root, scenario, "resume"),
        }

    approve_effects = read_effects(root / "approve" / "side_effect_counter.json")
    reject_effects = read_effects(root / "reject" / "side_effect_counter.json")
    assertions = {
        "pause_and_resume_are_distinct_processes": all(
            records[s]["pause"]["result"]["pid"] != records[s]["resume"]["result"]["pid"] for s in records
        ),
        "pause_has_exactly_one_interruption": all(
            len(records[s]["pause"]["result"]["interruptions"]) == 1 for s in records
        ),
        "call_identity_survives_serialization": all(
            records[s]["resume"]["result"]["restored_call_id"] == CALL_IDS[s] for s in records
        ),
        "tool_identity_survives_serialization": all(
            records[s]["resume"]["result"]["restored_tool_name"] == "apply_effect" for s in records
        ),
        "unapproved_tool_never_runs": all(records[s]["pause"]["result"]["effect_count"] == 0 for s in records),
        "approved_effect_runs_once": len(approve_effects) == 1,
        "rejected_effect_never_runs": reject_effects == [],
        "resumed_runs_are_terminal": all(
            records[s]["resume"]["result"]["remaining_interruptions"] == 0 for s in records
        ),
    }
    observations = {"processes": records, "approve_effects": approve_effects, "reject_effects": reject_effects}
    wire = {
        scenario: {
            "serialized_state": f"{scenario}/run_state.json",
            "call_id": CALL_IDS[scenario],
            "decision": scenario,
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
    parser.add_argument("--phase", choices=("pause", "resume"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if bool(args.scenario) != bool(args.phase):
        raise SystemExit("--scenario and --phase must be provided together")
    return run_phase(args.output, args.scenario, args.phase) if args.phase else orchestrate(args.output)


if __name__ == "__main__":
    raise SystemExit(main())
