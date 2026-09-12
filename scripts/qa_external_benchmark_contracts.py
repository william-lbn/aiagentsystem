from __future__ import annotations

import json
import re

from common import ROOT


catalog = json.loads((ROOT / "experiments/benchmarks/catalog.json").read_text(encoding="utf-8"))
errors: list[str] = []
commit = re.compile(r"[0-9a-f]{40}")
for slug, spec in catalog.get("benchmarks", {}).items():
    if not commit.fullmatch(spec.get("harness_commit", "")):
        errors.append(f"{slug}: harness commit is not an exact SHA")
    alternative = spec.get("alternative_runner_commit")
    if alternative and not commit.fullmatch(alternative):
        errors.append(f"{slug}: alternative runner commit is not an exact SHA")
    if spec.get("status") == "EXECUTED" and not (ROOT / "evidence/benchmarks" / slug).exists():
        errors.append(f"{slug}: EXECUTED without committed evidence")
    if spec.get("status") != "EXECUTED" and "contains no" not in spec.get("claim_ceiling", ""):
        errors.append(f"{slug}: unexecuted contract lacks an explicit claim ceiling")
    if not spec.get("required_evidence"):
        errors.append(f"{slug}: required evidence is empty")

if errors:
    print("EXTERNAL_BENCHMARK_CONTRACT_QA_FAILED")
    for error in errors:
        print("-", error)
    raise SystemExit(1)
print(f"EXTERNAL_BENCHMARK_CONTRACT_QA_OK contracts={len(catalog['benchmarks'])}")
