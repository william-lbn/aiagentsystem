# 附录 G：第一篇问题参考答案

> 本附录把第一篇六章的参考答案与题目分离。答案用于校准概念和设计推理，不是唯一措辞；涉及系统设计的题目，应同时给出假设、反例、证据等级与未覆盖边界。

## 第一章：从生成模型到可治理行动系统 {#part1-solutions-ch01}

### 题一：JSON 与动作安全

JSON 只提供可解析的表示，至多再由 schema 约束局部形状。安全动作还需要：调用者/租户身份正确；工具和对象属于授权范围；审批绑定具体 run、action 与参数摘要；预算、时间窗和前置条件满足；副作用具有幂等或对账语义；结果由独立后置条件验证。任何一项缺失，结构正确的调用仍可能越权或产生错误效果。

### 题二：Workflow—Agent 连续体

应使用三个轴定位：策略自主性决定谁选下一步，行动权限决定爆炸半径，时间持续性决定恢复需求。固定 DAG + 模型分类节点是中等策略自主、有限权限、短/中持续；开放工具循环可能三轴都高。这个表示比“是不是 Agent”更能推导治理、评测和 Runtime 要求。

### 题三：三种完成语义

`COMMITTED` 说明某个工具调用已确定提交；`FINISHED` 说明 Runtime 到达其控制流终态；verified completion 说明业务后置条件经独立观测成立。工具可以提交错误对象，Runtime 也可能在 verifier 缺失时提前结束，因此前两者都不蕴含业务完成。

### 题四：最小审批对象

最小结构分为三组：身份字段 `approval_id`、`run_id`、`action_id`、`subject`；完整性字段 `canonical_args_sha256`、`policy_version`；时序字段 `decision`、`issued_at`、`expires_at`。执行前重新计算参数摘要并比较当前 state version。若只绑定 action name 或布尔批准，攻击者/竞态可在批准后替换 service、tenant 或参数，形成 TOCTOU。

### 题五：证据等级实验

L2：独立 oracle 发现未授权效果，但 SUT 没检测或阻断。L3：同一故障真正到达执行入口，SUT 检测并保持效果数为零。L4：在 L3 基础上，系统通过新审批、重试、补偿或对账最终恢复业务后置条件。实验必须分别记录 `oracle_detected/system_detected/contained/recovered/invariant_holds`，不能由场景名推断。

## 第二章：概率生成与结构化决策 {#part1-solutions-ch02}

### 题一：零温度与确定性

零温度通常选择最高概率 token，却不固定服务端模型快照、浮点归约、批处理、并行 kernel、tokenizer 或 tie-breaking。提供方升级和输入序列化也会改变结果。因此测试应验证结构合同、动作不变量和任务分布指标，而不是把相同文本作为跨环境保证。

### 题二：Schema 能力边界

Schema 能证明字段存在、局部类型、枚举、范围和判别分支等“表示性质”；它不能证明 service 属于当前租户、变更窗口有效、工具真实存在、调用者获权、动作会成功或结果可信。这些分别属于目录解析、策略、执行和验证层。

### 题三：合同漂移测试

从一个 canonical tool contract 同时生成/检查 provider schema 与本地函数签名；对每个必填字段、额外字段、类型、默认值和枚举做双向 golden test。故意把本地 `window_minutes:int` 改为 `str` 或删除必填字段，CI 必须在任何真实工具执行前失败，并输出具体 diff。

### 题四：公共决策证据

私有思维链不是稳定协议，可能敏感且无法保证忠实解释。替代证据包括：输入/上下文 manifest 摘要、模型和 schema 版本、候选/选中动作、结构化理由码、policy decision、工具 call/result identity、外部 receipt、verifier 结果、成本和时间。它们直接对应可审计边界。

### 题五：真实 OpenAI 证据包

从环境变量读取 key，输出中绝不包含 secret。记录运行 UTC 时间、SDK 与模型标识、请求 ID、输入 fixture/hash、tool schema/hash、采样参数、原始 response item 的脱敏副本、本地 validation、成本/usage、最终 oracle 和退出码。标记为 external/provider run，并与离线 Core Lab 分目录、分证据等级报告。

## 第三章：受治理的上下文视图 {#part1-solutions-ch03}

### 题一：窗口为何不解决选择

更大窗口只扩大容量，不保证检索召回、证据时效、来源可信、指令不冲突或模型有效利用。噪声和位置效应会使更多 token 降低表现，成本和延迟也增加。Context Engineering 解决的是“什么以何种权威在何时进入模型”，不是单纯装箱。

### 题二：为什么不能压成相似度

租户和指令信任是硬安全约束，违反时必须拒绝；相关性、时效性和权威性是在合法集合内的软排序信号。把它们压成一个分数，会允许极高相关性的跨租户秘密或恶意指令抵消安全惩罚。

### 题三：Mandatory 超预算

静默截断会让模型在缺 policy 或当前任务状态时继续，产生不可解释的策略变化。正确结果是 `CONTEXT_INFEASIBLE`：换更大窗口、结构化压缩非关键字段、拆分任务或升级人工，并记录哪些强制项导致不可行。

### 题四：摘要完整性

