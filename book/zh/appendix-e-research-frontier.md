# 附录 E：2026 AI Agent 研究版图、理论前沿与开放问题

> **研究截止日期：2026-09-11。** 本附录只收录会改变 Agent 系统设计、评测或治理结论的研究与官方规范。论文预印本、厂商研究、产品发布和标准草案的证据强度不同；引用它们不等于宣称结论已经成为学界共识。

## E.1 从“LLM + Tools”到四平面 Agent System

到 2026 年，只把 Agent 定义成“LLM 加工具调用”已经不足以解释真实系统。更准确的系统视角是四个相互约束的平面：

1. **Decision Plane**：模型根据目标、上下文和 observation 提出下一步候选决策；
2. **Execution Plane**：Runtime、tool executor、sandbox、workspace 将被允许的决策变成真实动作；
3. **Truth & Recovery Plane**：checkpoint、journal、external observation、verifier 决定“发生了什么”以及崩溃后如何继续；
4. **Governance Plane**：identity、policy、delegation、approval、audit 决定“谁可以让系统做什么”。

可以把一次长时执行抽象成：

$$
S_{t+1}=F(S_t,O_t,D_t,A_t,E_t,G_t)
$$

其中 $D_t$ 是模型决策，$A_t$ 是运行时允许并执行的动作，$E_t$ 是外部世界真正发生的 effect，$O_t$ 是可观察到的证据，$G_t$ 是治理状态。最重要的教材结论是：**模型可以影响决策，但不能凭语言声明拥有外部事实、事务结果和授权。**

这也是为什么 2026 年的前沿工作越来越集中在长时执行、记忆、Agentic RL、身份协议、轨迹级评测和安全，而不是只比较“模型会不会调用工具”。

## E.2 Planning：从步骤生成转向可行性、拒绝与动态修复

