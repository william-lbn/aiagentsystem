# Lab 06A — 事件重放与版本化 Checkpoint｜正常路径

## 实验目标

验证合法事件序列可由 reducer 重放到 `FINISHED`，每次持久化通过真实 `JsonCheckpointStore` 递增版本，并保存 trajectory digest。

## 环境与版本

Python `3.11–3.13`；macOS 13+/Ubuntu 22.04+ 的 POSIX 文件语义；`arm64/x86_64`；无网络、Docker 或 API key。临时目录内执行 file lock、fsync 与 atomic replace。

## 环境准备

```bash
python -m pip install uv==0.10.0
uv sync --locked --all-groups --no-install-project
```

## 实验代码与输入

- 入口：`examples/chapters/ch06_state.py`
- reducer：`foundation_system.py::RunStateReducer`
- store：`checkpoint.py::JsonCheckpointStore`

事件依次为收到请求、持久化工具 intent、观察工具结果、验证产物；phase 走 `RECEIVED→RUNNING→WAITING_TOOL→RUNNING→FINISHED`。

## 运行步骤

```bash
PYTHONPATH=src uv run python examples/chapters/ch06_state.py
```

## 实际验证输出

```json
{"phase": "FINISHED", "stale_write_rejected": false, "trajectory_sha256": "15eb13b91c3f77d0", "trajectory_valid": true, "version": 3}
```

## 调试断点

检查 reducer 的 sequence/from/to；`persist_replay` 拒绝 invalid 轨迹；store 在锁内比较 expected/current；观察 temp write、fsync、replace 和最终 load。

## 验收标准

轨迹合法，最终 phase 为 FINISHED，checkpoint version 为 3，digest 非空且重复运行稳定，完整结果为 `L1_MECHANISM`。

## 证据解释与上限

这是单机 POSIX checkpoint 机制证据，不证明跨主机共识、灾备或外部副作用 exactly-once。`FINISHED` 仅因 fixture 的 `artifact_verified` 事件成立。

## 进阶实验

在每个持久化窗口模拟进程 kill，枚举恢复点；要求恢复不重新执行已记录工具结果，也不跳过尚未验证的后置条件。
