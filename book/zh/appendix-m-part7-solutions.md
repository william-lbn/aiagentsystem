# 附录 M：第七篇进阶问题参考答案

本附录回答第 36–40 章问题。答案强调 artifact identity、训练数据因果边界、实时控制、自我改进分权与端到端证据；它们不是唯一实现，但替代方案必须保留同等强度的不变量。

<a id="ch36"></a>

## 第36章答案：部署工程

**1. 为什么 digest-pinned base 仍不足以证明最终 image 可复现？**

它只固定一个输入。COPY 的源码、依赖锁、包仓库内容、构建器版本、构建参数、平台、网络下载、时间戳和生成工具都能改变最终字节。可信声明需要 final digest、完整/足够的 provenance 和 clean rebuild 结果；若无法字节复现，应明确 semantic equivalence 与不可复现字段。

**2. arm64 与 amd64 同 tag 时，哪些证据必须分平台保存？**

各自的 manifest/config/layer digest、base image、native wheel/library、SBOM、漏洞扫描、build provenance、测试输出、运行时版本和性能结果。Image index digest只证明集合身份，不能说明每个平台实现已执行同一测试。平台无关的 source/task/verifier manifest可共享。

**3. liveness 与 readiness 混用为什么会制造重启风暴或错误放流？**

短暂数据库/模型依赖故障通常应使 readiness false，停止新流量但保留进程恢复；若 liveness 也失败，orchestrator 会不断重启，加剧连接/迁移压力。反之只测进程/TCP 存活会让失去 queue、checkpoint 或 tool 权限的实例继续接任务。Startup probe 又用于慢初始化，三者回答不同问题。

**4. 为什么代码 rollback 不能等价为业务 effect rollback？**

旧代码恢复不会撤销已发邮件、扣款、merge、删除或机器人动作。Rollback 只改变后续执行版本；历史 effect 保持 COMMITTED/UNKNOWN，并需要查询、补偿或人工处理。若新旧版本使用不同 effect key/schema，回滚甚至会增加重复风险。

**5. 如何把本章 L1/L3 preflight 升级为可审计的真实发布证据？**

在干净、锁定 builder 中为 amd64/arm64 构建；生成每平台 digest、SBOM 与 SLSA provenance；签名并推 registry；由独立 job 验证签名/subject/inputs；在各平台拉取 digest 启动非 root/只读容器，从外部执行 health/API/restart/effect smoke；保存 raw logs、manifests 和 failure runs，再做 canary/rollback 演练。

<a id="ch37"></a>

## 第37章答案：Post-training

**1. 为什么 verified success trajectory 仍不能直接作为全部训练数据？**

它可能只覆盖当前策略容易到达的状态，造成 selection bias；大量相似成功会压过关键失败；其中可能含敏感数据、偶然捷径或高成本路径。训练还需要代表性采样、失败/拒绝/恢复轨迹、许可与隐私处理，以及与 eval 的组/时间隔离。Verifier 通过是必要标签，不是充分的数据设计。

**2. DPO 简化了什么，又没有解决什么？**

DPO 将特定 KL 约束的偏好优化重参数化为 policy/reference log-ratio 的分类式目标，避免单独拟合 reward model 并运行传统在线 RL。它不保证偏好标签正确，不消除 self-bias、数据污染、分布外行为、reward misspecification、安全约束或独立评测需求。

**3. 为什么按行随机切分特别容易高估 Agent 泛化？**

轨迹记录常按 repo、用户、模板、事故、网站状态或派生生成相关。同一问题的改写/中间轨迹跨 split 后，模型可记住结构或答案。应先按因果相关单元聚组，必要时加入时间切分和 semantic duplicate audit，再在组层分配 split。

**4. 如何把安全约束从 reward average 中分离出来？**

把权限、危险 effect、secret exposure、tenant 泄露等定义为 zero-tolerance/hard gate；只有通过 hard gates 的 run 才计算质量/成本软目标。训练可使用 constrained optimization、拒绝/负例和独立 policy verifier；发布报告各维度与 slice，不允许一万个流畅回答抵消一次未经授权转账。

**5. 怎样设计一次不泄露 API key、且结果可审计的真实模型训练实验？**

数据去标识并版本化 manifest；key 仅从 secret manager/环境注入，禁止进入 JSONL、命令回显和 trace；锁 base model/provider、训练配置、代码和预算；保存 provider job/model IDs、usage、状态和真实输出；在隔离 holdout 上由独立 verifier 重复评测并报告失败/区间。使用本地模型时额外保存 weight/quantization/runtime/hardware digest。

<a id="ch38"></a>

## 第38章答案：实时多模态

**1. 为什么 ASR partial 不能直接视为用户最终指令？**

Partial 会随后续音频被替换，边界、否定词和实体尤其易改变；VAD 也可能尚未判定 turn 结束。它可用于检索预取或可丢弃计算，但高风险 intent 应等待 final/stability、显式确认和 capability gate。否则“不要删除”早期可能暂时变成“删除”。

**2. event time、ingest time 与 sequence 各解决什么问题？**

Event time描述源端发生时刻，用于跨流对齐；ingest time描述系统收到时刻，用于网络/排队延迟；sequence给单一 producer/session 的离散顺序和缺口检测。三者都不能单独提供全局因果顺序，跨时钟还需 offset/uncertainty、watermark 或逻辑时钟。

