from __future__ import annotations
import os
import subprocess
import sys
import time

cmd = [sys.executable, "-m", "pytest", "-q"]
env = {**os.environ, "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1"}
proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env)
last = time.time()
assert proc.stdout is not None
while True:
    line = proc.stdout.readline()
    if line:
        print(line, end="", flush=True)
        last = time.time()
    elif proc.poll() is not None:
        break
    else:
        if time.time() - last > 10:
            print("PYTEST_HEARTBEAT", flush=True)
            last = time.time()
        time.sleep(0.5)
rc = proc.wait()
if rc != 0:
    raise SystemExit(rc)
