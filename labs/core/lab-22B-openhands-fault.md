# Lab 22B — 跨 Workspace 事件写入阻断｜故障注入

## 实验目标

向绑定 `workspace-1` 的 conversation 注入 `workspace-2` 事件，证明 durable store 在 commit 前拒绝跨边界污染。

## 环境与版本

与 Lab 22A 相同。

## 环境准备

```bash
source .venv/bin/activate
export PYTHONPATH=src
```

## 实验代码

```bash
python examples/chapters/ch22_openhands.py --fault
```

实际输出：

```json
{"error":"workspace_binding_mismatch","event_types":[],"sequences":[],"cross_workspace_event_count":0,"evidence_level":"L3_CONTAINED","passed":true}
```

## 调试断点

停在 `AgentEventStore.append` 的 owner lookup；确认 workspace mismatch 时未计算/提交合法 sequence，重开数据库后 events 仍为空。

## 验收标准

退出码 0、错误类型匹配、事件数 0、`contained=true`。本实验不证明容器隔离、租户认证或网络重试语义。
