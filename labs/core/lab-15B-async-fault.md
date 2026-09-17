# Lab 15B — 异步 Runtime：Winner 后取消 Loser｜故障注入

## 实验目标

运行 fast/slow 两个真实 task；首个成功结果出现后取消 slow，并等待其取消清理完成，证明没有未记账 orphan。

## 环境与版本

- Python 3.11–3.13，标准库 `asyncio`；
- 无远端请求/API key；取消只证明本地 task 生命周期；
- 预期 `L3_CONTAINED`。

## 环境准备

```bash
uv sync --locked --all-groups --no-install-project
```

## 实验代码

```bash
PYTHONPATH=src uv run python examples/chapters/ch15_async.py --fault
```

## 实际输出

```json
{"contained":true,"evidence_level":"L3_CONTAINED","fault":true,"observation":{"concurrency_limit":2,"max_active":2,"results":{"fast":"evidence"},"states":{"fast":"SUCCEEDED","slow":"CANCELLED"},"winner":"fast"},"passed":true,"scenario":"async"}
```

## 调试断点

在 `asyncio.wait(FIRST_COMPLETED)`、`task.cancel()`、`CancelledError` 和 `gather(..., return_exceptions=True)` 处确认取消被观察。

## 验收标准

winner 为 fast，slow 终态为 `CANCELLED`，函数返回时所有 task 均 done。不得声称远端 effect 已撤销。
