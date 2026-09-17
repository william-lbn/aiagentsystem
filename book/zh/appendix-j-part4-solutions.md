# 附录 J：第四篇进阶问题参考答案

本附录回答第 21–26 章的问题。答案给出可审计的工程判断，不是唯一实现；若改变威胁模型、数据一致性或任务风险，应重新证明相应不变量。

<a id="ch21"></a>

## 第21章答案：Coding Harness

**1. 为什么保存完整聊天记录仍不能恢复一个 Coding Agent？**

聊天记录通常缺少 repo/workspace identity、baseline commit、dirty state、进程状态、权限版本、tool receipt 和测试 artifact。即使所有 token 都保留，恢复进程也无法证明文件是否已修改、某命令是否已经产生 effect，或当前代码是否仍对应当时的语境。可恢复状态必须存在模型上下文之外。

**2. 哪些事实允许模型压缩，哪些必须结构化保留？**

解释性讨论、重复日志和已被 artifact 覆盖的细节可生成摘要；目标、硬约束、失败测试、未解决风险、baseline、changed-file scope、pending approval、effect receipt 与 verifier 结果必须结构化保留。辅助摘要还要带 source pointer，不能成为这些事实的唯一副本。

**3. branch 与 worktree 为什么必须分别建模？**

Branch 表示决策/事实谱系，worktree 表示文件系统执行视图。一个 branch 可以更换 workspace，一个 workspace 也可能因实现错误被多个 branch 共享。只有分别建模并显式绑定，系统才能识别“逻辑分支正确但物理目录错误”的污染。

**4. 如何验证 compaction 没有改变任务语义？**

选择同一事件 offset，分别执行完整日志重放和“snapshot + 尾部事件”重放；比较目标、约束、failure set、artifact digest、pending action、state version 和允许的下一动作集合。文本相似度不能替代状态等价检查。

**5. 如何把本章 L1/L3 实验升级为可公开复核的 Coding Agent benchmark？**

锁定仓库 snapshot、issue 集、容器镜像、模型/provider、harness commit、预算和官方 evaluator；对每个 instance 保存 trajectory、patch、测试日志、资源、重试和人工干预。使用官方 scoring 汇总并发布失败分类；不能从少量精选成功案例计算“基准分数”。

<a id="ch22"></a>

## 第22章答案：远程 Agent Server

**1. 为什么 WebSocket 消息不能直接充当事件日志？**

WebSocket 提供连接上的传输顺序，却不天然提供 durable commit、跨重连 cursor、去重、保留期或服务重启后的重放。正确架构以 durable log 为事实源，WebSocket 只是该日志的投影。

**2. request ID 与 effect idempotency key 有什么不同？**

Request ID 去重同一 API/transport 请求；effect key 标识业务副作用，例如同一订单或部署动作。一个请求可能触发多个 effect，多个不同请求也可能指向同一业务 effect，因此两者不能混用。

**3. 容器状态为何不能代表 Agent 任务完成？**

容器 `Succeeded` 只说明进程退出码；它不证明目标 artifact 正确、外部 effect 完成、审批有效或 verifier 通过。Agent 完成必须由任务级终态和独立证据决定。

**4. Workspace lease 过期时应如何处置仍在运行的进程？**

先标记 lease expired 并阻止新 command，撤销短期 credential/egress，然后请求终止并记录 acknowledgement；对可能已发生的 effect 做 reconciliation。不能简单回收 metadata 后让旧进程继续拥有权限。

**5. 如何把本章实验升级为真实 OpenHands Agent Server 互操作测试？**

锁定 OpenHands SDK/server commit 与镜像，实际创建 conversation/workspace，执行工具并在客户端/服务端重启、断线重连和重复 request 下验证事件序列、artifact 与最终状态；原始日志、配置和失败输出都需归档。只有这些行为证据才能标为对应版本的 L5。

<a id="ch23"></a>

## 第23章答案：Browser / Computer Use Agent

**1. 为什么 DOM target 存在仍不足以授权点击？**

元素可能已不可见、被遮挡、属于错误 frame、语义与 label 不符，或页面 revision 已变化。授权还需绑定当前 observation、业务对象、风险策略和 postcondition，DOM 存在只解决 locator 的一部分。

**2. Revision 与 action idempotency 分别解决什么问题？**

Revision 防止把旧观察上的动作应用到新环境；idempotency 防止同一业务动作因重试重复发生。前者处理 optimistic concurrency，后者处理 duplicate execution，缺一不可。

**3. 如何为“提交订单”设计独立 postcondition？**

用订单系统返回的稳定 order ID 查询状态，并核对商品、数量、金额、币种、收货对象和请求 idempotency key；页面出现“成功”文字或按钮消失只能作为辅助 observation。

**4. 网页 prompt injection 应在哪些层被隔离？**

输入层标记网页为 untrusted data；模型上下文不把其内容提升为 developer instruction；tool/runtime 层只接受 typed action；policy 层独立授权；secret broker 和网络层限制能力；输出层扫描数据外传。只靠提示词防御不足。

