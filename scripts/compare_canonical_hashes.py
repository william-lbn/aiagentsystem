from __future__ import annotations

import argparse
import json
from pathlib import Path


parser = argparse.ArgumentParser()
parser.add_argument("directory", type=Path)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()

reports = [
    json.loads(path.read_text(encoding="utf-8")) for path in sorted(args.directory.rglob("canonical-hashes-*.json"))
]
if len(reports) < 2:
    raise SystemExit("CROSS_HOST_COMPARE_REQUIRES_TWO_MANIFESTS")
producers = [report["producer"] for report in reports]
if len(set(producers)) != len(producers):
    raise SystemExit("CROSS_HOST_COMPARE_REQUIRES_DISTINCT_PRODUCERS")
baseline = reports[0]["artifacts"]
differences: dict[str, dict[str, str | None]] = {}
for report in reports[1:]:
    for name in sorted(set(baseline) | set(report["artifacts"])):
        if baseline.get(name) != report["artifacts"].get(name):
            differences[f"{reports[0]['producer']}::{report['producer']}::{name}"] = {
                reports[0]["producer"]: baseline.get(name),
                report["producer"]: report["artifacts"].get(name),
            }
result = {
    "schema_version": 1,
    "status": "PASS_CROSS_HOST_CANONICAL_EQUIVALENCE" if not differences else "FAIL_CROSS_HOST_CANONICAL_EQUIVALENCE",
    "producers": producers,
    "artifact_count": len(baseline),
    "differences": differences,
}
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(result["status"], f"producers={producers}", f"artifacts={len(baseline)}", f"differences={len(differences)}")
raise SystemExit(0 if not differences else 1)