对金额、否定、时间、身份和审批状态使用结构化抽取与原值保留；摘要附 source IDs/digests 与覆盖范围；由独立规则比较关键字段；抽样人工审计；在下游引用时可回到原文。摘要不能覆盖原始证据，且需要版本与失效条件。

### 题五：Context ablation

建立任务质量与安全双指标：verified completion、证据引用准确率、工具调用成本，以及 cross-tenant exposure、untrusted instruction following、mandatory omission。分别移除 provenance gate、tenant gate、freshness、reranker 和 compaction，在相同任务/攻击种子上重复；任何质量提升若伴随硬边界泄漏都不可接受。

## 第四章：类型化消息与轨迹 {#part1-solutions-ch04}

### 题一：Role 不足以关联结果

`role=tool` 只说明发送主体类别。并行、重试和重复投递时可能有多个同名工具调用，必须用稳定 call ID 指向唯一未决调用，并验证 tool name/类型。否则到达顺序变化就会把观测配错。

### 题二：两类身份

Provider response ID 用于在提供方 API 中继续对话、诊断计费或追踪请求；本地 canonical item ID 用于跨 provider、跨重试、持久化和审计。前者生命周期与供应商绑定，后者由应用控制。应保存映射，但不能让本地恢复完全依赖远端对象仍存在。

### 题三：流式执行边界

文本 delta 可展示，但工具参数只有在 provider 宣告 item 完成、JSON/schema/semantic validation 通过、action intent 持久化和授权成立后才能执行。任何增量字段到达都不应触发部分副作用。

### 题四：Append-only 与防篡改

Append-only 规定应用语义上不修改旧事件，却不能阻止管理员或磁盘攻击者重写文件。还需要 hash chain/签名、不可变存储、可信时间、访问控制、备份和定期验证；同时处理敏感数据删除与审计保留的冲突。

### 题五：无思维链审计

保存结构化输入摘要、context manifest、候选/选中动作、理由码、策略决策、tool call/result、观察、verifier 和状态转移。这样的 action-observation trace 足以判断“做了什么、依据什么外部事实、是否获权、是否完成”，且比自然语言自我解释更可检验。

## 第五章：可执行规划与混合控制 {#part1-solutions-ch05}

### 题一：四个概念

Plan 是具体实例的动作结构；policy 是从状态/观察到动作的规则；workflow 是预定义控制图；schedule 是把可行步骤安排到时间和资源。一个 plan 可以由 policy 产生、嵌入 workflow，再由 scheduler 执行，四者不能互换。

### 题二：拓扑序为何不充分

拓扑序只证明依赖图无环且依赖可排序。步骤仍可能引用缺失能力、无权限对象、冲突资源、过期前提、超预算动作或错误后置条件。执行还需动态 precondition、授权、effect semantics 和 verification。

### 题三：不可解识别

评测应把任务分为可解/不可解并测 abstention precision/recall：可解任务完成率与不可解任务正确拒绝率同时报告。盲目尝试不可解任务会增加成本和副作用；准确地请求缺失能力或人工信息是一种合格决策，不应算作普通失败。

### 题四：局部或全部重规划

若变化只影响尚未执行的局部子图、上游观测仍新鲜且已提交效果保持有效，可从受影响节点局部修复。若目标、身份、policy、关键世界版本或共享假设变化，必须使整份 plan 失效。已执行副作用不通过“重规划”撤销，而由补偿/对账处理。

### 题五：Planner—Verifier 共偏差

使用不同信息源和实现路径的 verifier；高风险后置条件由确定性外部查询或人审；对 evaluator 做对抗与盲测；保留失败反例；禁止 planner 自己生成唯一验收文本。评测同时看最终状态与轨迹约束，避免双方共享语言幻觉。

## 第六章：可恢复状态与轨迹 {#part1-solutions-ch06}

### 题一：三者权威边界

Checkpoint 是某事件位置的恢复快照；trajectory 是发生顺序及其证据；memory 是供当前或未来策略读取的信息资产。控制恢复以 state/event 为权威，memory 不能直接宣告动作已完成，checkpoint 也不能替代外部效果事实。

### 题二：CAS 与旧 Worker

CAS 只在同一个 checkpoint store 的条件写上拒绝旧版本。租约过期 worker 如果仍持有数据库或云 API 凭据，可能绕过 store 产生副作用。需将单调 fencing token 传到工具网关/资源端，由资源端拒绝旧 epoch。

### 题三：为何不重新采样历史

重新采样可能选择不同工具、参数或自然语言，使恢复不再是原 run 的延续，并可能重复副作用。应重放已经持久化的决定和观测，在第一个未决定边界才重新调用模型；若输入或 policy 变更，则创建显式 revision。

### 题四：工具前持久化什么

至少持久化 run/state version、canonical action intent、call/action identity、规范化参数摘要、授权依据、幂等键、tool contract version 和 effect phase `PREPARED`。这样崩溃后可查询/对账，而不会把“无结果”误认为“未发送”。

### 题五：Compaction 等价验证

在 compaction offset 生成 snapshot 和此前事件的 digest；分别以完整日志重放与“snapshot + 后续日志”重放，比较所有权威 state 字段和 pending effects。做 schema 多版本 golden tests，并在删除旧段前验证 snapshot、digest 与备份可恢复；观察字段或缓存差异不能掩盖权威状态差异。
