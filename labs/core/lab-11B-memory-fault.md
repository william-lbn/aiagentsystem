# Lab 11B — 等等级冲突与跨租户记忆污染｜故障注入

## 实验目标

在可信 `mem-zh=zh-CN` 旁注入同 tenant、同 authority/confidence 但值为 `en-US` 的记录，并加入 tenant B 的 `secret`。Last-write-wins 会给出虚假确定答案；正确 resolver 必须隔离跨租户并对同等级冲突 abstain。

## 环境与版本

Python 3.11–3.13，macOS/Linux、arm64/x86_64；无网络/API key，使用与 Lab 11A 相同的双时态 store。

## 环境准备

执行 `uv sync --locked --all-groups --no-install-project`；冲突和跨租户记忆是显式 fixture，实验不调用信息抽取模型。

## 实验代码

```bash
PYTHONPATH=src uv run python examples/chapters/ch11_memory.py --fault
```

## 实际输出

```json
{"contained":true,"evidence_level":"L3_CONTAINED","fault":true,"invariant_holds":true,"observation":{"candidates":["mem-conflict","mem-zh"],"quarantined":{"mem-conflict":"unresolved_equal_rank_conflict","mem-foreign":"tenant_mismatch","mem-zh":"unresolved_equal_rank_conflict"},"selected":null,"value":null},"oracle_detected":true,"passed":true,"scenario":"memory","system_detected":true}
```

## 验收标准

`selected/value` 均必须为空；跨租户与同租户冲突必须给出不同 reason。由于任何污染值都未投影给下游模型，证据为 L3。

## 调试断点

在 scope filter 确认 `mem-foreign` 不进入 candidates；在 rank comparator 确认两个合法记录完全同级；在 conflict gate 确认它比较 value 并返回 abstention。随后给新记录加入显式 `supersedes` 和更高 authority，设计受控消歧分支。

## Claim ceiling

实验没有测 memory extraction 模型。若接入小模型/OpenAI 抽取器，输出只能写 candidate queue；需另测 extraction precision、PII、否定和时间解析。
