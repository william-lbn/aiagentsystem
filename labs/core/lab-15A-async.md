# Lab 15A — 异步 Runtime：有界并发｜正常路径

## 实验目标

运行三个真实 coroutine，验证 supervisor 把峰值并发限制为 2，并为每个任务记录终态和结果。

## 环境与版本

- Python 3.11–3.13，标准库 `asyncio`；
- `AsyncSupervisor(concurrency=2)`；无网络/API key；
- 证据上限 `L1_MECHANISM`。

## 环境准备

```bash
uv sync --locked --all-groups --no-install-project
```

## 实验代码

```bash
PYTHONPATH=src uv run python examples/chapters/ch15_async.py
```

## 实际输出

```json
{"evidence_level":"L1_MECHANISM","fault":false,"observation":{"concurrency_limit":2,"max_active":2,"results":{"documents":"documents","metrics":"metrics","policy":"policy"},"states":{"documents":"SUCCEEDED","metrics":"SUCCEEDED","policy":"SUCCEEDED"},"winner":null},"passed":true,"scenario":"async"}
```

## 调试断点

在 semaphore 进入前、`states[name]=RUNNING`、finally 中 `active -= 1` 处观察 queued/running 数量。

## 验收标准

三个状态均 `SUCCEEDED`，结果无遗漏，`max_active=2` 且不超过 `concurrency_limit`。
