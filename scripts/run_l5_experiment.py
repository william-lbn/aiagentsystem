from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import platform
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from common import ROOT


CATALOG = ROOT / "experiments/l5/catalog.json"
DEFAULT_EVIDENCE_ROOT = ROOT / "evidence/l5"
REQUIRED_ARTIFACTS = {"observations.json", "wire.json", "verifier.json"}
SECRET_NAME = re.compile(r"(?:^|_)(?:API_?KEY|TOKEN|SECRET|PASSWORD|CREDENTIALS?)(?:$|_)", re.IGNORECASE)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def inspect_python(python: Path, packages: dict[str, str]) -> dict[str, Any]:
    code = (
        "import importlib.metadata as m,json,platform,sys;"
        f"names={list(packages)!r};"
        "print(json.dumps({'python':sys.version,'executable':sys.executable,"
        "'platform':platform.platform(),'machine':platform.machine(),"
        "'packages':{n:m.version(n) if any(d.metadata['Name'].lower()==n.lower() for d in m.distributions()) else None for n in names}},sort_keys=True))"
    )
    proc = subprocess.run([str(python), "-c", code], cwd=ROOT, text=True, capture_output=True, timeout=60)
    if proc.returncode:
        raise RuntimeError(f"cannot inspect experiment interpreter: {proc.stderr.strip()}")
    return json.loads(proc.stdout)


def validate_verifier(path: Path, slug: str) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    assertions = data.get("assertions")
    if data.get("experiment") != slug:
        raise ValueError("verifier experiment id does not match catalog slug")
    if not isinstance(assertions, dict) or not assertions or not all(isinstance(v, bool) for v in assertions.values()):
        raise ValueError("verifier.assertions must be a non-empty bool mapping")
    if data.get("all_passed") is not all(assertions.values()):
        raise ValueError("verifier.all_passed is inconsistent with assertions")
    return data


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run one externally versioned evidence experiment")
    parser.add_argument("slug")
    parser.add_argument("--python", type=Path, default=Path(sys.executable))
    parser.add_argument("--run-id", required=True, help="Immutable evidence directory name")
    parser.add_argument("--evidence-root", type=Path, default=DEFAULT_EVIDENCE_ROOT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    experiment = catalog.get("experiments", {}).get(args.slug)
    if experiment is None:
        raise SystemExit(f"unknown experiment: {args.slug}")
    # Do not resolve the venv launcher symlink: resolving it to the base
    # interpreter discards the virtual environment's site-packages.
    python = args.python if args.python.is_absolute() else (ROOT / args.python).absolute()
    if not python.is_file():
        raise SystemExit(f"experiment interpreter not found: {python}")
    target = (args.evidence_root / args.slug / args.run_id).resolve()
    if target.exists():
        raise SystemExit(f"refusing to overwrite immutable evidence: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)

    environment = inspect_python(python, experiment["packages"])
    expected_packages = experiment["packages"]
    pins_match = environment["packages"] == expected_packages
    command: list[str] = [str(python), str(ROOT / experiment["script"])]

    with tempfile.TemporaryDirectory(prefix=f"agentlab-{args.slug}-") as temporary:
        staging = Path(temporary)
        command.append(str(staging))
        run_env = os.environ.copy()
        removed_secret_names = sorted(name for name in run_env if SECRET_NAME.search(name))
        for name in removed_secret_names:
            run_env.pop(name, None)
        proc = subprocess.run(command, cwd=ROOT, env=run_env, text=True, capture_output=True, timeout=180)
        target.mkdir(parents=True)
        (target / "stdout.log").write_text(proc.stdout, encoding="utf-8")
        (target / "stderr.log").write_text(proc.stderr, encoding="utf-8")
        inherited_pythonpath = run_env.get("PYTHONPATH")
        rendered_command = shlex.join(command)
        if inherited_pythonpath:
            rendered_command = f"PYTHONPATH={shlex.quote(inherited_pythonpath)} {rendered_command}"
        (target / "commands.txt").write_text(rendered_command + "\n", encoding="utf-8")
        environment.update(
            {
                "schema_version": 2,
                "os": platform.system(),
                "os_release": platform.release(),
                "processor": platform.processor(),
                "expected_packages": expected_packages,
                "package_pins_match": pins_match,
                "pythonpath": inherited_pythonpath,
                "secret_filter": "deny names matching API_KEY/TOKEN/SECRET/PASSWORD/CREDENTIAL(S)",
                "secret_variable_count_removed": len(removed_secret_names),
            }
        )
        (target / "environment.json").write_text(
            json.dumps(environment, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        for path in staging.iterdir():
            if path.is_file():
                shutil.copy2(path, target / path.name)

    missing = sorted(REQUIRED_ARTIFACTS - {p.name for p in target.iterdir() if p.is_file()})
    verifier: dict[str, Any] | None = None
    validation_error: str | None = None
    if not missing:
        try:
            verifier = validate_verifier(target / "verifier.json", args.slug)
        except (ValueError, json.JSONDecodeError) as exc:
            validation_error = str(exc)

    passed = bool(
        proc.returncode == 0
        and pins_match
        and not missing
        and validation_error is None
        and verifier
        and verifier["all_passed"]
    )
    status = "PASS_EXTERNAL_IMPLEMENTATION_EVIDENCE" if passed else "FAIL_EXTERNAL_EVIDENCE"
    summary = {
        "schema_version": 2,
        "experiment": args.slug,
        "status": status,
        "executed_at_utc": dt.datetime.now(dt.UTC).isoformat(),
        "exit_code": proc.returncode,
        "authority": experiment["authority"],
        "claim": experiment["claim"],
        "claim_ceiling": experiment["claim_ceiling"],
        "evidence_vector": experiment["evidence_vector"],
        "package_pins_match": pins_match,
        "missing_artifacts": missing,
        "validation_error": validation_error,
        "source_script_sha256": sha256(ROOT / experiment["script"]),
    }
    (target / "evidence.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    hashes = {
        path.name: sha256(path)
        for path in sorted(target.iterdir())
        if path.is_file() and path.name != "artifact-hashes.sha256"
    }
    (target / "artifact-hashes.sha256").write_text(
        "".join(f"{digest}  {name}\n" for name, digest in hashes.items()),
        encoding="utf-8",
    )
    print(json.dumps({"evidence_dir": str(target), **summary}, ensure_ascii=False, sort_keys=True))
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