**5. 报告 WebArena/OSWorld 分数时至少要公开哪些复现变量？**

Benchmark commit、站点/OS 镜像、task split、seed、账号初始状态、模型 snapshot/provider、agent/harness commit、action/observation space、预算、重试、人工干预、硬件、重复次数、官方 evaluator 原始输出和失败分类。

<a id="ch24"></a>

## 第24章答案：Data Agent

**1. 为什么 `startswith("select")` 不是只读安全边界？**

词法前缀不了解 SQL 方言、CTE、触发器、多语句、可写 UDF、pragma 或外部表。安全边界应由只读数据库角色/连接、authorizer、允许 schema 和资源策略强制。

**2. Query plan 和 result digest 分别提供什么证据？**

Plan 揭示访问路径、扫描/join 和潜在成本；digest 固定规范化结果，便于比较重放。Plan 不证明数值正确，digest 也不解释结果如何产生，二者需要和 SQL、参数、snapshot、verifier 一起保存。

**3. 如何防止截断结果被报告成完整总体？**

Result schema 显式携带 `truncated`、returned/estimated total、limit 和分页 token；报告生成器在 truncated 时禁止使用“全部/总计”等措辞，除非另有独立 count/aggregate 查询证明。

**4. Text-to-SQL 的 semantic error 应怎样评测？**

除执行成功和 exact SQL match 外，应在固定数据 snapshot 上比较 denotation，按指标、过滤、时间、join、粒度和单位标注错误；加入对抗 schema/同义指标与真实业务问题，并由领域规则或专家复核高风险样本。

**5. 在允许 Python 分析时还需增加哪些隔离和复现字段？**

需要进程/container identity、镜像 digest、Python/包 lock、CPU/memory/PID/time、mount、network policy、secret scope、输入/输出 artifact digest、随机种子和完整 stdout/stderr。Notebook 单元显示“已运行”不是充分证据。

<a id="ch25"></a>

## 第25章答案：Research Agent

**1. URL、quote 和 entailment 为什么是三个不同验证层级？**

URL 只定位资源；quote 证明某个版本包含这些字符；entailment 判断字符是否支持 claim。页面存在但未包含引文、引文真实但与结论无关，都是不同失败，必须分别检测。

**2. Claim coverage 为 100% 为什么仍可能错误？**

所有 claim 都有 citation，并不保证来源可靠、未过时、正确消歧或真正蕴含 claim，也不保证从多条证据得出的推断有效。Coverage 是必要的完整性指标，不是准确性证明。

**3. 如何处理网页更新导致的 citation drift？**

在获取时保存 retrieved-at、content digest、locator 和允许范围内的 snapshot/短摘录；复核时若 digest 变化则标记 source revision，尝试官方归档或新版本重绑定。不能静默用新页面解释旧报告。

**4. 研究截止日期应进入哪些数据结构？**

进入 research question、检索 query/filter、source metadata、claim validity interval、冲突判定和最终报告 header。仅在封面写日期不足以约束检索和合成。

**5. 怎样评测 Research Agent 而不只评价报告文风？**

使用带 gold/专家审计的 claim 集，分别测 retrieval recall、primary-source ratio、citation precision、entailment、temporal accuracy、conflict handling、unsupported-claim rate 和校准；保存完整 trajectory，让评价者定位失败阶段。

<a id="ch26"></a>

## 第26章答案：Graph Runtime

**1. 为什么 checkpoint 不能证明 external effect exactly-once？**

进程可能在外部系统完成 effect 后、写 checkpoint 前崩溃。恢复只看到旧 checkpoint，无法区分“没调用”和“调用成功但 receipt 丢失”。需要 intent、稳定 effect key、receipt 和外部 reconciliation。

**2. Topology signature 应覆盖哪些内容？**

至少覆盖节点/边 identity、node implementation/version、state schema/reducer、interrupt/resume schema、effect contract 和相关 policy version。仅 hash 节点名称无法识别语义变化。

**3. Interrupt 与普通函数 return 的语义差异是什么？**

Interrupt 要在 durable point 保存当前 state、待决 action 和恢复 schema，并允许进程/worker 释放后由新实例继续；普通 return 只结束当前调用栈，不自动提供外部输入关联和持久恢复。

**4. 并行 graph reducer 需要满足哪些代数性质？**

若分支完成顺序不可控，reducer 通常应满足结合律和交换律；在可能重复投递时还应幂等。不能满足时必须固定顺序、保存版本并对冲突显式序列化。

**5. 为什么 LangGraph、ADK、MAF 的现有 L5 证据不能互换？**

三组实验验证的对象不同：LangGraph 是 graph interrupt/checkpoint resume，ADK 是 session/event persistence，MAF 是 superstep/checkpoint 与 topology identity。依赖、存储与恢复入口也不同；一个框架的证据不能替另一个框架证明未运行的行为。
