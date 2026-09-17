# Lab 25B — Citation Drift / Quote Mismatch 阻断｜故障注入

## 实验目标

给正确 source/span 注入过时 quote，验证 evidence binder 拒绝把漂移引用加入报告。

## 环境与版本

与 Lab 25A 相同。

## 环境准备

```bash
source .venv/bin/activate
export PYTHONPATH=src
```

## 实验代码

```bash
python examples/chapters/ch25_research_agent.py --fault
```

实际输出：

```json
{"source_sha256":"7b60ca286b55c0ae","claim_bound":false,"quote":null,"span":null,"error":"quote_mismatch","evidence_level":"L3_CONTAINED","passed":true}
```

## 调试断点

停在 `EvidenceBinder.bind` 的 `source.content[start:end]` 与 expected quote 比较；异常后确认没有构造 `VerifiedClaim`。

## 验收标准

退出码 0、`claim_bound=false`、`error=quote_mismatch`、`contained=true`。系统只阻断不一致引用，没有自动找到替代证据。
