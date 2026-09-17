# Agent Harness：模型之外的系统产品

> **本章命题**：Harness 是把模型、上下文、工具、workspace、policy、审批、持久化、观测与 verifier 组合为可运行产品的宿主系统。一个更强模型无法补偿错误的生命周期、权限或回滚设计。

![Harness 的内核、适配器、插件与控制面](../../assets/diagrams/19-harness-architecture.svg)

## 问题背景与学习目标

真实 Agent 产品不是一个 SDK 调用：CLI/UI 接收任务，context manager 选择证据，model adapter 调用 provider，tool runtime 执行动作，workspace 管理文件，policy/approval 控制权限，checkpoint 恢复状态，trace/eval 判断质量。若这些部件通过隐式全局状态拼接，任何插件升级都可能改变权限或留下半激活资源。

本章目标是给出 Harness 的最小内核和端口；用依赖 DAG 管理插件；实现确定性激活和逆序回滚；区分业务插件与安全不可旁路的内核；设计兼容、生命周期、配置与证据合同。

## 核心概念与系统直觉

Harness 可用六个平面理解：交互面、决策面、执行面、状态面、治理面、证据面。插件不是任意代码片段，而是声明依赖、能力、配置 schema、生命周期 hook 和兼容版本的组件。

若插件依赖图 $G=(V,E)$ 无环，激活顺序是其确定性拓扑序；若第 $k$ 个插件失败，则已激活集合必须按逆拓扑顺序 dispose：

$$
activate(v_1),...,activate(v_{k-1}),fail(v_k)
\Rightarrow dispose(v_{k-1}),...,dispose(v_1)
$$

这与事务补偿类似，但 dispose 也可能失败，因此生产实现还要记录 cleanup debt。

## 原理与理论基础

Harness 的关键架构原则包括：ports/adapters 隔离 provider；capability-based dependency injection 防止组件获得全局权限；配置在启动前验证并生成不可变 snapshot；核心安全 gate 不允许普通插件绕过；所有 cross-component event 有稳定 schema 和版本。

核心不变量是：**插件只按已验证的无环依赖图确定性激活；部分激活失败时，所有已激活资源必须逆序回滚并留下可审计结果。** 这只覆盖 lifecycle，不代表插件本身安全或业务正确。

> **Invariant**: plugin activation follows a validated dependency DAG, and partial activation rolls back all acquired handles in reverse order.

## 关键机制与执行流程

![Harness 从 manifest 校验到激活、运行和失败回滚](../../assets/diagrams/19-harness-flow.svg)

1. 发现 manifest，验证唯一 identity、版本、schema、digest/signature；
2. 解析依赖和 capability request，拒绝缺失依赖、循环与越权；
3. 构造确定性拓扑序，冻结配置和 policy snapshot；
4. 逐个 activate，handle 只暴露声明的端口；
5. 全部成功后发布 runtime ready；
6. 中途失败时禁止接收任务，逆序 dispose 已激活 handle；
7. 运行期插件异常经 circuit breaker/bulkhead 隔离；
8. 升级采用 drain/checkpoint/migrate/canary/rollback，而非热替换共享状态。

## 从原理到实现

本书 `PluginRuntime` 先校验 identity、缺失依赖和 DAG，再以稳定名称排序：

```python
ready = sorted(name for name, degree in indegree.items() if degree == 0)
while ready:
    name = ready.pop(0)
    order.append(name)
    for child in sorted(edges[name]):
        indegree[child] -= 1
        if indegree[child] == 0:
            ready.append(child)
            ready.sort()
if len(order) != len(plugins):
    raise ValueError("plugin_dependency_cycle")
```

激活失败不保留“部分可用”假象：

```python
try:
    for name in order:
        handles[name] = plugins[name].activate()
except Exception as exc:
    for active_name in reversed(tuple(handles)):
        plugins[active_name].dispose(handles[active_name])
    return PluginRunReport("ROLLED_BACK", order, (), tuple(disposed), ...)
```

生产版本还应捕获每个 dispose 的独立错误、设置超时并将未清理资源送入 durable cleanup queue。

## 主流系统实现对照与源码阅读入口

