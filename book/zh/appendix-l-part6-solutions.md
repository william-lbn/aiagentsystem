# 附录 L：第六篇进阶问题参考答案

本附录回答第 29–35 章问题。答案强调可证伪不变量、证据范围和工程取舍；它们不是唯一实现，但任何替代方案都应保存同等强度的事实边界。

<a id="ch29"></a>

## 第29章答案：Agent Evaluation

**1. 为什么最终答案正确仍可能必须判定 task 失败？**

Agent 的 task contract 不只有答案。它还约束允许的 effect、预算、数据来源、步骤和安全。如果系统用未授权数据、删除了资源、重复扣款或超过风险阈值后碰巧得到正确文本，outcome check 为真但 task conjunction 为假。把它计为成功会训练/选择出危险策略，并掩盖不可恢复路径。

**2. LLM-as-judge 在什么条件下可以参与、但不能独占 verdict？**

当性质是开放式质量、风格、解释清晰度或 rubric 匹配，并且 judge 已用 human/program anchors 校准、记录模型/提示版本、重复测量偏差时，它可提供 soft score。数据库 effect、代码 tests、权限、引用存在性和 tenant 隔离应由环境/程序 verifier 决定；judge 不得改写 hard gate，也不得把自己的自然语言判断当环境事实。

**3. 如何避免 Agent 修改自己的 tests/verifier？**

将被测 workspace 与 grader 隔离：tests/rubric 从只读、digest-locked 来源加载；Agent capability 不包含 grader path/secret；patch 只应用到候选 workspace；验证进程使用独立 identity/container；保存 base、patch、test 和 evaluator digests。若任务允许修改 tests，必须另有 hidden/independent tests 检查修改合理性。

**4. 为什么 task digest 一致仍不足以证明两次结果可比较？**

相同 task 仍可能在不同模型配置、tool、依赖、容器、账户状态、预算、harness 或 verifier 下执行。Digest 只证明一个对象字节相同，不证明其依赖环境和测量过程相同。完整可比性由下一章 manifest gate 建立。

**5. 如何把本章 L1/L3 实验升级为真实模型的统计性评测？**

固定任务集、环境、模型/provider、sampling、tool、预算和 verifier；运行预注册的多次 seed/repeat；保存每次 trajectory、effect、usage 与 verdict；报告 point estimate、区间、失败 taxonomy 和 cost/verified success；故障组加入错误自评、越权 effect、环境残留和 judge 偏差。只有实际 provider artifacts 存在才报告模型结果。

<a id="ch30"></a>

## 第30章答案：Benchmark

**1. 为什么两个系统都在同名 Docker tag 下运行仍可能不可比？**

Tag 是可变引用，registry 可让同名 tag 指向不同 image manifest；多架构 tag 还会在 ARM/x86 拉取不同镜像。应记录 OCI digest、平台、依赖 lock 和 runtime 配额，并验证容器内关键版本。显示名称相同不构成 content identity。

**2. `5/5` 为什么不能表述为真实成功率已知为 100%？**

它只是这五个选定实例的样本比例。即使假设独立同分布，Wilson 95% 区间仍很宽；此外还存在任务选择偏差、相关性、污染和 grader 错误。应写“5/5 verified on this manifest”，同时给区间和不外推范围。

**3. 如何区分模型失败、harness 失败和 broken task？**

保存分层状态：environment setup/reset、Agent trajectory/termination、artifact validity、evaluator execution 和 task audit。先用 gold/reference artifact 验证 harness/evaluator；环境无法启动归 infrastructure，Agent 未产有效 artifact 归 execution，reference 也无法通过或 spec 矛盾进入 broken-task review。不要把三类都编码成 score 0。

**4. 为什么公开网页自动化不能直接称为 WebArena 成绩？**

WebArena 类 benchmark 的任务依赖固定自托管站点、账户、后台数据、reset 和官方 evaluator。访问公开网站时内容/登录/时间/广告/策略均漂移，也未使用相同实例和 grader，因此只能称 browser smoke/task result，不能使用 benchmark 名称或分数。

**5. 怎样设计一次可审计的真实 SWE-bench smoke run？**

固定官方 harness commit、一个 instance/base commit、container digest、模型/scaffold/预算；先跑 gold patch 验证 evaluator；再生成 candidate patch；在隔离 grader 执行官方 tests；保存 patch、trajectory、test output、report、logs、usage 和全部 digests。preflight、gold-harness、model-run、evaluation 分开标状态，失败不自动反复挑选最好结果。

<a id="ch31"></a>

## 第31章答案：Observability

**1. 为什么 span tree 完整仍不足以证明外部 effect 状态？**

