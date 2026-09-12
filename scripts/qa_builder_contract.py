from __future__ import annotations
import json
import re
from common import ROOT, build_cfg

cfg = build_cfg()
errors = []
docker = (ROOT / "Dockerfile.builder").read_text(encoding="utf-8")
lock = json.loads((ROOT / "builder.lock.json").read_text(encoding="utf-8"))
base = lock.get("canonical_base_image", "")
if "@sha256:" not in base or not re.fullmatch(r".+@sha256:[0-9a-f]{64}", base):
    errors.append("canonical base image is not digest pinned")
if f"FROM {base}" not in docker:
    errors.append("Dockerfile FROM differs from builder.lock canonical_base_image")
uv = str(lock.get("uv", ""))
if not uv or f"uv=={uv}" not in docker:
    errors.append("uv pin differs between Dockerfile and builder.lock")
requested = lock.get("os_packages_requested")
if not isinstance(requested, list) or not requested:
    errors.append("missing os_packages_requested")
else:
    for pkg in requested:
        if not re.search(r"(?<![A-Za-z0-9_.+-])" + re.escape(pkg) + r"(?![A-Za-z0-9_.+-])", docker):
            errors.append(f"package not requested by Dockerfile: {pkg}")
policy = lock.get("supply_chain_policy", {})
if policy.get("base_image") != "digest-pinned":
    errors.append("base image policy must be digest-pinned")
ceiling = str(policy.get("claim_ceiling", ""))
if "not bit-hermetic" not in ceiling:
    errors.append("APT non-hermetic claim ceiling must remain explicit")
if "dpkg" not in str(policy.get("os_packages", "")):
    errors.append("resolved dpkg inventory evidence is not required by policy")
if errors:
    print("BUILDER_LOCK_QA_FAILED")
    for e in errors:
        print("-", e)
    raise SystemExit(1)
print(
    f"BUILDER_LOCK_QA_OK build_system={cfg['system_version']} base_digest={base.rsplit('@', 1)[-1][:19]}... uv={uv} apt_claim=non-hermetic-recorded"
)
