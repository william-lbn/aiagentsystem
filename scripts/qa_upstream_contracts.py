from __future__ import annotations
import json
from common import ROOT, build_cfg

cfg = build_cfg()
errors = []
contracts = json.loads((ROOT / "integrations/UPSTREAM_BEHAVIOR_CONTRACTS.json").read_text(encoding="utf-8"))
files = sorted((ROOT / "labs/upstream").glob("*.md"))
if len(files) != cfg["expected_upstream_labs"]:
    errors.append(f"upstream lab count={len(files)} expected={cfg['expected_upstream_labs']}")
if len(contracts) != cfg["expected_upstream_labs"]:
    errors.append(f"contract count={len(contracts)} expected={cfg['expected_upstream_labs']}")
required_sections = [
    "## 行为合同",
    "### 正常场景",
    "### 故障场景",
    "### 独立 Verifier",
    "## 最小证据包",
    "## 判定规则",
    "## Claim Ceiling",
]
for p in files:
    slug = p.stem
    text = p.read_text(encoding="utf-8")
    c = contracts.get(slug)
    if not c:
        errors.append(f"{p.name}: missing machine contract")
        continue
    for sec in required_sections:
        if sec not in text:
            errors.append(f"{p.name}: missing {sec}")
    for token in ["EXTERNAL_NOT_RUN_IN_THIS_RELEASE", "PASS_L5_EXTERNAL", "verifier.json", "artifact-hashes.sha256"]:
        if token not in text:
            errors.append(f"{p.name}: missing token {token}")
    if c.get("status") != "EXTERNAL_NOT_RUN_IN_THIS_RELEASE":
        errors.append(f"{slug}: false execution status")
    if not str(c.get("pin", "")).strip():
        errors.append(f"{slug}: missing pin")
    if not str(c.get("source", "")).startswith("https://"):
        errors.append(f"{slug}: source must be https")
    if len(str(c.get("normal", ""))) < 60 or len(str(c.get("fault", ""))) < 50 or len(str(c.get("verifier", ""))) < 35:
        errors.append(f"{slug}: behavior contract too shallow")
if errors:
    print("UPSTREAM_CONTRACT_QA_FAILED")
    for e in errors:
        print("-", e)
    raise SystemExit(1)
print(f"UPSTREAM_CONTRACT_QA_OK contracts={len(contracts)} status=EXTERNAL_NOT_RUN_IN_THIS_RELEASE")
