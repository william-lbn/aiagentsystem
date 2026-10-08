# Lab 32A — Prompt Injection、防护与最小权限｜正常路径

## 实验目标

验证两道相互独立的安全边界：检索/工具内容始终以 `UNTRUSTED_DATA` 类型进入 data channel；外部 effect 只有在 authenticated principal 的 `(tool, resource)` capability 精确匹配时才提交。正常路径允许 researcher 对 `invoice-7` 执行摘要。

## 环境与版本

- Python 3.11–3.13；标准库；x86_64/arm64；
- 无模型、网络、Docker 或 API key；固定 fixture 用于隔离 control plane；
- 真实模型只能提出 `ToolIntent`，无权修改 trust label、grant 或 `AuthorizationDecision`。

## 环境准备

```bash
python -m pip install uv==0.10.0
uv sync --locked --all-groups --no-install-project
```

## 实验代码

入口为 `examples/chapters/ch32_security.py`；核心为 `ContentEnvelope` 与 `CapabilityGateway`：

```python
instruction = ContentEnvelope("operator", "TRUSTED_INSTRUCTION", "text/plain", "Summarize invoice-7")
retrieved = ContentEnvelope("retrieval:web", "UNTRUSTED_DATA", "text/html", invoice)
context = gateway.assemble_context(instruction, [retrieved])
decision = gateway.authorize(
    "researcher",
    ToolIntent("documents.summarize", "invoice-7", {"style": "brief"}),
)
```

安全性不依赖在文本中搜索 `ignore policy`；即使 data 内容是自然语言命令，它也不获得 capability。

## 执行步骤

```bash
PYTHONPATH=src uv run python examples/chapters/ch32_security.py
```

## 实际验证输出（本发布源码执行所得）

```json
{"channels":["instruction","data"],"authorization":"CAPABILITY_MATCH","effect_count":1,"secret_redacted":true,"evidence_level":"L1_MECHANISM"}
```

## 调试断点

- `ContentEnvelope.__post_init__`：拒绝未知 trust label；
- `assemble_context`：确认 instruction/data channel 不可由检索内容互换；
- `authorize`：匹配 principal、tool 与 resource 三者；
- audit append 前：arguments 中 token/secret 已递归脱敏。

## 验收标准

退出码 0；channels 严格为 `instruction,data`；正常 intent 返回 `CAPABILITY_MATCH`；effect count 恰为 1；审计无秘密。L1 不代表已经覆盖所有 prompt injection 变体。

## 生产迁移

Capability 应由服务身份/IAM/短期 token 产生，不放在 system prompt；工具 schema 应限制参数、资源 namespace、金额与次数；高风险 effect 增加人工审批和事务日志；浏览器/代码执行继续使用 OS/container sandbox 与 egress policy。模型层 guardrail 是附加检测器，不是授权根。
