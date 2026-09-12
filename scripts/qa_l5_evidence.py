from __future__ import annotations

import hashlib
import json
from pathlib import Path

from common import ROOT


CATALOG = ROOT / "experiments/l5/catalog.json"
EVIDENCE_ROOT = ROOT / "evidence/l5"
REQUIRED = {
    "artifact-hashes.sha256",
    "commands.txt",
    "environment.json",
    "evidence.json",
    "observations.json",
    "stderr.log",
    "stdout.log",
    "verifier.json",
    "wire.json",
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_hashes(path: Path) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        value, name = line.split("  ", 1)
        parsed[name] = value
    return parsed


catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
errors: list[str] = []
passed = 0
for slug, experiment in catalog["experiments"].items():
    root = EVIDENCE_ROOT / slug
    if not root.exists():
        errors.append(f"{slug}: no evidence directory")
        continue
    slug_runs = 0
    for run in sorted(p for p in root.iterdir() if p.is_dir()):
        files = {p.name for p in run.iterdir() if p.is_file()}
        missing = REQUIRED - files
        if missing:
            errors.append(f"{slug}/{run.name}: missing {sorted(missing)}")
            continue
        evidence = json.loads((run / "evidence.json").read_text(encoding="utf-8"))
        verifier = json.loads((run / "verifier.json").read_text(encoding="utf-8"))
        environment = json.loads((run / "environment.json").read_text(encoding="utf-8"))
        if evidence.get("schema_version") != 2 or environment.get("schema_version") != 2:
            errors.append(f"{slug}/{run.name}: unsupported evidence schema")
        if evidence.get("status") != "PASS_EXTERNAL_IMPLEMENTATION_EVIDENCE":
            errors.append(f"{slug}/{run.name}: non-pass evidence committed")
        if evidence.get("authority") != experiment["authority"]:
            errors.append(f"{slug}/{run.name}: authority differs from catalog")
        if evidence.get("claim") != experiment["claim"]:
            errors.append(f"{slug}/{run.name}: claim differs from catalog")
        if evidence.get("claim_ceiling") != experiment["claim_ceiling"]:
            errors.append(f"{slug}/{run.name}: claim ceiling differs from catalog")
        if evidence.get("evidence_vector") != experiment["evidence_vector"]:
            errors.append(f"{slug}/{run.name}: evidence vector differs from catalog")
        source_path = ROOT / experiment["script"]
        if evidence.get("source_script_sha256") != digest(source_path):
            errors.append(f"{slug}/{run.name}: source script changed after evidence generation")
        if verifier.get("all_passed") is not True or not all(verifier.get("assertions", {}).values()):
            errors.append(f"{slug}/{run.name}: verifier did not pass every assertion")
        if environment.get("packages") != experiment["packages"] or environment.get("package_pins_match") is not True:
            errors.append(f"{slug}/{run.name}: package pins do not match catalog")
        recorded = parse_hashes(run / "artifact-hashes.sha256")
        actual = {name: digest(run / name) for name in files if name != "artifact-hashes.sha256"}
        if recorded != actual:
            errors.append(f"{slug}/{run.name}: artifact hash mismatch")
        passed += 1
        slug_runs += 1
    if slug_runs == 0:
        errors.append(f"{slug}: no complete evidence run")

if errors:
    print("L5_EVIDENCE_QA_FAILED")
    for error in errors:
        print("-", error)
    raise SystemExit(1)
print(f"L5_EVIDENCE_QA_OK verified_runs={passed} catalog_experiments={len(catalog['experiments'])}")
