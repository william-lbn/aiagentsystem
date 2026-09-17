# Lab 07A — 工具合同审计与内容寻址结果｜正常路径

## 实验目标

工具必须声明有界语义、最小 capability、risk/effect 和输出形状；大结果不直接占满模型上下文。本实验真实执行 contract validator 与 artifact store，不调用或伪装大模型。

## 环境与版本

- Python 3.11–3.13；macOS/Linux，arm64/x86_64；
- 运行 `uv sync --locked --all-groups --no-install-project`；
- 不需要网络、Docker、GPU 或 API key；
- SUT：`src/agentlab/knowledge_system.py::{validate_tool_contract,ArtifactStore}`；
- 入口：`examples/chapters/ch07_tool_design.py`。

## 环境准备

在仓库根目录执行 `uv sync --locked --all-groups --no-install-project`；后续命令均使用锁定环境，不读取任何 provider 密钥。

## 固定输入

`billing.invoice_read` 带明确 use/do-not-use 描述、对象 schema、`billing.invoice.read` capability、`READ_ONLY/PURE` 语义及 512-byte 内联上限。工具生成 1504-byte JSON。

## 实验代码

```bash
PYTHONPATH=src uv run python examples/chapters/ch07_tool_design.py
```

## 本仓库实际输出

```json
{"contained":false,"evidence_level":"L1_MECHANISM","fault":false,"invariant_holds":true,"observation":{"artifact":{"artifact_id":"sha256:cbb40bb0c9460ee7c9f1b7308870a50117af71a8134e6e12881c1e5eae409dca","bytes":1504,"preview_chars":120,"sha256":"cbb40bb0c9460ee7"},"contract":"billing.invoice_read","dispatched":true,"errors":[]},"passed":true,"scenario":"tool-design"}
```

## 调试断点

1. `validate_tool_contract`：确认所有 error gate 均为空；
2. `ArtifactStore.put`：观察 SHA-256 由真实 bytes 计算；
3. `course_scenarios.tool_design`：确认只有 validator 通过才将 `dispatched` 置真。

## 验收标准

退出码 0；`errors=[]`、`dispatched=true`、artifact bytes/hash 稳定。L1 只证明离线机制，不证明某个模型会选对工具。

## 深化实验

修改一字节 line item，验证 artifact ID 变化；重复写入相同 bytes，验证 ID 相同。再接入一个锁定版本的小模型或 OpenAI Responses tool calling，单独报告 tool-selection accuracy，不把 provider 结果混入本 lab。