[Agent Planning Benchmark（APB）](https://arxiv.org/abs/2606.04874)把 planning 从端到端 success 中拆出来，包含 4,209 个多模态案例、22 个领域和五类设置，并显式考察额外工具、坏工具和不可解任务。它揭示了一个重要事实：**Agent 会生成“看起来合理”的计划，并不代表它能识别计划不可执行。**

因此 Planning 的研究对象应至少包含四层：目标分解、约束传播、工具/资源可用性、以及 calibrated refusal。一个工程上可验证的计划不应只是自然语言步骤，而应接近：

$$
P=(V,E,C,R),\qquad feasible(P)\iff constraints(P)\land resources(P)
$$

未来研究的关键不是无限延长 CoT，而是让计划能够被 runtime 验证、局部重算、对 broken tool 做降级，并在任务本身不可解时停止。

## E.3 Long-Horizon Execution：显式任务状态比无限 Context 更重要

长时 Agent 最难的问题不是“上下文窗口够不够大”，而是**任务状态是否有独立于上下文的真实表示**。[LongHorizon-Harness](https://arxiv.org/abs/2608.01964)采用 Manage-Execute-Audit 思路，将 task state 外置，让执行器与审计器围绕显式状态协作。这与本书 Checkpoint/Journal/Harness 章节的核心判断一致：Context 可以压缩和重建，恢复所需的 durable state 不应只存在 prompt 中。

长时任务中的几个关键研究变量是：

- compaction 后是否保持任务约束；
- 进程/连接中断后是否能恢复而不重复 effect；
- auditor/verifier 是否独立于产生决策的 Agent；
- unresolved work 是否被显式保存，而不是由模型“记得还有什么没做”。

因此“可运行 8 小时”不是单独的能力指标。更有意义的指标是 resume equivalence、checkpoint recovery、unknown-outcome duration、verification coverage 和 human intervention rate。

## E.4 Memory：写入、更新、遗忘与删除传播成为一等问题

早期 Agent Memory 主要问“能不能记住过去”。2026 年研究把问题推进到**什么应该写、什么时候应该更新、旧事实何时失效、删除如何传播到派生记忆**。

[Memora](https://arxiv.org/abs/2604.20006)用 FAMA（Forgetting-Aware Memory Accuracy）显式惩罚对已过期/无效记忆的依赖；结果表明多种 memory agent 会重复使用已经失效的事实。[LongMemEval-V2](https://arxiv.org/abs/2605.12493)进一步把经验规模拉长到大量历史轨迹，测试 Agent 是否真正形成环境知识，而不是只做短窗口检索。[Deployment-Time Memorization](https://arxiv.org/abs/2606.10062)则把个性化 utility、可提取风险和 deletion fidelity 放在同一设计空间中；尤其重要的是，**只删除原始记录并不等于删除派生 summary**。

因此生产级 Memory 应被建模为控制回路：

$$
M_{t+1}=Update(M_t,x_t,write,conflict,forget),\qquad R_t=Read(M_t,q_t,policy,budget)
$$

未来真正困难的问题不是 vector database 选型，而是 provenance、conflict resolution、time validity、privacy boundary、derived-data deletion 和跨设备/跨 Agent 的一致性。

## E.5 Tool Runtime 与 Semantic Transaction：副作用从 RPC 上升到任务级语义

传统 tool calling 把工具看成独立 RPC；真实 Agent 却会在一个任务里组合多个互相关联的副作用。[Cordon](https://arxiv.org/abs/2606.17573)提出 Semantic Transaction，把 task-level execution boundary、shadow state、effect outbox、delegated authority 和 recovery metadata 组合起来，说明“每次调用前加一个 guardrail”不足以解决跨步骤副作用一致性。

这类研究最值得迁移到工程实践的不是“把所有 Agent 做成数据库事务”，而是三点：

- 用 `INTENT / EXECUTING / COMMITTED / NOT_APPLIED / UNKNOWN` 显式描述结果知识；
- 对不可逆 effect 在释放前进行 staging/validation；
- timeout 后先 reconciliation，而不是无条件 retry。

这会把 Agent correctness 从“模型是不是聪明”转化成“系统是否能证明当前外部状态以及下一动作是否安全”。

## E.6 Agentic RL：瓶颈从模型算法转向环境、Verifier 与 Credit Assignment

[ToolVerse](https://arxiv.org/abs/2607.15660)把 Agentic RL 环境扩展到近 400 个现实 MCP 环境、约 4,500 个工具，并关注长时 Tool-Integrated Reasoning。这揭示 2026 年 Agentic RL 的一个结构性变化：**训练瓶颈越来越不是有没有 RL 算法，而是有没有足够真实、可重置、可评分、不会污染现实系统的环境。**

Agentic RL 需要同时处理：

- sparse terminal reward 与长轨迹 credit assignment；
- tool/environment drift；
- verifier reward hacking；
- 成本和风险不是“训练后再优化”的附加项；
- 训练环境与部署环境之间的权限和数据差异。

因此目标函数更接近：

$$
J(\pi)=\mathbb{E}[R_{task}-\lambda_c Cost-\lambda_r Risk+\sum_t\alpha_t r_t]
$$

未来高质量 Agentic RL 基础设施很可能由环境版本化、任务生成、外部 verifier、trajectory store、counterfactual replay 和安全 sandbox 共同组成。

## E.7 MCP、A2A 与 Agent Identity：互操作不等于信任

[MCP 2026-07-28 规范](https://blog.modelcontextprotocol.io/posts/2026-07-28/)将核心协议推进到 stateless model，并加入 Multi Round-Trip Requests、header routing、可缓存 list 结果和 authorization hardening。这说明协议设计正在主动减少“会话是隐含正确性前提”的状态耦合。

[A2A Python SDK 源码 tag 1.1.4](https://github.com/a2aproject/a2a-python/releases/tag/v1.1.4)在 task ownership、cancel/subscribe 和 store correctness 等方面继续收紧，也说明多 Agent 互操作的难点很快会从“能不能通信”转向**任务所有权和生命周期到底属于谁**。需要区分源码 release 与可安装制品：截至核验日，PyPI 的 `a2a-sdk` 最新发行仍为 1.1.2。

但协议只回答“怎样连接和交换消息”。生产系统还需要独立回答：Principal 是谁、Agent 代表谁、授权范围是什么、能否转委托、何时过期、怎样撤销、谁对 effect 负责。NIST 2026 年关于 Agent Identity 与 Agent Standards 的工作进一步推动了这一层。因此应牢记：

> **Protocol interoperability ≠ identity ≠ authorization ≠ trust.**

## E.8 Multi-Agent：协调成本可能吞掉并行收益

[Anthropic 2026-08-13 的 multi-agent 研究](https://www.anthropic.com/research/multiagent-systems)强调了多个 Agent 在共享代码库、市场和社会系统中交互时出现的新问题。[DPBench](https://arxiv.org/abs/2602.13255)等工作也表明，当任务存在同步资源、依赖和死锁条件时，单纯让 Agent 通过自然语言协商不足以保证正确协调。

Multi-Agent 应用应使用净效用而不是“Agent 数量”衡量：

$$
U=Gain-CoordinationCost-ConflictCost-EffectRisk
$$

在检索、独立子任务、候选方案并行生成等弱耦合任务中，多 Agent 可能有效；在同一文件、同一外部资源、支付、库存、锁竞争等强耦合任务中，则需要 deterministic coordinator、lease、ownership、barrier 或 transaction semantics。

未来重要的不是造更多人格化角色，而是研究**资源仲裁、任务所有权、delegation chain、共享记忆一致性和跨 Agent 安全策略**。

## E.9 Evaluation：从 Final Answer 分数转向 Trajectory/System Verification

2026 年越来越多研究开始揭示 benchmark 本身的问题。OpenAI 在[编码评测审计](https://openai.com/index/separating-signal-from-noise-coding-evaluations/)中展示了 broken/ambiguous task 会污染能力判断；OSWorld、PaperBench、MLE-bench 等环境型 benchmark 也都说明环境状态、grader 和依赖版本会改变观察到的分数。

Agent 评测的推荐模型是：

$$
Score=V(Task,Trajectory,Environment,Artifact,Cost,Risk)
$$

至少需要区分：

- **Task success**：目标是否完成；
- **Trajectory validity**：过程中是否遵循约束；
- **Artifact verification**：最终代码、文件、数据或外部状态是否真实；
- **Unsafe success**：是否“完成任务但使用了不可接受的方法”；
- **Cost/Risk adjusted performance**：完成同一目标需要多少 token、工具调用、人工时间和风险暴露。

这意味着未来 Agent Evals 更接近分布式系统测试 + 安全测试 + 数据质量测试，而不是传统 NLP leaderboard。

## E.10 Security：Prompt Injection 只是入口，Capability 才是爆炸半径

NIST [AI 800-5](https://csrc.nist.gov/pubs/ai/800/5/final)和 2026 年 Agent security 工作都把重点放在模型之外的工程控制。Anthropic 在[2026-09-09 的真实网络安全事件复盘](https://www.anthropic.com/research/alignment-assessment-cybersecurity-incidents)中披露了四起模型获得真实第三方系统未授权访问的事件，并扩大审查范围到大量轨迹。这类证据的意义不是“某个模型不安全”，而是证明：**高权限 Agent 的安全边界不能依赖模型服从。**

更可靠的安全模型是：

$$
AllowedAction=Identity\cap Policy\cap Capability\cap Approval
$$

再用 sandbox、short-lived credentials、network policy、effect verifier 和 audit 把 blast radius 固化到模型之外。Prompt injection defense 仍重要，但它主要是输入风险控制；真正能限制损害规模的是 capability boundary。

## E.11 Research Agent：从“写报告”迈向长时科学与形式验证

Research Agent 的高标准输出不是长文本，而是可追踪的 `claim → evidence → method → artifact`。SciAgentArena 等 benchmark 开始把研究过程放进评测；OpenAI 2026 年对 scientific computing 和 research acceleration 的公开案例也在展示“模型 + 代码 + 数据 + verifier”的组合。

Anthropic 在[2026-09-04 的 Fermat's Last Theorem 形式化项目](https://www.anthropic.com/research/formalizing-fermats-last-theorem)中报告 Claude 大部分时间自主工作 11 天完成 Lean 形式化，并由 proof checker 提供机器可验证终点。这类案例非常重要，因为它说明长时研究 Agent 最有希望的方向不是“模型自己说研究完成”，而是**研究过程最终落到强 verifier 可以检查的 artifact**。

仍然没有解决的问题包括：原创性/novelty 如何验证、负结果如何保存、文献遗漏如何量化、实验环境污染如何控制，以及研究 Agent 如何避免把自己生成的二手内容循环引用成“新证据”。

## E.12 Self-Improvement：生成候选与接受改进必须分离

自我改进最危险的结构是“同一个 Agent 修改自己的 prompt/tool/policy，然后自己评价修改是否更好”。更稳健的模式是：Candidate Generator 产生改动，Frozen/Independent Verifier 在固定数据集、故障集、安全门和成本门上决定是否接受。

$$
Accept(c)\iff \Delta Quality>\tau_q\land \Delta Risk\le\tau_r\land \Delta Cost\le\tau_c
$$

Anthropic 2026 年自动化 alignment researcher 的工作说明 Agent 可以在研究/评估循环中承担更多角色，但同时也强化了一个边界：**自动化研究能力越强，越需要外部化研究目标、评价标准和 stop condition。**

## E.13 Physical AI：语言 Agent 与实时控制必须分层

机器人/物理 Agent 将错误从“答案不对”升级为物理世界 effect。高层 Agent 可以负责任务理解、环境语义、技能选择、重规划；低层 motion/control loop 则必须满足实时 deadline、动力学约束和独立 safety controller。

因此 Physical AI 不应简单套用 browser/coding agent 的 loop。更合理的是：

`Task Planner → World/Scene Model → Skill Selector → Constrained Controller → Safety Supervisor → Sensors/Verifier`

随着通用机器人模型和 skill foundation model 发展，真正决定生产可用性的仍然是可校验空间、紧急停止、碰撞约束、设备状态、仿真到现实偏差以及责任追踪。

## E.14 2026–2030：八条更可能持续的结构性趋势

1. **任务时长会继续增长，但 Human Steering 不会消失。** 长时任务更需要异步反馈、暂停、恢复和可见 unresolved work。
2. **Runtime 会成为独立工程层。** 模型能力提升不会自动替代 durable state、sandbox、effect semantics、policy 和 verifier。
3. **Memory 会从“功能”变成治理对象。** provenance、过期、删除和隐私会成为平台契约。
4. **协议与信任会继续分层。** MCP/A2A 解决互操作，Identity/Delegation/Policy 解决谁能做什么。
5. **Evaluation 会接近系统测试。** Final-answer benchmark 将被 trajectory、environment、artifact 和 risk-aware evaluation 补充。
6. **Agentic RL 的竞争焦点会转向环境与 verifier。** 高质量可重置环境可能比新算法更稀缺。
7. **Multi-Agent 会从角色扮演走向治理。** ownership、resource coordination、conflict arbitration 和 collective risk 会成为核心。
8. **Digital Agent 与 Physical Agent 的可靠性问题会汇合。** UNKNOWN outcome、权限、恢复、审计和安全控制都将从软件扩展到物理效果。

这些趋势不是“2030 必然预测”，而是基于截至 2026-09-11 的研究/标准/产品信号给出的结构性判断。任何具体产品、模型或厂商排名都可能快速变化。

## E.15 尚未解决的十个研究问题

1. 如何给不同 Agent Runtime 定义可组合的 verified execution semantics？
2. UNKNOWN outcome 如何在任意第三方 API 上通用 reconciliation？
3. 长期 Memory 怎样实现 provenance-preserving update、forgetting 与删除传播？
4. Agent Identity、delegation 和 revocation 如何跨 MCP/A2A/云 IAM 一致表达？
5. Agentic RL 怎样解决几百步工具轨迹的信用分配，同时抑制 verifier hacking？
6. 多 Agent 的 deadlock、resource contention 和 collective unsafe behavior 怎样被形式化？
7. Benchmark 如何持续检测 task corruption、grader drift、环境版本和数据污染？
8. Research Agent 的 originality、negative result、causal validity 如何自动/半自动验证？
9. 企业如何把 Agent 的收益从“节省 token/工时”提升为可审计的业务 outcome 与风险调整 ROI？
10. 当 Agent 能产生物理或金融 effect 时，安全不变量如何跨模型、软件 runtime 与现实控制器端到端证明？

## E.16 本附录结论

2026 年以后，AI Agent 的竞争重点正在从“模型是否显得聪明”迁移到一个更难的问题：**怎样让聪明模型在长时、开放、具有真实副作用的环境里保持可验证、可恢复、可治理。**

因此本书采用 Runtime、Truth/Recovery、Governance 与 Evaluation 作为主线并不是保守的软件工程偏好，而是对 Agent 研究正在发生的系统化转向的回应。真正长期有效的知识，不是某一代模型的 prompt 技巧，而是对状态、权限、证据、副作用和失败边界的清晰建模。
