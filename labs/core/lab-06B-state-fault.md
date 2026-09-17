# Lab 06B — 并发 Stale Writer 与 CAS 约束｜故障注入

## 实验目标

让两个 reader 同时读取 version 1；A 写入 version 2 后，B 仍以 expected version 1 伪写 `FINISHED`。要求真实 checkpoint store 抛出冲突并保留 version 2/RUNNING。

## 环境与版本

Python `3.11–3.13`；macOS/Linux POSIX 文件系统；`arm64/x86_64`；无网络、Docker 或 API key。若把目录放到语义不同的网络文件系统，应重新验证锁与 rename 保证。

## 环境准备

```bash
python -m pip install uv==0.10.0
uv sync --locked --all-groups --no-install-project
```

## 实验代码与故障模型

入口 `examples/chapters/ch06_state.py --fault`。不是直接构造 exception：reader A/B 均调用 `store.load`，A 实际提交 version 2，B 实际调用 `store.save(... expected_version=1)` 触发 `CheckpointConflictError`。

## 运行步骤

```bash
PYTHONPATH=src uv run python examples/chapters/ch06_state.py --fault
```

## 实际验证输出

```json
{"phase": "RUNNING", "stale_write_rejected": true, "trajectory_sha256": "8677d6a0e96bdc5c", "trajectory_valid": true, "version": 2}
```

## 调试断点

在两次 load 记录共同版本 1；在 A 保存后确认 current=2；在 B 的 CAS 比较观察 expected=1/current=2；捕获后重新 load，确认 state 未被污染。

## 验收标准

冲突由 SUT 检测，stale write 被阻断，最终 version 恰为 2 且 phase 仍为 RUNNING；完整结果为 `system_detected=true/contained=true/invariant_holds=true/L3_CONTAINED`。

## 证据解释与上限

L3 证明 checkpoint lost update 被约束，不代表业务已恢复。CAS 也不能阻止租约过期 worker 绕过 store 调用外部工具；跨主机需 fencing/lease 与外部执行层协同。

## 进阶实验

在工具网关加入单调 fencing token；模拟旧 worker 已持有凭据并尝试写外部系统，要求网关拒绝旧 epoch，证明保护范围从 checkpoint 扩展到 effect boundary。
