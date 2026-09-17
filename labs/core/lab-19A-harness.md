# Lab 19A — Plugin Harness：依赖 DAG 激活｜正常路径

## 实验目标

构造 `tools → loop → ui` 插件依赖图，真实调用 activate callbacks，验证确定性拓扑顺序和完整 active set。

## 环境与版本

- Python 3.11–3.13；`PluginRuntime`；
- 单进程 callback fixture，无动态第三方代码/API key；
- 证据上限 `L1_MECHANISM`。

## 环境准备

```bash
uv sync --locked --all-groups --no-install-project
```

## 实验代码

```bash
PYTHONPATH=src uv run python examples/chapters/ch19_harness.py
```

## 实际输出

```json
{"evidence_level":"L1_MECHANISM","fault":false,"observation":{"activated":["tools","loop","ui"],"active":["tools","loop","ui"],"disposed":[],"error":null,"order":["tools","loop","ui"],"status":"ACTIVE"},"passed":true,"scenario":"harness"}
```

## 调试断点

观察 identity/missing-dependency 校验、indegree、ready queue、每个 activate 返回的 handle 和最终 ready 状态。

## 验收标准

order、activated、active 三者完全相同且为 `tools,loop,ui`；无 dispose/error。