| Harness | 公开边界 | 阅读方法 |
|---|---|---|
| [OpenAI Agents SDK](https://github.com/openai/openai-agents-python) | Agent/Runner/Tools/Handoffs/Guardrails/Sessions/HITL/Tracing | 追 Runner lifecycle、model/tool adapters 与 RunState，不把 SDK 等同完整宿主产品 |
| [OpenAI Codex CLI](https://github.com/openai/codex) | CLI、config、workspace、approval/sandbox 等公开 Rust 源码 | 追配置到执行权限和本地 artifact；不推断未公开托管服务 |
| [OpenHands SDK](https://github.com/OpenHands/software-agent-sdk) | Conversation/Agent/Tool/Workspace/Event/Server | 比较远程 workspace、resume 与 service boundary |
| [Google ADK](https://github.com/google/adk-python) | agents、workflow、runner/session、tool、telemetry/eval | 区分 framework extension 与部署控制面 |
| [LangGraph](https://github.com/langchain-ai/langgraph) | graph/checkpointer/interrupt/stream | 适合作为 orchestration port，不替代 sandbox/policy/effect journal |

## 设计方案与方法对比

| 架构 | 优点 | 风险 |
|---|---|---|
| 单体 Harness | 易调试、低延迟 | 升级耦合、故障域大 |
| 插件化单进程 | 可替换、组合快 | 插件同权限、崩溃共享 |
| 多进程/服务 | 隔离、独立扩缩 | 协议、延迟和一致性复杂 |
| Workflow engine 为骨架 | durable timer/retry 成熟 | 开放式模型循环需适配 |
| Event-driven | 弹性与审计 | 乱序、重复、最终一致 |

安全关键 policy、credential broker、effect journal 和 verifier 不应作为可被普通插件卸载的 optional feature。

## 可复现实验

### Lab 19A：确定性依赖激活

正常实验构造 `tools → loop → ui` 依赖 DAG，并执行真实 activate callbacks：

```bash
PYTHONPATH=src uv run python examples/chapters/ch19_harness.py
```

实际输出 `order=activated=active=[tools,loop,ui]`、`status=ACTIVE`，等级 `L1_MECHANISM`。

### Lab 19B：部分激活逆序回滚

```bash
PYTHONPATH=src uv run python examples/chapters/ch19_harness.py --fault
```

UI 激活抛出真实异常；实际输出 `status=ROLLED_BACK`、`active=[]`、`disposed=[loop,tools]`、错误定位 `activation_failed:ui:RuntimeError`，等级 `L3_CONTAINED`。见 [Lab 19A](../../../labs/core/lab-19A-harness.md) 与 [Lab 19B](../../../labs/core/lab-19B-harness-fault.md)。

**关键断点**：manifest 校验、ready queue、activate handle、异常点和 reverse dispose。**验收标准**：顺序确定、缺失/循环依赖拒绝、故障后无 active handle、dispose 严格逆序。

## 工程场景与系统设计

企业 Harness 可把 model provider、retriever 和 UI 做适配器，把 tool runtime、policy、effect journal 和 trace schema 放在稳定内核。每个 task 取得 immutable runtime snapshot，升级不改变正在运行任务的依赖；新版本先在固定 eval/fault suite 上 canary。

配置应分三类：可公开静态配置、secret reference、运行期 policy decision。禁止把 secret 填进通用 plugin config 后随 trace 序列化。插件输出必须经过 artifact registry/provenance 层再交给其他组件。

## 故障模型、失败模式与排错

- 重名插件/identity spoofing：name + publisher + digest/signature；
- 依赖循环/缺失：启动前 DAG 验证；
- 半激活：ready flag 只能在全成功后发布；
- dispose 失败：逐项记录并进入 cleanup debt；
- 隐式全局单例：用 scoped handle/capability 注入；
- schema 漂移：manifest/API/event version 与兼容测试；
- 插件绕过 policy：所有 effect 经过不可替换的内核 gate；
- 热升级破坏 checkpoint：runtime snapshot 和显式 state migration。

## 性能、可靠性与工程化

监控 startup/activation latency、dependency resolution、plugin errors、rollback/cleanup debt、per-port latency、queue saturation、configuration drift 和版本分布。插件隔离用 timeout、bulkhead、circuit breaker 与 resource quotas；不能让 tracing 插件故障阻塞核心 effect receipt 持久化。

发布要求插件 artifact digest、SBOM、签名、兼容矩阵、capability diff 和 rollback plan。回归不只测 happy path，还应故障注入每个 activation/dispose 点。

## 技术边界与设计取舍

本章实验是真实 callback/DAG/rollback，但在单进程中运行，没有动态加载第三方代码、签名验证、进程隔离或 dispose failure recovery。它证明 lifecycle mechanism，不证明 plugin supply-chain security。

OpenAI 或开源模型只是 model port 的实现。更换模型时，tool/policy/checkpoint/verifier 合同保持不变；key 由 credential port 短期提供，不传给其他插件。

## 前沿研究与演进方向

Harness 正从框架辅助代码演化为 Agent OS：统一 workspace、subagent、durable task、browser/computer use、policy 和 eval。值得研究的问题包括组件能力证明、跨 Harness 可移植 checkpoint、模型/工具热升级的语义兼容、插件供应链 attestations，以及怎样用运行历史自动改进 Harness 而不让自修改绕过治理。

### 深度审计与研究证据链

本章的真实证据是依赖解析、callback 激活和逆序 dispose 的可执行轨迹；它不包含第三方二进制加载或供应链签名。主流 Harness 对照只引用公开源码边界，任何托管内部实现都不从外部行为反推。

## 本章总结与进阶实践

Harness 决定 Agent 是否真正可运行、可治理和可演进。插件化的价值不在“扩展点多”，而在依赖、权限、生命周期与失败恢复都可验证。

进阶问题：

1. 哪些能力必须留在不可旁路的 Harness 内核？
2. 逆序 dispose 为什么仍不等于事务回滚？
3. 如何让正在运行的任务不受插件热升级影响？
4. 插件 manifest 至少应绑定哪些供应链和权限字段？
5. 怎样比较单进程插件与远程服务的故障域？

参考答案见[附录 I：第三篇问题参考答案](../appendix-i-part3-solutions.html#part3-solutions-ch19)。
