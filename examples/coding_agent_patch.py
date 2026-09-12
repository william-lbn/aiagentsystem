from pathlib import Path
import subprocess
import tempfile
import shutil
import sys

FIXTURE = Path("production/coding_ops/fixture_repo")
with tempfile.TemporaryDirectory() as td:
    work = Path(td) / "repo"
    shutil.copytree(FIXTURE, work)
    before = subprocess.run([sys.executable, "-m", "pytest", "-q"], cwd=work, text=True, capture_output=True)
    target = work / "calculator.py"
    text = target.read_text()
    target.write_text(text.replace("return a - b  # BUG", "return a + b"))
    after = subprocess.run([sys.executable, "-m", "pytest", "-q"], cwd=work, text=True, capture_output=True)
    print("before_rc", before.returncode, "after_rc", after.returncode)
    print("patch", target.read_text().strip())
