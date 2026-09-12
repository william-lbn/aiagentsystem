from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import platform
import shutil
import subprocess
from pathlib import Path
from typing import Any

from common import ROOT


CATALOG = ROOT / "experiments/benchmarks/catalog.json"
DEFAULT_OUTPUT = ROOT / "validation_logs/external-benchmark-preflight.json"
MIN_SWEBENCH_FREE_BYTES = 120 * 1024**3


def docker_probe() -> dict[str, Any]:
    executable = shutil.which("docker")
    if executable is None:
        return {"cli_present": False, "daemon_reachable": False, "error": "docker CLI not found"}
    proc = subprocess.run(
        [executable, "info", "--format", "{{json .ServerVersion}}"],
        text=True,
        capture_output=True,
        timeout=20,
    )
    raw_version = proc.stdout.strip()
    try:
        server_version = json.loads(raw_version) if raw_version else None
    except json.JSONDecodeError:
        server_version = None
    reachable = proc.returncode == 0 and bool(server_version) and not proc.stderr.strip()
    return {
        "cli_present": True,
        "daemon_reachable": reachable,
        "server_version": server_version if reachable else None,
        "error": proc.stderr.strip()[-1000:] if not reachable else None,
    }


def checks_for(slug: str, spec: dict[str, Any], docker: dict[str, Any]) -> dict[str, Any]:
    secret_present = bool(os.environ.get("OPENAI_API_KEY"))
    if spec["kind"] == "coding_agent":
        free_bytes = shutil.disk_usage(ROOT).free
        checks = {
            "docker_cli_present": docker["cli_present"],
            "docker_daemon_reachable": docker["daemon_reachable"],
            "free_disk_at_least_120_gib": free_bytes >= MIN_SWEBENCH_FREE_BYTES,
            "openai_api_key_present": secret_present,
        }
        observations = {"free_disk_bytes": free_bytes, "docker": docker}
    else:
        variables = spec["required_environment"]
        checks = {
            "docker_cli_present": docker["cli_present"],
            "docker_daemon_reachable": docker["daemon_reachable"],
            "all_self_hosted_site_endpoints_present": all(bool(os.environ.get(name)) for name in variables),
            "openai_api_key_present": secret_present,
        }
        observations = {
            "docker": docker,
            "site_endpoint_presence": {name: bool(os.environ.get(name)) for name in variables},
        }
    return {
        "benchmark": slug,
        "declared_status": spec["status"],
        "ready": all(checks.values()),
        "checks": checks,
        "observations": observations,
        "secret_values_recorded": False,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--benchmark",
        choices=("all", "swebench-lite-agent-smoke", "webarena-official-agent-smoke"),
        default="all",
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    choices = list(catalog["benchmarks"])
    if args.benchmark != "all":
        choices = [args.benchmark]
    docker = docker_probe()
    results = [checks_for(slug, catalog["benchmarks"][slug], docker) for slug in choices]
    report = {
        "schema_version": 1,
        "generated_at_utc": dt.datetime.now(dt.UTC).isoformat(),
        "host": {"platform": platform.platform(), "machine": platform.machine()},
        "results": results,
        "all_ready": all(item["ready"] for item in results),
        "claim": "environment readiness only; not benchmark execution evidence",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, sort_keys=True))
    return 0 if report["all_ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
