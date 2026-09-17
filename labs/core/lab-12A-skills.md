# Lab 12A — Skill Manifest 编译与稳定 DAG｜正常路径

## 实验目标

把 `incident-triage@1.2.0` 的程序性知识真实编译为执行顺序和 capability grant；输出绑定 source/manifest digest，避免恢复时同名漂移。

## 环境与版本

Python 3.11–3.13，无网络/API key。Skill 三步：collect_logs、collect_metrics、correlate；最后一步依赖前两步。声明和 policy 均只含 `logs.read/metrics.read`。

## 环境准备

执行 `uv sync --locked --all-groups --no-install-project`；Skill source bytes、manifest 与 policy 都是版本化固定输入。

## 实验代码

```bash
PYTHONPATH=src uv run python examples/chapters/ch12_skills.py
```

## 实际输出

```json
{"evidence_level":"L1_MECHANISM","fault":false,"invariant_holds":true,"observation":{"capability_grant":["logs.read","metrics.read"],"error":null,"execution_order":["collect_logs","collect_metrics","correlate"],"manifest_sha256":"51f162ee2fda5ede","steps_executed":3},"passed":true,"scenario":"skills"}
```

## 调试断点

检查 semver/source digest、declared vs policy capability、dependency closure、indegree 和稳定 ready queue。

## 验收标准

PASS 要求顺序、grant 和 digest 均存在。单测还覆盖重复 step、缺依赖与 cycle 的拒绝路径。

## 扩展

把 compiled manifest digest 写入 checkpoint，再修改同名 Skill，确认恢复被阻止或要求显式 migration。真实脚本包还需 signature、dependency lock 和 sandbox。
