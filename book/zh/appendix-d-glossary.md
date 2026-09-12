# 附录 D：术语、不变量与状态词典

- **Intent**：系统准备执行的外部动作；应在高风险副作用之前形成可持久化证据。
- **COMMITTED**：已有足够证据确认外部效果完成。
- **NOT_APPLIED**：已有足够证据确认效果未发生，可以按策略决定是否重试。
- **UNKNOWN**：现有证据不能判断外部效果；必须 reconciliation。
- **Checkpoint**：恢复长期执行所需的 durable run state。
- **Trajectory**：一次任务的可观察决策/动作/环境反馈序列。
- **Verifier**：独立于 Agent 自我叙述的任务判定机制。
- **Harness**：模型之外负责 context、tool、session、workspace、policy、sandbox、eval 等能力组合的运行环境。
- **MCP**：面向 context/tools/resources/prompts 的互操作协议边界。
- **A2A**：面向 Agent Card/task/artifact 与跨 Agent 协作的协议边界。
