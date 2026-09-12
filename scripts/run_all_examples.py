from __future__ import annotations
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
import subprocess
import sys
import time
import json
import signal

ROOT = Path(__file__).resolve().parents[1]
ENV = {**os.environ, "PYTHONPATH": os.pathsep.join([str(ROOT / "src"), str(ROOT)])}
FILES = sorted((ROOT / "examples").glob("*.py")) + sorted((ROOT / "examples/chapters").glob("ch*.py"))


def _run(p: Path):
    t = time.time()
    # Examples execute concurrently, so mutable runtime state must be isolated
    # per process. Without this, unrelated examples contend on the same default
    # checkpoint/journal and a clean validation can become timing-dependent.
    safe = p.relative_to(ROOT).as_posix().replace("/", "__").replace(".py", "")
    state_dir = ROOT / "validation_logs" / "example_state" / safe
    state_dir.mkdir(parents=True, exist_ok=True)
    env = {**ENV, "AGENTLAB_HOME": str(state_dir)}
    proc = subprocess.Popen(
        [sys.executable, str(p)],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        start_new_session=True,
    )
    try:
        out, err = proc.communicate(timeout=25)
        return {
            "file": str(p.relative_to(ROOT)),
            "returncode": proc.returncode,
            "seconds": round(time.time() - t, 3),
            "stdout": out[-5000:],
            "stderr": err[-5000:],
        }
    except subprocess.TimeoutExpired:
        # Kill the whole process group so descendants cannot keep stdout/stderr pipes open.
        os.killpg(proc.pid, signal.SIGKILL)
        out, err = proc.communicate()
        return {
            "file": str(p.relative_to(ROOT)),
            "returncode": 124,
            "seconds": round(time.time() - t, 3),
            "stdout": out[-5000:],
            "stderr": (err[-5000:] + "\nTIMEOUT >25s").strip(),
        }


results = []
# Keep fan-out deliberately small: high fork/exec fan-out can stall on constrained CI hosts.
# Each child has its own hard timeout, and four workers still keep the full suite fast.
workers = min(int(os.environ.get("EXAMPLE_WORKERS", "4")), max(1, len(FILES)))
with ThreadPoolExecutor(max_workers=workers) as ex:
    futs = [ex.submit(_run, p) for p in FILES]
    for fut in as_completed(futs):
        r = fut.result()
        results.append(r)
        print(f"[{r['returncode']}] {r['file']} {r['seconds']:.2f}s", flush=True)
results.sort(key=lambda x: x["file"])
logdir = ROOT / "validation_logs"
logdir.mkdir(exist_ok=True)
(logdir / "examples.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
failed = [r for r in results if r["returncode"] != 0]
if failed:
    for r in failed:
        print("FAIL", r["file"], r["stderr"][-1000:], file=sys.stderr)
    raise SystemExit(1)
print(
    f"ALL_EXAMPLES_OK total={len(results)} support={len(list((ROOT / 'examples').glob('*.py')))} chapters={len(list((ROOT / 'examples/chapters').glob('ch*.py')))}"
)
