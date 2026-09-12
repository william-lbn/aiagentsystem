from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import Counter
import subprocess
import sys
import os
import json
import shutil

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "validation_logs/core_labs"
OUT.mkdir(parents=True, exist_ok=True)
for p in OUT.glob("*.log"):
    p.unlink()
for p in OUT.glob("*.json"):
    p.unlink()
shutil.rmtree(OUT / "state", ignore_errors=True)

tasks = []
for p in sorted((ROOT / "examples/chapters").glob("ch*.py")):
    tasks += [(p, "normal", []), (p, "fault", ["--fault"])]


def run(t):
    p, mode, args = t
    try:
        # Parallel labs must never share mutable checkpoint/journal state.
        # Isolating AGENTLAB_HOME makes failures semantic rather than lock-contention artifacts.
        state_dir = OUT / "state" / f"{p.stem}-{mode}"
        state_dir.mkdir(parents=True, exist_ok=True)
        env = {**os.environ, "PYTHONPATH": str(ROOT / "src"), "AGENTLAB_HOME": str(state_dir)}
        cp = subprocess.run(
            [sys.executable, str(p), *args], cwd=ROOT, text=True, capture_output=True, env=env, timeout=30
        )
        (OUT / f"{p.stem}-{mode}.log").write_text(cp.stdout + cp.stderr, encoding="utf-8")
        parsed = json.loads(cp.stdout.strip().splitlines()[-1]) if cp.stdout.strip() else {}
        ok = (
            cp.returncode == 0
            and parsed.get("passed") is True
            and parsed.get("fault") == (mode == "fault")
            and parsed.get("evidence_level")
        )
        return {
            "file": p.name,
            "mode": mode,
            "ok": ok,
            "returncode": cp.returncode,
            "result": parsed,
            "stdout": cp.stdout,
            "stderr": cp.stderr,
        }
    except Exception as e:
        return {
            "file": p.name,
            "mode": mode,
            "ok": False,
            "returncode": -1,
            "result": {},
            "stdout": "",
            "stderr": repr(e),
        }


results = []
workers = min(int(os.environ.get("CORE_LAB_WORKERS", "4")), len(tasks))
with ThreadPoolExecutor(max_workers=workers) as ex:
    for f in as_completed([ex.submit(run, t) for t in tasks]):
        results.append(f.result())
results.sort(key=lambda x: (x["file"], x["mode"]))
fails = [r for r in results if not r["ok"]]
levels = Counter(r["result"].get("evidence_level", "MISSING") for r in results if r["mode"] == "fault")
summary = {
    "total": len(results),
    "pass": len(results) - len(fails),
    "fail": len(fails),
    "normal_count": sum(r["mode"] == "normal" for r in results),
    "fault_count": sum(r["mode"] == "fault" for r in results),
    "fault_evidence_levels": dict(sorted(levels.items())),
    "semantics": {
        "passed": "scenario oracle observed its expected result",
        "L2_ORACLE_ONLY": "fault visible to independent oracle; no system containment claim",
        "L2_DETECTED": "system detected fault; no containment/recovery claim",
        "L3_CONTAINED": "system detected and contained/fail-closed",
        "L4_RECOVERED": "system detected, contained, and reconciled/recovered",
    },
}
(OUT / "SUMMARY.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
print(f"CORE_LABS total={summary['total']} pass={summary['pass']} fail={summary['fail']}")
print("FAULT_EVIDENCE", json.dumps(summary["fault_evidence_levels"], sort_keys=True))
for r in fails[:20]:
    print("FAIL", r["file"], r["mode"], r["returncode"], r["result"], r["stderr"])
raise SystemExit(1 if fails else 0)
