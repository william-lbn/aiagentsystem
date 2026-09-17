# Lab 17A — 路径与能力 Gate：授权写入｜正常路径

## 实验目标

通过真实文件 I/O 验证只有持有 `fs.write/fs.read` capability 且目标解析到 workspace 内时才允许写入和读取。

## 环境与版本

- Python 3.11–3.13；macOS/Linux；ARM64/x86_64；
- `PathSandbox` 教学 gate；无 Docker/API key；
- 证据上限 `L1_MECHANISM`，不是 OS sandbox 认证。

## 环境准备

```bash
uv sync --locked --all-groups --no-install-project
```

## 实验代码

```bash
PYTHONPATH=src uv run python examples/chapters/ch17_sandbox.py
```

## 实际输出

```json
{"evidence_level":"L1_MECHANISM","fault":false,"observation":{"allowed":true,"content_sha256":"e67c6d223f7cc649","escaped_exists":false,"reason":null,"target":"artifacts/report.txt"},"passed":true,"scenario":"sandbox"}
```

## 调试断点

观察 capability gate、root/candidate resolve、`os.open` flags、`fsync` 与读回 digest。

## 验收标准

授权路径可读回相同内容，输出有 digest，workspace 外文件不存在。报告必须保留“工具 gate”边界。
