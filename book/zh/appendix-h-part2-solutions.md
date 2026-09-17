# 附录 H：第二篇问题参考答案

> 本附录与第七至十三章的问题页分离。参考答案强调推理边界；读者的方案只要明确假设、风险、反例与证据，也可能得到不同但成立的结论。

## 第七章：工具契约与能力边界 {#part2-solutions-ch07}

### 题一：Schema 与租户

`additionalProperties=false` 只限制输入对象的字段集合。合法的 `invoice_id` 仍可能属于其他租户；只有目录查找后的 tenant/object ownership 与 subject policy 才能判权。

### 题二：何时拆工具

当步骤的风险、审批、可逆性、凭据或后置条件不同时应拆分。读取、创建草稿和最终提交有不同 effect semantics；若合成一个工具，Runtime 无法在调用前准确施加治理。

### 题三：工具选择评测

建立包含正常、相似工具、缺参数、不可解、注入和高风险任务的固定数据集；记录 expected tool/abstention、参数约束、unsafe effect，按模型与工具集版本多次运行，并保留 held-out set 防止描述优化过拟合。

### 题四：Artifact Preview

保留对象类型、来源、观察时间、内容 hash、大小、截断标记和最小诊断摘要；删除 secret、无关 PII、大段不可信文本与可通过 handle 读取的正文。preview 不能成为原始证据的替代品。

### 题五：两类 ID

Provider call ID 属于一次 API 响应生命周期；本地 action ID 要跨 provider、重试、审批、journal 和恢复稳定。两者应建立映射，不能合并，否则 provider 重建/重试会破坏本地 effect identity。

## 第八章：Tool Runtime 与副作用 {#part2-solutions-ch08}

### 题一：连接断开

连接断开只能证明客户端缺少响应。请求可能没发出、在路上、服务端处理中或已提交；这四种世界对客户端呈现相同 timeout，因此写操作必须进入 UNKNOWN。

### 题二：幂等键

Key 至少绑定 tenant、业务 operation、对象、canonical args digest 与 action identity；服务端定义作用域、参数冲突、保留期和查询接口。保留期必须覆盖最迟重试/对账窗口。

### 题三：最终一致下的 NOT_FOUND

查询副本可能尚未看到已提交效果。只有服务合同保证的强一致查询，或超过明确 settling window 后的权威查询，才可能支持 NOT_APPLIED；普通 NOT_FOUND 仍可能是 UNKNOWN。

### 题四：取消后的对账

取消停止的是本地等待/后续计划，不会撤回已经到达外部系统的请求。若 action 已进入发送窗口，reconciliation 必须继续，最终通知用户真实结果。

### 题五：补偿与回滚

Rollback 假设原事务未对外可见并能原子恢复；compensation 是新的业务动作，有自己的失败、费用和不可逆后果。退款不会抹去原付款记录，撤回邮件也无法保证收件人没阅读。

## 第九章：受治理检索 {#part2-solutions-ch09}

### 题一：先过滤后排序

租户/ACL 是不可违反的硬约束。若把它作为分数惩罚，高相关越权文档可能抵消惩罚并进入 top-k；先过滤可保证 ranking 只在合法 universe 内发生。

### 题二：长度归一化反例

法律条款、代码文件或长表格可能因必要上下文而长，长度归一化会压低其分数；非常短的导航/模板页反而被抬高。需要按文档类型、字段或 chunk 策略校准。

### 题三：Recall 与 Citation Precision

高 Recall@k 说明相关证据进入候选，不保证生成器引用正确；高 citation precision 说明已给引用支持 claim，不保证遗漏其他必要证据。二者分别测检索覆盖和回答支撑。

### 题四：拒答阈值

在有解/无解标注集上画 coverage-risk 或 precision-recall 曲线，按错误代价选阈值；再按语言、领域、租户规模和时间切片校准。阈值应与 index/model version 一起发布。

### 题五：索引不是权威

索引会延迟、压缩、分块和丢字段；权限/删除传播也可能滞后。Raw source + metadata manifest 才能重建和审计，索引只是可替换的访问路径。

## 第十章：混合与 Agentic RAG {#part2-solutions-ch10}

### 题一：异构分数

BM25、cosine 和图路径的量纲、范围及分布不同，固定加权在 corpus/model 更新后会漂移。RRF 以 rank 融合是无需标定的基线；若加权必须用标注集校准并持续监控。

### 题二：不信任 Adapter

