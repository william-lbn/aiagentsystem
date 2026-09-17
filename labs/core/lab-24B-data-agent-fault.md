# Lab 24B — 数据库写入权限拒绝｜故障注入

## 实验目标

向只读 Data Agent 注入 `DELETE`，验证 mode=ro/query-only/authorizer 阻断，并用独立连接证明数据未变化。

## 环境与版本

与 Lab 24A 相同。

## 环境准备

```bash
source .venv/bin/activate
export PYTHONPATH=src
```

## 实验代码

```bash
python examples/chapters/ch24_data_agent.py --fault
```

实际输出：

```json
{"sql":"delete from invoices","error":"QueryRejected","verified_row_count":3,"result_sha256":null,"evidence_level":"L3_CONTAINED","passed":true}
```

## 调试断点

在 `ReadOnlyDataAgent._authorize` 和 `QueryRejected` 转换处停下；随后观察 verifier connection 的 `count(*)`，不要只接受 exception 作为证据。

## 验收标准

退出码 0、写入被系统检测、表中仍为 3 行、`contained=true`。字符串预检查不是本实验的安全边界。
