# Lab 20B — 最小 Coding Agent：错误补丁回滚｜故障注入

## 实验目标

注入能成功应用但行为错误的乘法补丁，验证子进程 oracle 失败后恢复原始文件，而不是保留污染状态。

## 环境与版本

- Python 3.11–3.13；真实临时 workspace/子进程；
- 无模型、容器/API key；
- 预期 `L3_CONTAINED`，不是 SWE-bench 成绩。

## 环境准备

```bash
uv sync --locked --all-groups --no-install-project
```

## 实验代码

```bash
PYTHONPATH=src uv run python examples/chapters/ch20_coding_minimal.py --fault
```

## 实际输出

```json
{"contained":true,"evidence_level":"L3_CONTAINED","fault":true,"observation":{"accepted":false,"changed_files":["calc.py"],"diff_sha256":"a3c8b1c13fcc56d0","returncode":1,"rolled_back":true,"verifier_stdout":"","workspace_restored":true},"passed":true,"scenario":"coding-minimal"}
```

## 调试断点

在子进程退出码、`accepted` 和 rollback write 后停下；重新读取文件确认仍是原始 `return a - b`。

## 验收标准

`accepted=false`、退出码非零、`rolled_back=true`、`workspace_restored=true`。补丁存在 diff 不能算成功。