Span 表示本地观察到调用开始/返回，无法排除 response 丢失、provider 最终一致或未埋点 effect。外部事实需要 provider receipt/query、数据库状态或环境 observation。Trace 应链接 effect key/receipt，而不能把 `span.status=OK` 当业务提交证明。

**2. Hash chain 能防止哪些攻击，不能防止哪些攻击？**

在可信 chain head 下，它能检测单条修改、删除、插入和重排。若攻击者控制整个数据库并可重算从 genesis 开始的所有 hash，它不能证明历史真实性；也不提供保密、访问控制、可用性或备份。需将 signed head 周期锚定到独立 WORM/透明日志并保护 signing key。

**3. 为什么不能把 run_id 放进 Prometheus-style metric label？**

Run ID 近乎每次唯一，会造成无界 time-series cardinality、内存/索引成本和查询退化。Metrics 使用低基数维度如 model class、tool、outcome、tenant tier；单 run identity 留在 trace/log，必要时用 exemplar 链接。

**4. 如何在不保存完整 prompt 的情况下支持事故复核？**

保存 prompt/template/version、input/artifact digests、来源/provenance、token/size、redacted structured fields 和加密 artifact reference。只有最小授权人员在限定 retention/审计下读取原 artifact。对高敏数据可只保存可重放 fixture 的匿名化版本和不可逆 hash，但要承认这降低了语义复核能力。

**5. 怎样把本地 L3 篡改检测升级为跨 host 的审计证据？**

各 producer 对 event batch/chain head 签名，包含 host/workload identity、schema 与 sequence；collector 验签并写 append-only/WORM；定期将全局 Merkle root/签名锚定到独立账户；测试丢包、重放、乱序、host key rotation 和 collector compromise。发布 raw manifests、验证器和 failure evidence，而非只给截图。

<a id="ch32"></a>

## 第32章答案：安全与最小权限

**1. 为什么“模型识别出了恶意文本”不是充分的安全证明？**

它只证明某个攻击样本上的分类成功，不覆盖改写、多模态、间接来源、长上下文或适应性攻击。若识别失败时模型仍持有高权限，安全性完全依赖概率性判断。充分的 containment 需要即使模型提出恶意 intent，独立 capability/sandbox 仍阻断 effect。

**2. Trust label 为什么不能由 LLM 根据内容自行判断？**

攻击者可伪装语气、来源说明或引用，模型没有认证事实。Trust 应由通信身份、入口、签名、ACL 和数据流 provenance 决定；模型可输出风险信号，但不能把 data 升级为 authority。

**3. Capability 与传统工具 allowlist 有什么本质差异？**

“允许调用 SQL/tool”粒度过宽；capability 绑定 principal、action、resource、参数范围、次数/期限和可委派性。例如 `documents.summarize:invoice-7` 不蕴含读取 invoice-8 或 secrets。它把爆炸半径变成可验证合同，而非一个布尔工具开关。

**4. 人工 approval 如何避免变成橡皮图章？**

只在高风险/异常动作请求批准；显示规范化 action、resource、diff、金额、来源、policy 和 alternatives；隐藏模型说服性冗文；批准 receipt 绑定不可变 intent digest、审批者、期限和单次使用；测量 approval rate、拒绝、响应时间和 override incident，并通过抽样培训/复核。

**5. 如何把本章 L3 扩展到真实 browser/coding Agent 红队实验？**

在隔离网站/repo 注入网页、邮件、README、issue、代码注释、tool metadata、图片 OCR 和 memory attacks；运行真实模型多次；sandbox 限 filesystem/egress/credential；记录候选 intent、deny/allow、真实环境 effect 和 utility。主要指标是 unauthorized effect/secret exposure，而非模型是否复述攻击文本。

<a id="ch33"></a>

## 第33章答案：Effect Recovery

**1. 为什么 timeout 既不能视为失败，也不能视为成功？**

Timeout 只表示调用方在 deadline 内没收到确定 response；请求可能未发出、传输中、已处理或 response 丢失。成功/失败属于远端 effect 状态，必须通过 idempotency key 的权威 lookup/receipt 观察。在此之前状态只能是 UNKNOWN。

**2. 幂等键为什么必须绑定规范化业务语义？**

若 key 与 amount/recipient/operation 无关，误复用会把新业务意图当旧结果返回，造成漏单或错单。Provider/客户端都应校验参数 digest，冲突显式失败；key scope、TTL 和 tenant 也必须明确。

**3. Transactional outbox 解决了什么，又没解决什么？**

它把本地业务更新与“待发送消息”放在同一数据库 transaction，消除本地双写丢失。Relay 仍可能重复发送，consumer 需要 inbox/idempotency；对第三方 API 的最终 effect、receipt、取消和补偿仍需 reconciliation。

