# Lab 20A — 最小 Coding Agent：补丁通过独立验证｜正常路径

## 实验目标

对真实 `calc.py` 应用受范围约束的补丁，在隔离 Python 子进程执行两个行为断言，仅在退出码 0 时保留修改。

## 环境与版本

- Python 3.11–3.13；macOS/Linux；ARM64/x86_64；
- `CodingWorkspace`、真实文件、`subprocess.run`；
- 无模型、容器/API key；证据上限 `L1_MECHANISM`。

## 环境准备

```bash
uv sync --locked --all-groups --no-install-project
```

## 实验代码

```bash
PYTHONPATH=src uv run python examples/chapters/ch20_coding_minimal.py
```

## 实际输出

```json
{"evidence_level":"L1_MECHANISM","fault":false,"observation":{"accepted":true,"changed_files":["calc.py"],"diff_sha256":"bccfb8a58c315cd1","returncode":0,"rolled_back":false,"verifier_stdout":"2 passed","workspace_restored":false},"passed":true,"scenario":"coding-minimal"}
```

## 调试断点

观察 allowed-files gate、唯一 preimage、unified diff、最小子进程 env/cwd、returncode 与 accept 分支。

## 验收标准

`accepted=true`、`returncode=0`、stdout 为 `2 passed`、变更仅 `calc.py` 且不回滚。
