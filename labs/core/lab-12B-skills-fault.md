# Lab 12B — Skill Capability Escalation｜故障注入

## 实验目标

在合法诊断 Skill 上追加 `database.delete`，但主体 policy 仅允许日志和指标读取。关键 oracle 是任何 step 都未开始，而非执行后才发现危险。

## 环境与版本

Python 3.11–3.13，macOS/Linux、arm64/x86_64；无网络/API key，使用 Lab 12A 的同一 compiler 与锁定 policy。

## 环境准备

执行 `uv sync --locked --all-groups --no-install-project`；恶意 capability 只进入 manifest compiler，不连接真实数据库。

## 实验代码

```bash
PYTHONPATH=src uv run python examples/chapters/ch12_skills.py --fault
```

## 实际输出

```json
{"contained":true,"evidence_level":"L3_CONTAINED","fault":true,"invariant_holds":true,"observation":{"capability_grant":[],"error":"capability_escalation:['database.delete']","execution_order":[],"manifest_sha256":null,"steps_executed":0},"oracle_detected":true,"passed":true,"scenario":"skills","system_detected":true}
```

## 验收标准

必须返回具体新增 capability；compiled graph/grant 为空；`steps_executed=0`。静默取能力交集不算通过，因为 Skill 可能以缺失前提继续产生部分结果。

## 调试断点

把恶意 capability 放入单个 step 但不放 declared list，应触发 `undeclared_step_capability`；构造 A↔B 依赖应触发 cycle；篡改 source bytes 但保留 digest，应在供应链 gate 拒绝。

## Claim ceiling

此 lab 不执行第三方脚本，证明的是 manifest/compiler containment。真实 Skill 安全还要求 filesystem/network/syscall sandbox 和依赖供应链扫描。
