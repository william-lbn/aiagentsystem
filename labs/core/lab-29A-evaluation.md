# Lab 29A — Agent Evaluation：从最终答案到轨迹验证｜正常路径

## 实验目标

运行一个具有真实 SQLite 证据账本的 release gate：Agent 可以声明 `PASS`，但只有独立 verifier 对 task digest、最终答案、外部 effect、步骤预算和 trajectory 逐项核验后，run 才能进入 `ELIGIBLE`。

可证伪不变量：**only an independent verifier over durable observations may authorize promotion; an agent success claim has no authority**。

## 环境与版本

- Python 3.11–3.13，x86_64/arm64 均可；核心路径只使用标准库与本仓库代码；
- SQLite 文件在临时目录创建并真正提交 transaction；不需要模型、网络、Docker 或 API key；
- 可选模型只负责生成候选答案，不能调用 `verify()` 或修改 verdict 表。

## 环境准备

```bash
python -m pip install uv==0.10.0
uv sync --locked --all-groups --no-install-project
```

## 实验代码

入口为 `examples/chapters/ch29_evaluation.py`；场景编排在 `course_scenarios.evaluation`；持久任务、run、observation 与 verdict 位于 `assurance_system.EvaluationLedger`。本例注册版本化任务、记录工具 observation、写入 Agent 声明，最后由 ledger 重新读取事实进行验证。

关键逻辑不是 `answer == "42"` 本身，而是判定权分离：

```python
checks = {
    "answer": hmac.compare_digest(row["final_answer"], spec["expected_answer"]),
    "effects": set(effects).issubset(set(spec["allowed_effects"])),
    "budget": 0 <= row["step_count"] <= spec["max_steps"],
    "trajectory_present": observation_count > 0,
}
promotion = "ELIGIBLE" if all(checks.values()) else "QUARANTINED"
```

## 执行步骤

```bash
PYTHONPATH=src uv run python examples/chapters/ch29_evaluation.py
```

## 实际验证输出（本发布源码执行所得）

```json
{"agent_claim":"PASS","checks":{"answer":true,"budget":true,"effects":true,"trajectory_present":true},"promotion_status":"ELIGIBLE","verifier_passed":true,"evidence_level":"L1_MECHANISM"}
```

完整 CLI 还会输出固定 task digest、证据语义和不变量。这里省略不影响判定的外层字段，digest 可由相同 canonical task spec 重算。

## 调试断点

- `EvaluationLedger.register`：确认版本化 spec 的 canonical digest；
- `EvaluationLedger.finish`：确认这里只写 `agent_claim` 和 observations，不授予成功；
- `EvaluationLedger.verify`：分别翻转 answer/effects/budget/trajectory；
- verdict transaction：确认 `ELIGIBLE` 与完整 verdict 同时持久化。

## 验收标准

退出码为 0；四项 checks 全为 true；`promotion_status=ELIGIBLE`；`invariant_holds=true`。L1 只证明该离线任务的机制路径，不代表任何远程模型质量或业务成功率。

## 扩展到真实模型

把模型调用放在 `finish` 之前，保持 task/verifier 不变。OpenAI 可选路径使用 `OpenAI()` 从 `OPENAI_API_KEY` 环境变量取凭据，模型名从项目自定义环境变量读取；本地模型可通过 Ollama、llama.cpp 或 vLLM 的 OpenAI-compatible endpoint 接入。不得把 key 写入 task、prompt、SQLite、trace 或实验输出，也不得把一次运行改写成 benchmark 百分比。
