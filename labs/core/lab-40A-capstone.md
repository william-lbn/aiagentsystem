# Lab 40A — Capstone：权限、审批、唯一副作用与独立验证｜正常路径

## 实验目标

运行真实 SQLite 状态链与独立 provider SQLite：实验主体拥有精确 capability，调用方提供的审批夹具绑定 canonical intent digest，远端只提交一个 effect，最后由 verifier 复核 receipt、effect count 和 tamper-evident event chain 后进入 `COMPLETED`。本实验不验证真实人审身份或签名。

## 可证伪假设与不变量

不变量：最终文本、状态名或模型 claim 都不能单独表示完成；authority、approval、effect、trace 与 verifier 必须同时闭合。

## 环境与版本

- Python 3.11–3.13，x86_64/arm64；标准库 SQLite；
- 不需要模型、Docker、网络或 API key；
- 两个数据库真实分离本地 coordinator 与 provider，仍不等价于真实 SaaS 的网络/一致性语义。

## 环境准备

```bash
python -m pip install uv==0.10.0
uv sync --locked --all-groups --no-install-project
```

## 实验代码

```python
orchestrator = CapstoneOrchestrator(workdir)
approval = orchestrator.demonstration_approval("run-capstone")
result = orchestrator.run("run-capstone", approval=approval)
assert result["path"][-1] == "COMPLETED"
assert result["approval_bound"] and result["capability_allowed"]
assert result["effect_count"] == 1 and result["trace_verified"] and result["verified"]
orchestrator.close()
```

## 执行步骤

```bash
PYTHONPATH=src uv run python examples/chapters/ch40_capstone.py
```

## 实际验证输出（本发布源码执行所得）

```json
{"path":["RECEIVED","TRIAGED","PLANNED","WAITING_APPROVAL","EXECUTING","VERIFYING","COMPLETED"],"capability_allowed":true,"approval_bound":true,"effect_count":1,"recovery_used":false,"trace_verified":true,"verified":true,"evidence_level":"L1_MECHANISM"}
```

## 调试断点

- capability 对 principal/action/resource 的精确匹配；
- approval receipt 的 intent digest；
- effect key 与 provider unique constraint；
- event hash chain 和 verifier 收敛条件。

## 验收标准

退出码 0；状态按允许边推进到 `COMPLETED`；本地 capability 与审批字段绑定都为真；effect count 恰为 1；chain/verifier 为真。L1 证明本地端到端机制，不声称真实人审或真实 provider 已运行。把审批 `run_id` 改成另一 run 时，必须在 `EXECUTING` 前失败且 provider effect count 为 0。

## 反例与进阶注入

- 把 local/provider 换成不同容器和网络，再重演 timeout/crash；
- 接入 OpenAI 或小型开源模型只负责 proposal，保留同一 capability/effect/verifier；
- 引入多租户 API、审计导出、人工审批服务和真实 ticket sandbox，形成 L5 外部证据。
