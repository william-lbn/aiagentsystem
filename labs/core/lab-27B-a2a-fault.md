# Lab 27B — A2A 与 Multi-Agent 互操作｜故障注入

## 实验目标

构造一个 **协议完全合法但授权不足** 的 A2A 请求：grant 只含 `artifact.publish`，调用却要求 `repository.write`。验证系统在创建 Task、写 artifact 或产生 effect 前 fail closed。

## 可证伪假设与故障位置

若实现误把“Card 声称支持某能力”或“消息 schema 合法”当成授权，本次调用会在数据库留下任务行。正确实现必须返回 `delegation_scope_missing`，并满足 `persisted_tasks=0`、`artifact_effects=0`。

该故障刻意不破坏 wire schema，因为解析失败无法证明授权边界有效。

## 环境与版本

与 Lab 27A 相同：Python 3.11–3.13、标准库 SQLite/HMAC、本仓库 AgentLab；不需要网络、Docker、模型或 API key。先执行 27A，确保正常路径基线通过。

## 环境准备

```bash
python -m pip install uv==0.10.0
uv sync --locked --all-groups --no-install-project
```

## 实验代码

入口为 `examples/chapters/ch27_a2a.py`，故障注入位于 `course_scenarios.a2a`，授权检查由 `coordination_system.DelegationAuthority.verify` 执行。

## 执行步骤

```bash
PYTHONPATH=src uv run python examples/chapters/ch27_a2a.py --fault
```

场景先验证 Card/Task wire contract，再用有效签名和正确 task/delegate 提交，但将 `required_scope` 改为未授予的 `repository.write`。`DelegationAuthority.verify` 应在任何 SQLite insert 前抛出异常。

## 实际验证输出（本发布源码 QA 生成）

```json
{"contained": true, "evidence_level": "L3_CONTAINED", "evidence_meaning": "fault_detected_and_contained", "fault": true, "fault_injected": true, "invariant": "A2A interoperability requires protocol validation plus task-bound authorization and durable lifecycle evidence", "invariant_holds": true, "observation": {"artifact_effects": 0, "grant": {"delegate": "researcher", "scopes": ["artifact.publish", "evidence.read"], "task_id": "task-27"}, "persisted_tasks": 0, "protocol_errors": [], "protocol_valid": true, "rejected": "delegation_scope_missing"}, "oracle_detected": true, "passed": true, "recovered": false, "scenario": "a2a", "system_detected": true}
```

## 调试断点

- `DelegationAuthority.verify` 的 required-scope 分支；
- `A2ATaskLedger.submit` 调用 verifier 的第一行；
- `A2ATaskLedger.task_count`，确认异常后没有半成品；
- `course_scenarios.a2a` 的 fault exception handler，确认只接受精确错误类型。

## 验收标准

PASS 当且仅当：退出码 0；wire 仍 `protocol_valid=true`；`rejected=delegation_scope_missing`；任务与 artifact effect 都为 0；`system_detected=true`、`contained=true`、`evidence_level=L3_CONTAINED`。

`passed=true` 只表示故障注入得到预期证据。L3 表示被测系统主动阻断扩散，不表示业务已恢复或远端 IAM 已通过生产审计。

## 反例与进阶注入

- 修改已签名 scopes 但保留旧 signature，应得到 `delegation_signature_invalid`；
- 保持 scope 正确但更换 task ID，应得到 `delegation_task_mismatch`；
- 把 `now` 设为 expiry，应得到 `delegation_expired_or_not_yet_valid`；
- 复用 nonce 创建另一 task，应得到 `delegation_nonce_or_identity_reused`；
- 在真实 SDK server 的 auth hook 注入同类故障，并保存 HTTP/JSON-RPC 错误、task-store 查询和服务端 effect log，才可提高外部证据等级。

## 结果解释与声明边界

本实验最重要的观察不是异常文本，而是数据库与 effect 仍为空。它证明本地授权 guard 位于副作用之前；不证明 HMAC fixture 可作为生产 token，也不把一次 scope 拒绝外推为完整 zero-trust 架构。
