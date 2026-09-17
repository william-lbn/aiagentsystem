# Lab 04A — 闭合的 Tool Call/Result 轨迹｜正常路径

## 实验目标

验证类型化 ledger 接受 `user → tool call → matching result → final`，并在最终响应前清空所有 pending calls；轨迹通过稳定 canonical JSON 产生 digest。

## 环境与版本

Python `3.11–3.13`；macOS/Linux；`arm64/x86_64`；无网络、Docker 或 API key。只依赖标准库和仓库 `MessageLedger`。

## 环境准备

```bash
python -m pip install uv==0.10.0
uv sync --locked --all-groups --no-install-project
```

## 实验代码与输入

入口 `examples/chapters/ch04_messages.py`；SUT `foundation_system.py::MessageLedger`。调用 `call-7/read_ticket` 查询 `INC-2048`；返回同一 call ID/name 后才追加最终消息。

## 运行步骤

```bash
PYTHONPATH=src uv run python examples/chapters/ch04_messages.py
```

## 实际验证输出

```json
{"accepted": [true, true, true, true], "errors": [], "ledger_size": 4, "pending_calls": [], "trajectory_sha256": "7fa13744dfddaf47"}
```

## 调试断点

在 `MessageLedger.append` 的 item ID、tool-call registration、tool-result match、final pending gate 与 digest serialization 处观察。结果到达前 pending 应为 `call-7`，匹配后应为空。

## 验收标准

四次 append 全部接受，ledger 恰为 4 项，pending 为空，digest 与同一环境重复运行一致，完整结果为 `L1_MECHANISM`。

## 证据解释与上限

实验验证单进程 canonical ledger，不证明多写者线性一致性、数字签名或 provider stream 的真实互操作。显示哈希为完整 SHA-256 的前 16 位。

## 进阶实验

创建两个并行 calls 并逆序返回结果；要求二者按 identity 正确闭合，再定义一个确定性的派生排序用于比较语义等价轨迹。
