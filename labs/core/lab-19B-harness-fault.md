# Lab 19B — Plugin Harness：部分激活回滚｜故障注入

## 实验目标

让 UI 插件在真实 callback 中抛出异常，验证已激活的 loop/tools 被逆序 dispose，Harness 不发布部分 active 状态。

## 环境与版本

- Python 3.11–3.13；单进程 lifecycle fixture；
- 无网络/API key；
- 预期 `L3_CONTAINED`，不声称 dispose 失败恢复。

## 环境准备

```bash
uv sync --locked --all-groups --no-install-project
```

## 实验代码

```bash
PYTHONPATH=src uv run python examples/chapters/ch19_harness.py --fault
```

## 实际输出

```json
{"contained":true,"evidence_level":"L3_CONTAINED","fault":true,"observation":{"activated":["tools","loop"],"active":[],"disposed":["loop","tools"],"error":"activation_failed:ui:RuntimeError","order":["tools","loop","ui"],"status":"ROLLED_BACK"},"passed":true,"scenario":"harness"}
```

## 调试断点

在 UI activate 抛错点和 `reversed(tuple(handles))` 处观察 handle 集合；确认 ready 未发布。

## 验收标准

`status=ROLLED_BACK`、`active=[]`、dispose 顺序严格为 `loop,tools`，错误包含失败插件身份。