**4. Compensation 为什么不能覆盖原 effect 状态？**

补偿是新的业务动作：退款不抹去收费历史，回滚部署不等于原部署没发生。覆盖会丢失审计、金额和失败信息。应保留原 effect=COMMITTED，再创建关联 compensation intent，拥有自己的 key、receipt 和可能的 UNKNOWN。

**5. 如何把本章双 SQLite L4 升级为真实 provider 的恢复证据？**

选 provider sandbox，锁 API/SDK 版本；真实发送带 key 的 effect；在请求已到达后切断 response/kill worker；重启新进程查询 provider；恢复本地 receipt；再次提交同 intent；独立查询 provider 证明只有一条 effect。保存 raw provider IDs、脱敏 HTTP/trace、数据库 snapshot、时间线和 verifier，不保存 API key。

<a id="ch34"></a>

## 第34章答案：性能与成本

**1. 为什么 total latency 未超预算，单个 stage 超预算仍应失败？**

Stage SLO 可能来自下游 timeout、capacity 或交互体验合同；其他阶段偶然变快不能保证下一工作负载仍有余量。局部退化也提供可归因回归信号。若 stage budget 只是提示而非 hard contract，应在设计中明确，而不是事后用 total 掩盖。

**2. 并行执行为什么可能降 latency 却增加 cost 与错误？**

Wall time 取并行分支最大值，但 token/compute/tool cost 近似求和；共享 workspace/resource 产生冲突，fan-out 增加限流与重试，join 可能等待最慢分支，多个候选还需 verifier。只有可独立、可取消、可验证且关键路径受益的任务适合并行。

**3. Cache key 至少应包含哪些安全和版本维度？**

Tenant/principal 或授权域、规范化输入/task digest、模型/provider、prompt/template、tool/data snapshot、policy/schema/verifier version、locale/time-sensitive boundary；value 保存 provenance、freshness 与权限。高风险 mutable result 通常不跨 run 缓存。

**4. 如何公平比较本地小模型与远程强模型？**

固定 task、context、tool、runtime、verifier、预算上限、采样次数和硬件/服务区域；记录本地 compute/energy/折旧和远程 token/tool/网络成本；同时报告 verified quality、p50/p95/p99、throughput、failure、cost/verified success 和隐私/离线约束。不能只比单次延迟或标价。

**5. 怎样把本章微基准升级为可信的 p99/容量实验？**

预注册 workload/arrival distribution；专用/锁定 host/container；包含 warm/cold；用 open-loop 避免 coordinated omission；足够样本和重复批次；逐 stage trace queue/service/retry/cancel；逐步提升 load 到 SLO breach，报告 throughput-latency 曲线、置信区间和资源饱和；故障组注入 429/slow tool/cache miss。

<a id="ch35"></a>

## 第35章答案：生产 Agent API

**1. 为什么 request ID、run ID 与 idempotency key 不能混用？**

Request ID 标识一次 HTTP 尝试，重试应不同；run ID 标识 durable task；idempotency key 标识“这些创建尝试属于同一意图”。一 key 可对应多个 request 但只能一个 run。混用会让重试无法追踪、或把不同业务意图错误合并。

**2. 202 Accepted 与 Agent 成功之间还缺哪些状态？**

至少缺 queue/claim、RUNNING、checkpoint、WAITING_APPROVAL、tool/effect outcome、verification 和终态。202 只证明服务持久接受请求；即使 execution COMPLETED，也可能 verifier FAILED、effect UNKNOWN 或 artifact 被 QUARANTINED。

**3. 为什么对象授权必须下推到 storage query？**

先按全局 ID 读取再在应用层过滤，会通过 timing、cache、log、exception 或误序列化泄漏 foreign object。`WHERE tenant=? AND run_id=?` 或 RLS 令未授权对象在数据访问层就不可见，形成纵深隔离，并简化 absent/foreign 统一响应。

**4. 同一 idempotency key 改 payload 为什么应返回 conflict？**

静默返回旧 run 会让客户端以为新参数已执行，创建新 run 又破坏去重。保存规范化 payload digest 并返回 409 能暴露客户端 bug/攻击，保持 key 到业务意图的一对一含义。

**5. 如何把本章 loopback L3 升级为多实例、真实身份的隔离证据？**

使用真实 OIDC issuer/audience/key rotation、API gateway、多个服务实例、共享 PostgreSQL/RLS、queue/cache/artifact store；并发创建/读取不同 tenant；注入 token tamper/expiry、cache key 缺 tenant、worker crash、stream reconnect；从外部 client 验证 status/body/timing 不泄漏，内部 audit 可追踪；保存配置 digest、trace、DB policy 和独立 security test report。
