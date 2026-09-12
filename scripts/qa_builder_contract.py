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
texlive_requested = lock.get("texlive_packages_requested")
if not isinstance(texlive_requested, dict) or not texlive_requested:
    errors.append("missing texlive_packages_requested")
else:
    if not re.search(r"\btlmgr\s+update\s+--self\b", docker):
        errors.append("Dockerfile does not update the base image's stale tlmgr before package resolution")
    if not re.search(r"\btlmgr\s+install\b", docker):
        errors.append("Dockerfile does not explicitly install TeX Live packages")
    for pkg, required_file in texlive_requested.items():
        if not re.search(r"(?<![A-Za-z0-9_.+-])" + re.escape(pkg) + r"(?![A-Za-z0-9_.+-])", docker):
            errors.append(f"TeX Live package not requested by Dockerfile: {pkg}")
        if f'kpsewhich {required_file}' not in docker:
            errors.append(f"TeX Live artifact not verified by Dockerfile: {required_file}")
policy = lock.get("supply_chain_policy", {})
if policy.get("base_image") != "digest-pinned":
    errors.append("base image policy must be digest-pinned")
ceiling = str(policy.get("claim_ceiling", ""))
if "not bit-hermetic" not in ceiling or "APT" not in ceiling or "CTAN" not in ceiling:
    errors.append("APT/CTAN non-hermetic claim ceiling must remain explicit")
if "dpkg" not in str(policy.get("os_packages", "")):
    errors.append("resolved dpkg inventory evidence is not required by policy")
if "revision" not in str(policy.get("texlive_packages", "")):
    errors.append("resolved TeX Live revision inventory evidence is not required by policy")
if errors:
    print("BUILDER_LOCK_QA_FAILED")
    for e in errors:
        print("-", e)
    raise SystemExit(1)
print(
    f"BUILDER_LOCK_QA_OK build_system={cfg['system_version']} base_digest={base.rsplit('@', 1)[-1][:19]}... uv={uv} apt_ctan_claim=non-hermetic-recorded"
)