**3. epoch fencing 比一个 `cancelled` 布尔值强在哪里？**

布尔值可能被新 turn 清零，旧异步 completion 随后误提交。每次修订/打断递增 epoch，effect 保存 started epoch，commit 必须等于 active epoch；任意旧 generation 都自然失效。它还能区分多次连续打断，而不依赖回调到达顺序。

**4. 何时 `STALE_DROPPED` 不足，必须进入 UNKNOWN？**

当 completion 只是响应而底层 effect 可能已经在远端/物理世界提交时，丢响应不能撤销事实。必须持久化 UNKNOWN，按 key 查询 provider、actuator或传感器；若不可观察则人工处置。只有能证明 effect 尚未提交的本地结果才可安全丢弃。

**5. 如何把本章实验升级成真实 Realtime/机器人证据而不夸大结论？**

锁 provider/model/transport/codec 或机器人固件，预注册网络和 workload；记录原始事件时间线、request/action IDs、cancel/actuator/sensor receipts；多次注入 barge-in、乱序、断线和 late completion；报告 latency/jitter/unsafe effect 与失败，不只给录屏。机器人还需独立 safety controller 与相应行业安全评估。

<a id="ch39"></a>

## 第39章答案：Self-Improving Agent

**1. 为什么 reflection 只能是候选 evidence，不能直接成为 truth？**

反思由同一概率模型生成，可能把相关性当因果、遗漏 effect、迎合提示或受攻击内容影响。它应链接原始 trace/环境 observation，由外部 verifier 或人类验证后才转成 skill/memory/test candidate；直接写入长期状态会累积并放大误诊。

**2. 配对评测比独立均值比较多控制了什么？**

Baseline 和 candidate 在同一 task/environment/预算上运行，task 难度差异被配对抵消，可直接观察每题改善/退化和高风险 slice。独立样本均值可能因抽到不同任务而改变。配对仍不控制 provider 时间漂移，最好交错/随机顺序并重复。

**3. 为什么 hard safety regression 不能被平均成功率抵消？**

安全损失通常非线性且不可逆，组织的 risk appetite 也不是“多答对几题就允许一次越权”。将其纳入加权平均会让权重选择掩盖灾难性行为。应先满足权限/危险 effect/tenant/secret 等 constraints，再在可行候选中优化质量和成本。

**4. Canary rollback 后还可能剩下哪些未解决状态？**

已产生的外部 effect、写入的新 schema/checkpoint、cache/memory、发给用户的内容、训练数据污染和跨区域 stale config 都不会因 active pointer 回退自动消失。必须逐类 reconciliation、compensation、migration rollback、cache invalidation、通知与 incident review。

**5. 如何防止自动优化器通过反复试验过拟合 holdout？**

限制试验预算并预注册 primary metric/stop rule；将开发 eval 与隐藏 final holdout 分开；周期性刷新时间外任务；记录所有 candidate 而非只留赢家；使用 nested evaluation、统计修正和真实 canary；candidate/proposer 无权读取或修改 final tasks/verifier。

<a id="ch40"></a>

## 第40章答案：端到端 Capstone

**1. 为什么 `COMPLETED` 必须是多个事实的合取而非一个状态字段？**

字段可被错误代码或模型写入，本身不证明权限、effect、环境结果和 trace。完成必须由独立 verifier 重新读取 approval/capability、provider receipt/query、终态、预算与证据完整性。任何 hard check 为假或未知，run 都应 quarantine/unknown。

**2. 两个 SQLite 已经分离时，本实验仍与真实远端 provider 有哪些差距？**

它们仍在同一主机/进程控制域，没有真实网络分区、认证、限流、最终一致、provider retention、时钟漂移、区域故障或协议升级。教学 provider 提供权威 lookup；现实 API 可能不提供，UNKNOWN 只能人工协调。SQLite L4 证明算法路径，不证明特定 SaaS。

**3. 为什么 approval 必须绑定 canonical intent digest？**

审批后模型/代码可能改变 operation、resource、金额或参数。Digest 将人看到的规范化动作与实际执行字节绑定；执行前重算不一致即拒绝。还应绑定 principal/tenant、policy/version、期限、次数和审批者，防止跨任务重放。

**4. L4 recovery 与 L5 external evidence 的差别是什么？**

L4 在明确受控故障模型内证明检测、containment 和恢复收敛；组件可以全是本地 reference implementation。L5 还要求 pinned 官方 SDK/真实 provider或环境、真实 fault、独立 verifier、raw artifact/digest 和第三方可复核步骤。L4 是机制恢复，L5 是外部真实性与互操作证据。

**5. 如何把本 Capstone 分阶段升级为可公开复核的生产 pilot？**

先用真实 OIDC、多实例 SQL/queue/object store 和容器 restart；再接一个有 sandbox/lookup 的低风险 provider，保留 effect key/receipt；加入真实模型只生成 proposal；运行 tenant/security/recovery/load eval；canary 限制权限与用户；生成脱敏 trace、SBOM/provenance、manifest 和独立报告；最后才扩大 effect/tenant，并持续 incident 回灌。
