# Lab 25A — Claim 与精确证据片段绑定｜正常路径

## 实验目标

读取真实来源文件，生成 URI/content SHA-256，把 claim 绑定到精确字符区间和 quote，形成可复核 evidence object。

## 环境与版本

Python 3.11–3.13；标准库文件与 `hashlib`；无需网络或模型。

## 环境准备

```bash
source .venv/bin/activate
export PYTHONPATH=src
```

## 实验代码

```bash
python examples/chapters/ch25_research_agent.py
```

实际输出：

```json
{"source_uri_scheme":"file","source_sha256":"7b60ca286b55c0ae","claim_bound":true,"quote":"independent verifier","span":[30,50],"evidence_level":"L1_MECHANISM","passed":true}
```

## 调试断点

在 `EvidenceBinder.ingest_file` 的 hash 和 `bind` 的 range/slice/quote comparison 停下；确认 report 使用同一 source digest。

## 验收标准

退出码 0；quote 与 source slice 逐字符相等；digest 存在；claim 被绑定。实验不证明 quote 语义一定蕴含 claim。
