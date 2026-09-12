from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, TypedDict

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt


EXPERIMENT = "langgraph-durable-restart"


class ApprovalState(TypedDict, total=False):
    action_id: str
    outcome: str


def read_counter(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"pre_interrupt_executions": 0, "effects": []}
    return json.loads(path.read_text(encoding="utf-8"))


def write_counter(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")


def build_graph(counter_path: Path, saver: SqliteSaver):
    def approval_node(state: ApprovalState) -> ApprovalState:
        counter = read_counter(counter_path)
        counter["pre_interrupt_executions"] += 1
        write_counter(counter_path, counter)

        decision = interrupt({"action_id": state["action_id"], "kind": "approval"})
        if decision.get("action_id") != state["action_id"]:
            return {"outcome": "identity_mismatch"}
        if not decision.get("approved"):
            return {"outcome": "rejected"}

        counter = read_counter(counter_path)
        counter["effects"].append({"action_id": state["action_id"], "applied_by_pid": os.getpid()})
        write_counter(counter_path, counter)
        return {"outcome": "applied"}

    builder = StateGraph(ApprovalState)
    builder.add_node("approval", approval_node)
    builder.add_edge(START, "approval")
    builder.add_edge("approval", END)
    return builder.compile(checkpointer=saver)


def run_phase(root: Path, scenario: str, phase: str) -> int:
    scenario_root = root / scenario
    scenario_root.mkdir(parents=True, exist_ok=True)
    db_path = scenario_root / "checkpoints.sqlite"
    counter_path = scenario_root / "side_effect_counter.json"
    action_id = f"action-{scenario}"
    config = {"configurable": {"thread_id": f"thread-{scenario}"}}

    with SqliteSaver.from_conn_string(str(db_path)) as saver:
        graph = build_graph(counter_path, saver)
        if phase == "pause":
            result = graph.invoke({"action_id": action_id}, config=config)
            interruptions = result.get("__interrupt__", ())
            payload = interruptions[0].value if interruptions else None
            output = {"phase": phase, "pid": os.getpid(), "interrupted": bool(interruptions), "payload": payload}
        else:
            approved = scenario == "approve"
            result = graph.invoke(
                Command(resume={"action_id": action_id, "approved": approved}),
                config=config,
            )
            output = {
                "phase": phase,
                "pid": os.getpid(),
                "approved": approved,
                "outcome": result.get("outcome"),
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
    phase_records: dict[str, Any] = {}
    for scenario in ("approve", "reject"):
        phase_records[scenario] = {
            "pause": execute_phase(root, scenario, "pause"),
            "resume": execute_phase(root, scenario, "resume"),
        }

    approve_counter = read_counter(root / "approve" / "side_effect_counter.json")
    reject_counter = read_counter(root / "reject" / "side_effect_counter.json")
    assertions = {
        "pause_and_resume_are_distinct_processes": all(
            phase_records[s]["pause"]["result"]["pid"] != phase_records[s]["resume"]["result"]["pid"]
            for s in phase_records
        ),
        "both_runs_reached_official_interrupt": all(
            phase_records[s]["pause"]["result"]["interrupted"] for s in phase_records
        ),
        "approval_identity_survived_checkpoint": phase_records["approve"]["pause"]["result"]["payload"]
        == {"action_id": "action-approve", "kind": "approval"},
        "approved_effect_applied_once": len(approve_counter["effects"]) == 1,
        "rejected_effect_not_applied": reject_counter["effects"] == [],
        "resume_replays_node_prefix": approve_counter["pre_interrupt_executions"] == 2
        and reject_counter["pre_interrupt_executions"] == 2,
        "terminal_outcomes_are_explicit": phase_records["approve"]["resume"]["result"]["outcome"] == "applied"
        and phase_records["reject"]["resume"]["result"]["outcome"] == "rejected",
        "sqlite_checkpoints_persisted": all(
            (root / s / "checkpoints.sqlite").stat().st_size > 0 for s in phase_records
        ),
    }
    observations = {
        "processes": phase_records,
        "approve_counter": approve_counter,
        "reject_counter": reject_counter,
        "note": "The node prefix executes again on resume; effects before interrupt therefore require idempotency.",
    }
    wire = {
        "approve_interrupt": phase_records["approve"]["pause"]["result"]["payload"],
        "approve_resume": {"action_id": "action-approve", "approved": True},
        "reject_interrupt": phase_records["reject"]["pause"]["result"]["payload"],
        "reject_resume": {"action_id": "action-reject", "approved": False},
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
