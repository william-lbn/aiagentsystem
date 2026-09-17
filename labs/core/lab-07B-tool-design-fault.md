# Lab 07B — 万能 Shell 与伪幂等合同｜故障注入

## 实验目标

一个名为 `shell` 的高影响接口以“Run anything”描述，申请 `*` capability，并把不可逆动作错误标为 idempotent。验收目标不是“发现文本可疑”，而是注册失败且执行计数保持零。

## 环境与版本

与 Lab 07A 相同；无网络/API key。独立 oracle 检查 validator reasons 和 `dispatched`，不依据场景名判定。

## 环境准备

执行 `uv sync --locked --all-groups --no-install-project`；不安装 shell 工具、不运行恶意命令，只将危险合同送入注册审计入口。

## 实验代码

```bash
PYTHONPATH=src uv run python examples/chapters/ch07_tool_design.py --fault
```

## 本仓库实际输出

```json
{"contained":true,"evidence_level":"L3_CONTAINED","fault":true,"invariant_holds":true,"observation":{"artifact":null,"contract":"shell","dispatched":false,"errors":["name_must_be_namespaced","description_missing_use_and_non_use_boundary","capability_scope_not_least_privilege","irreversible_effect_requires_reconciliation_contract"]},"oracle_detected":true,"passed":true,"scenario":"tool-design","system_detected":true}
```

## 验收标准

四项故障进入真实注册审计入口；SUT 给出具体 reason code；`dispatched=false` 且无 artifact/副作用。若只让测试脚本看见坏合同、Runtime 仍执行，则最多是 L2。

## 调试断点

- 删除 namespace gate：应观察第一项 reason 消失，但仍不得执行；
- 将 capability 改为最小权限：只应消除对应 reason；
- 将 effect 改为 `RECONCILABLE`：仍会因含混描述/名称失败；
- 只有全部 reason 被修复，才能进入正常路径。

## Claim ceiling

本实验不证明 OS sandbox 能阻止真实 shell，也不运行恶意命令。它证明工具目录在执行前拒绝了一类危险合同；真实 shell 安全需第十七章的容器/syscall/网络实验。
