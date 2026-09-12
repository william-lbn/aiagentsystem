# 附录 C：Agent Systems 故障模型与排错速查

| 故障 | 首先确认 | 禁止的第一反应 | 关键证据 |
|---|---|---|---|
| model/provider timeout | 是否产生 tool intent | 直接重跑整个任务 | trace/model request id |
| tool timeout | 外部效果是否可能已发生 | 无条件 retry | effect journal/idempotency key/actual state |
| process crash | 最后 durable checkpoint | 根据聊天历史猜状态 | checkpoint + journal |
| duplicate request | 幂等键与 owner/fencing | 执行第二次写操作 | request/effect id |
| prompt injection | 数据来源与权限边界 | 只增加一句 system prompt | policy decision + tool scope |
| multi-agent race | task ownership/version | 让两个 Agent 同时补写 | task DAG / optimistic version |
| disk full/corruption | fsync 是否成功、checksum | 删除日志继续运行 | storage error + checksum |

排错统一采用：现象 → 证据 → 假设 → 验证 → 根因 → 修复 → 正常/故障双轨回归。


## C.1 通用故障推理顺序

对所有章节都适用的基础故障集合包括 process crash、machine crash、timeout/partition、duplicate request、partial write、disk full/OOM 和 dependency failure；但正文只展开会改变该章不变量的 failure case。处理外部副作用时，排错顺序固定为：**最后一个可信 durable state → effect 是否可能已经发生 → 当前 observation 是否足够区分 COMMITTED / NOT_APPLIED / UNKNOWN → retry / continue / compensate / human escalation**。第一反应不应是“换模型”“改 prompt”或“直接重试”。

对 crash-sensitive 本地文件，至少区分 temp write、file fsync、atomic rename 与 parent-directory fsync；对远端副作用，如果本地进程在请求发出后、结果持久化前崩溃，则必须承认 ambiguous window。没有 idempotency key、外部查询或 reconciliation 机制时，系统不能诚实地声明 exactly-once。
