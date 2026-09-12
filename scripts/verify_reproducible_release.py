"""Legacy compatibility entrypoint.

Historically this script was named 'reproducible release', but its actual proof
was deterministic ZIP/metadata packaging from one already-built source tree.
Keep the entrypoint for downstream automation while making the claim explicit.
"""

from runpy import run_path
from pathlib import Path

run_path(str(Path(__file__).with_name("verify_deterministic_packaging.py")), run_name="__main__")
