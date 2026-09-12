from __future__ import annotations
import subprocess
import sys
from common import ROOT

subprocess.run([sys.executable, str(ROOT / "scripts/publish.py"), "book", "--engine", "auto"], check=True)
