from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import os
import subprocess
import sys
import json

ROOT = Path(__file__).resolve().parents[1]
TASKS = []
for p in sorted((ROOT / "examples/chapters").glob("ch*.py")):
    TASKS += [(p, False), (p, True)]


def _run(t):
    p, fault = t
    args = ["--fault"] if fault else []
    mode = "fault" if fault else "normal"
    state_dir = ROOT / "validation_logs" / "pytest_example_state" / f"{p.stem}-{mode}"
    state_dir.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src"), "AGENTLAB_HOME": str(state_dir)}
    cp = subprocess.run([sys.executable, str(p), *args], cwd=ROOT, text=True, capture_output=True, env=env, timeout=30)
    obj = json.loads(cp.stdout.strip().splitlines()[-1])
    return p, cp, obj, fault


def test_all_chapter_examples():
    workers = min(int(os.environ.get("EXAMPLE_TEST_WORKERS", "4")), len(TASKS))
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for p, cp, obj, fault in ex.map(_run, TASKS):
            assert cp.returncode == 0, f"{p.name} fault={fault}\n{cp.stdout}\n{cp.stderr}"
            assert obj["passed"] is True and obj["fault"] is fault
