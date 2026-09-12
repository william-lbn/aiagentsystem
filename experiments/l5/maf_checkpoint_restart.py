from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Never

from agent_framework import FileCheckpointStorage, WorkflowBuilder, WorkflowContext, executor


EXPERIMENT = "maf-checkpoint-restart"
WORKFLOW_NAME = "change-control-v1"


def build_workflow(root: Path, *, topology: str = "canonical"):
    storage = FileCheckpointStorage(root / "checkpoints")
    effect_path = root / "deployment-effects.jsonl"

    @executor(id="validate_change", input=str, output=str)
    async def validate_change(change: str, ctx: WorkflowContext[str]) -> None:
        request = json.loads(change)
        if request["risk"] != "high" or not request["change_id"]:
            raise ValueError("invalid change request")
        await ctx.send_message(json.dumps({**request, "validated": True}, sort_keys=True))

    apply_id = "apply_change" if topology == "canonical" else "apply_change_v2"

    @executor(id=apply_id, input=str, workflow_output=str)
    async def apply_change(validated: str, ctx: WorkflowContext[Never, str]) -> None:
        request = json.loads(validated)
        record = {
            "change_id": request["change_id"],
            "release": request["release"],
            "applied_by_pid": os.getpid(),
        }
        with effect_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
        await ctx.yield_output(json.dumps({**record, "status": "applied"}, sort_keys=True))

    return (
        WorkflowBuilder(
            name=WORKFLOW_NAME,
            start_executor=validate_change,
            checkpoint_storage=storage,
            output_from=[apply_change],
        )
        .add_edge(validate_change, apply_change)
        .build()
    ), storage


async def persist_phase(root: Path) -> dict[str, object]:
    workflow, storage = build_workflow(root)
    request = json.dumps(
        {"change_id": "chg-2026-0911-017", "release": "agent-runtime-13.1", "risk": "high"},
        sort_keys=True,
    )
    stream = workflow.run(request, stream=True)
    async for event in stream:
        if event.type == "superstep_completed" and event.iteration == 1:
            checkpoint = await storage.get_latest(workflow_name=WORKFLOW_NAME)
            if checkpoint is None:
                raise RuntimeError("superstep completed without a persisted checkpoint")
            phase_record = {
                "phase": "persist",
                "pid": os.getpid(),
                "checkpoint_id": checkpoint.checkpoint_id,
                "iteration": checkpoint.iteration_count,
                "graph_signature_hash": checkpoint.graph_signature_hash,
            }
            (root / "persist-phase.json").write_text(
                json.dumps(phase_record, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            print(json.dumps(phase_record, sort_keys=True), flush=True)
            # A hard process exit models loss of in-memory runner state immediately
            # after the durable superstep boundary. The orchestrator continues in a
            # fresh process and can only use the file checkpoint.
            os._exit(0)
    raise RuntimeError("workflow converged before the first superstep checkpoint")


async def resume_phase(root: Path) -> dict[str, object]:
    phase_record = json.loads((root / "persist-phase.json").read_text(encoding="utf-8"))
    checkpoint_id = phase_record["checkpoint_id"]

    mismatch_rejected = False
    mismatch_error = ""
    mismatched, _ = build_workflow(root, topology="changed")
    try:
        await mismatched.run(checkpoint_id=checkpoint_id)
    except Exception as exc:  # exact public exception type is not part of this proof
        mismatch_rejected = True
        mismatch_error = f"{type(exc).__name__}: {exc}"

    canonical, storage = build_workflow(root)
    restored = await storage.load(checkpoint_id)
    result = await canonical.run(checkpoint_id=checkpoint_id)
    outputs = result.get_outputs()
    return {
        "phase": "resume",
        "pid": os.getpid(),
        "checkpoint_id": checkpoint_id,
        "restored_iteration": restored.iteration_count,
        "restored_graph_signature_hash": restored.graph_signature_hash,
        "mismatch_rejected": mismatch_rejected,
        "mismatch_error": mismatch_error,
        "final_state": result.get_final_state().value,
        "outputs": outputs,
    }


def execute_phase(root: Path, phase: str) -> dict[str, object]:
    proc = subprocess.run(
        [sys.executable, __file__, str(root), "--phase", phase],
        text=True,
        capture_output=True,
        timeout=90,
    )
    if proc.returncode:
        raise RuntimeError(f"{phase} failed: stdout={proc.stdout!r} stderr={proc.stderr!r}")
    return {
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "result": json.loads(proc.stdout),
    }


def orchestrate(root: Path) -> int:
    root.mkdir(parents=True, exist_ok=True)
    persist = execute_phase(root, "persist")
    resume = execute_phase(root, "resume")
    effect_path = root / "deployment-effects.jsonl"
    effects = [json.loads(line) for line in effect_path.read_text(encoding="utf-8").splitlines()]
    checkpoint_files = sorted((root / "checkpoints").glob("*.json"))

    assertions = {
        "persist_and_resume_are_distinct_processes": persist["result"]["pid"] != resume["result"]["pid"],
        "checkpoint_identity_survives_restart": persist["result"]["checkpoint_id"] == resume["result"]["checkpoint_id"],
        "graph_signature_survives_restart": persist["result"]["graph_signature_hash"]
        == resume["result"]["restored_graph_signature_hash"],
        "changed_topology_is_rejected": resume["result"]["mismatch_rejected"] is True
        and "graph has changed" in resume["result"]["mismatch_error"],
        "canonical_topology_reaches_idle": resume["result"]["final_state"] == "IDLE",
        "business_effect_is_applied_once": len(effects) == 1 and effects[0]["change_id"] == "chg-2026-0911-017",
        "effect_runs_only_in_resume_process": effects[0]["applied_by_pid"] == resume["result"]["pid"],
        "terminal_output_matches_effect": len(resume["result"]["outputs"]) == 1
        and json.loads(resume["result"]["outputs"][0])["change_id"] == effects[0]["change_id"],
        "file_checkpoint_artifacts_exist": len(checkpoint_files) >= 2
        and all(path.stat().st_size > 0 for path in checkpoint_files),
    }
    observations = {
        "processes": {"persist": persist, "resume": resume},
        "effects": effects,
        "checkpoint_files": [path.name for path in checkpoint_files],
        "note": "The first process hard-exits after the first durable superstep. A new process rejects a changed graph and resumes the canonical graph from FileCheckpointStorage.",
    }
    wire = {
        "input": {"change_id": "chg-2026-0911-017", "release": "agent-runtime-13.1", "risk": "high"},
        "checkpoint_id": persist["result"]["checkpoint_id"],
        "output": json.loads(resume["result"]["outputs"][0]),
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
    parser.add_argument("--phase", choices=("persist", "resume"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.phase == "persist":
        return asyncio.run(persist_phase(args.output))  # pragma: no cover - os._exit terminates
    if args.phase == "resume":
        print(json.dumps(asyncio.run(resume_phase(args.output)), sort_keys=True))
        return 0
    return orchestrate(args.output)


if __name__ == "__main__":
    raise SystemExit(main())
