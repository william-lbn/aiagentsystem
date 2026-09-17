# Lab 22A — Conversation/Workspace 事件持久化｜正常路径

## 实验目标

以真实 SQLite 文件写入有序 `tool.started/tool.finished` 事件，关闭再重开 store，验证 conversation、workspace 和 sequence 绑定仍成立。

## 环境与版本

Python 3.11–3.13；标准库 SQLite；无需 OpenHands、容器、网络或 API key。

## 环境准备

```bash
source .venv/bin/activate
export PYTHONPATH=src
```

## 实验代码

```bash
python examples/chapters/ch22_openhands.py
```

实际输出：

```json
{"event_types":["tool.started","tool.finished"],"sequences":[1,2],"reopened_from_sqlite":true,"error":null,"evidence_level":"L1_MECHANISM","passed":true}
```

## 调试断点

在 `AgentEventStore.append` 的 workspace comparison、next sequence 与 commit 处停下；重开连接后观察 `events` 按 sequence 返回。

## 验收标准

退出码 0；sequence 恰为 1、2；事件类型和 payload 可重放。本实验不是 OpenHands SDK/Agent Server 互操作测试。