Adapter 可能版本错配、缓存污染、权限配置错误或遭入侵。融合器掌握本次 authorized corpus，应独立拒绝未知/越权 ID，形成纵深防御。

### 题三：Evidence Gain

可定义为新增高权威 source span、未覆盖 claim 的减少、冲突解析或 nDCG/coverage 的边际提升。重复返回相同文档不计增益；连续若干轮低于阈值就停止。

### 题四：Reranker Provenance

保留每路原 rank/score/version、融合分数、rerank model/version/score、最终 rank 与 source metadata。Reranker 只能改变顺序，不能抹去来源或权限判定。

### 题五：安全消融

在相同 query/corpus/scope 上比较 dense-only 与 hybrid，除 Recall/nDCG 外报告跨租户暴露、无解拒答、注入跟随、过期引用和成本；任何质量增益若破坏硬边界都不能接受。

## 第十一章：长期记忆 {#part2-solutions-ch11}

### 题一：双时态

Valid time 回答事实在世界中何时成立；recorded time 回答系统何时获知。迟到事件、纠错和历史回放需要两者，否则系统无法重现当时“知道什么”。

### 题二：候选写入

模型抽取会误解指代、否定、时间和敏感属性。将其作为 candidate 可经过 schema、source authority、consent、冲突与人工确认；直接写事实会把一次概率错误变成长时污染。

### 题三：冲突拒答

等 authority/confidence 的矛盾记录没有确定的胜者。最近写入只反映到达顺序，不证明真实性；abstain 并请求澄清能避免随机选择影响未来动作。

### 题四：删除验证

验证权威 store、向量/关键词索引、cache、checkpoint/context snapshot、分析副本、备份策略和下游导出；保存 deletion request/receipt，但不要在 receipt 中复制被删敏感内容。

### 题五：分阶段评测

Construction 测写入 precision/recall、成本和延迟；retrieval 测 recall、freshness、conflict/leakage；generation 测任务成功、unsupported claim 和 token。端到端分数无法定位代价转移。

## 第十二章：Skills 与程序性记忆 {#part2-solutions-ch12}

### 题一：三类责任

Tool 定义原子动作合同；Workflow 定义控制图；Skill 打包适用条件、步骤知识、依赖和验收，可编译为 workflow 并调用 tools。Policy 独立决定这些能力是否可用。

### 题二：为何超集失败

静默取交集可能让依赖被删除权限的步骤以残缺状态运行，产生不可预测结果；显式失败迫使作者提供降级分支或请求新的审批，并保留清晰审计。

### 题三：Digest Binding

同名版本可能被覆盖或 registry 被污染。Checkpoint 绑定 digest，恢复时能确认步骤、脚本与 capability 合同完全相同；不一致则迁移或拒绝，而非隐式继续。

### 题四：检测过拟合

将成功轨迹按项目/时间/任务族划分 train/held-out，比较无 Skill 基线；测试扰动、缺工具、异常顺序和对抗输入，并测安全/成本。只在原轨迹回放成功不算迁移。

### 题五：供应链字段

至少包括 publisher/owner、source URI、version/commit、content hash/签名、依赖锁、runtime compatibility、capabilities、reviewer、eval result、expiry/revocation 和已知漏洞。

## 第十三章：MCP 协议边界 {#part2-solutions-ch13}

### 题一：无会话与应用状态

Stateless core 取消的是 transport/protocol 隐式会话依赖。Server 仍可把状态存入数据库并返回显式 handle，Client 在后续请求传回；这样状态可见、可鉴权、可扩缩容。

### 题二：Opaque Request State

requestState 表示 Server 对原操作的连续状态。Client 若修改或跨请求替换会造成 confused-deputy/replay；所以应原样回传，并由 Server 绑定 request identity、轮数、过期和所需输入集合。

### 题三：路由一致性的边界

Header/body 一致证明中间层按同一 version/method/name 路由，降低误分类和走私；它不证明调用者获权、参数业务合法、Server 可信或副作用完成。

### 题四：Tasks 与 Effect Journal

Tasks 描述长任务状态和交互；外部工具可能在 task worker 崩溃前已提交。没有 action identity、effect phase、receipt 和 reconciliation，恢复 task 仍会重复副作用。

### 题五：跨语言 L5

锁定官方 Python 与另一语言 SDK，分别互换 client/server，使用真实 HTTP；覆盖 discovery、tool/resource、MRTR、故障帧和版本协商；保存 wire、两侧版本/日志、server effect 与独立 verifier，并明确 OAuth/远程网络是否实际覆盖。
