# 附录 K：第五篇进阶问题参考答案

本附录回答第 27–28 章的问题。答案以可验证状态、权限和证据为中心；具体协议版本、身份设施、数据库与风险等级改变时，应重新证明对应不变量。

<a id="ch27"></a>

## 第27章答案：A2A 与互操作

**1. 为什么签名 Agent Card 仍不能授权一次具体任务？**

Card 签名最多证明某个主体发布了未被篡改的能力声明。它通常不绑定当前 principal、delegate、task ID、业务对象、scope、有效期或一次性 nonce，也不说明调用方已获资源所有者授权。单次委派还需经身份系统签发并在执行点验证；Card 和 delegation 分别处理“你声称提供什么”与“我获准让你为哪个对象做什么”。

**2. request ID、task ID、context ID 和 effect key 应怎样组合？**

Request ID 对一次 transport/API 请求去重；Task ID 标识可轮询、取消和恢复的工作单元；Context ID 将多轮消息/多个 Task 关联到同一协作上下文；effect key 标识业务副作用。一次 task 可接收多次 request，也可产生多个 effect；同一 effect 也可能被不同恢复 request 查询。应分别建唯一约束，并在 trace 中建立显式关联，不能让一个随机 ID 承担四种语义。

**3. 取消成功为什么不必然等于业务副作用已撤销？**

取消通常意味着服务端接受停止请求或 Task 进入 canceled 终态，但请求到达前已提交的支付、邮件、部署或外部事务可能不可逆。正确做法是记录 cancel acknowledgement、最后 durable step 与 effect receipt，查询真实外部状态，然后选择保留、补偿或人工处理；禁止从 Task 标签推断外部世界已回滚。

**4. 如何把本章 scoped L5 扩展为跨语言、跨 binding 互操作矩阵？**

锁定规范、每种官方 SDK/语言、生成代码和镜像；对 Python/Go/Java/JS/.NET 等 client/server 组合，分别运行 JSON-RPC、gRPC、HTTP+JSON 支持项。统一 fixture 与 verifier，覆盖 discovery、普通/stream send、get/list/cancel/subscribe、artifact、版本协商、错误映射和认证；保存双方 raw trace、Task store、effect log 与失败分类。只汇报实际运行的矩阵单元，unsupported 与 not-run 必须分开。

**5. 当远端返回 `COMPLETED` 而 artifact verifier 失败时，哪个状态才是本地事实？**

远端 Task 对远端而言已完成，但本地业务不能进入 VERIFIED/ACCEPTED。本地应保存两个事实：`remote_state=COMPLETED` 与 `local_verification=FAILED`，并记录 artifact digest、verifier version 和原因。是否请求远端修订、开启新 Task 或人工升级由业务策略决定；覆盖远端状态或直接把本地标成成功都会丢失证据。

<a id="ch28"></a>

## 第28章答案：Multi-Agent 调度

**1. 为什么给 Coder 增加 `sources.read` scope 仍不应允许它 claim Researcher 的任务？**

Scope 表示主体可执行某类能力，owner 表示该主体对某个 work order 的当前责任。若“拥有 scope”即可接管任意任务，宽权限 worker 可绕过调度、上下文投影和责任链。正确 claim 同时检查 authenticated identity、owner/lease、required scope、依赖、预算与状态；重新分配必须是可审计的独立状态转移。

**2. 多 Agent 在什么条件下必然比单 Agent 更慢？**

当任务关键路径不能并行，或节省的计算时间小于分解、上下文转换、队列、通信、冲突解决、join 和验证开销时，makespan 必然增加。共享单一速率限制、频繁读写同一 workspace、每一步都等待 supervisor、以及高度耦合的小任务，都是典型反例。应以相同模型调用/工具预算做消融，而不是比较不同资源配置。

**3. 如何证明 context projection 没有遗漏必要信息又没有泄露其他任务数据？**

先把每个 work order 的输入定义为 typed references 与 schema，用数据流/权限策略列出允许集合；负向测试放入其他租户 secret、兄弟任务 scratchpad 和恶意引用，确认无法读取。正向测试使用最小 fixture，证明 worker 可完成 contract。运行时记录实际解引用集合，与允许集合比较；必要性通过删除/扰动每类输入的消融实验验证。

**4. 为什么多数投票不能消除多个同源模型的相关错误？**

多数投票只有在错误近似独立且单体正确率超过随机时才稳定增益。同一基础模型、相同检索源、相似 prompt 和共享错误上下文会产生强相关偏差；多个 worker 可能一致复述同一错误。应引入来源多样性、独立工具/环境 observation、异构 verifier、对抗测试和校准，而不是把三次一致当成事实证明。

**5. 怎样把本章 L1/L3 调度实验升级为真实模型团队的可复现实验？**

固定任务集、输入 snapshot、模型/provider/version、prompt、tool/sandbox、拓扑、并行度、token/tool/时间预算、重试和随机设置；同时运行单 Agent、相同模型 manager、handoff/DAG 等基线。保存逐步 trace、work order、context projection、artifact、费用与 evaluator 输出；重复运行并报告置信区间和失败类别。故障组还应注入 worker crash、恶意 artifact、陈旧 lease、预算竞态和 join 漏项，不能只展示一次成功对话。
