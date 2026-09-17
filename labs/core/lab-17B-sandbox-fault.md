# Lab 17B — 路径与能力 Gate：目录逃逸｜故障注入

## 实验目标

注入 `../escape.txt`，验证路径在 I/O 前被拒绝，并用独立文件存在性检查确认没有越界副作用。

## 环境与版本

- Python 3.11–3.13；真实临时目录；
- 无容器、网络或 API key；
- 预期 `L3_CONTAINED`，不外推 OS 隔离。

## 环境准备

```bash
uv sync --locked --all-groups --no-install-project
```

## 实验代码

```bash
PYTHONPATH=src uv run python examples/chapters/ch17_sandbox.py --fault
```

## 实际输出

```json
{"contained":true,"evidence_level":"L3_CONTAINED","fault":true,"observation":{"allowed":false,"content_sha256":null,"escaped_exists":false,"reason":"path_outside_workspace","target":"../escape.txt"},"passed":true,"scenario":"sandbox"}
```

## 调试断点

在 `_resolve` 的 parent containment 判定处断点，并在异常后检查 `root.parent/escape.txt`。

## 验收标准

原因必须为 `path_outside_workspace`，`escaped_exists=false`，`contained=true`；不能只检查“抛了异常”。
