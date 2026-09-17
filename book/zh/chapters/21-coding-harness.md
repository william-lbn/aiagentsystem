# Codex、Pi 与 Claude Code 类 Harness 解剖

> **本章命题**：Coding Agent 的核心产品不是聊天框，而是一个把仓库基线、会话谱系、工作区、权限、工具事件、验证结果和失败证据共同持久化的 engineering harness。模型提出补丁；Harness 决定补丁能否安全、可恢复地成为工程事实。

上一章已经实现最小的“读—改—测—失败回滚”。本章把单次补丁扩展为可分支、可压缩、可恢复的长期会话；下一章再把这些边界提升为远程 Agent Server。

![Coding Harness 的会话、工作区、控制面与证据面](../../assets/diagrams/21-coding-harness-architecture.svg)

## 问题背景与学习目标

长任务通常超过单次上下文窗口，并且会经历代码基线变化、工具失败、用户纠偏和并行探索。仅保存 message history 会制造危险错觉：自然语言看似连续，仓库、测试和权限状态却可能已经改变。真正需要恢复的是一个 engineering run，而不是一段对话。

读完本章，读者应能：区分 session、branch、workspace 与 model context；设计保留负面证据的 compaction；用 immutable baseline 和 dirty-state digest 防止跨分支污染；解释 approval 为何必须绑定具体 action；运行 SQLite 持久化实验并识别它不能证明真实 Coding Agent 的任务能力。

## 核心概念与系统直觉

**Session** 是任务身份和 durable state 的根；**branch** 是带父节点的假设分叉；**workspace** 是某个 branch 可写的代码视图；**context** 只是给模型的一次有限投影。四者混为一谈时，最常见的事故是：分支 B 使用分支 A 的摘要，却在共享目录覆盖 A 的文件。

Compaction 也不是“把旧消息总结短一点”。它至少应保留：目标、用户约束、baseline commit、允许修改范围、未解决失败、已验证事实、artifact digest、待审批动作和 ancestry。普通叙述可以压缩，决定系统能否继续执行的事实必须结构化并可回源。

Approval 则是一个不可变 action envelope 的授权证据，不能是脱离对象的一句“同意”。若命令、文件范围、仓库状态或 policy version 发生变化，旧批准必须失效。

## 原理与理论基础

把第 (b) 个分支的可恢复状态写成：

$$
R_b=(G,B,W,P,F,E,A,V),
$$

其中 (G) 是目标，(B) 是 baseline，(W) 是 workspace identity，(P) 是 parent/ancestry，(F) 是 typed facts，(E) 是事件序列，(A) 是待决授权，(V) 是 verifier 结果。模型上下文只是投影 (C_b=\pi(R_b, budget))，因此不能反过来把 (C_b) 当作完整事实源。

> **Invariant**: session branching and compaction must preserve ancestry, constraints, failures and verified facts.

这个不变量比“摘要读起来合理”更强。只要 ancestry、失败测试或 scope 中任一项丢失，恢复后的决策就无法证明仍针对同一任务世界。Compaction 的正确性应通过“完整事件重放”和“snapshot + 尾部事件重放”所得关键状态一致来检验。

## 关键机制与执行流程

![Coding Harness 从建会话、分支、压缩到恢复验证的流程](../../assets/diagrams/21-coding-harness-flow.svg)

1. 建立 run/session，锁定 goal、repo identity、baseline commit、policy 与 workspace；
2. 所有观察、决策、失败与 artifact 以 typed fact/event 写入；
3. 分支创建前验证 parent 存在，分配独立 worktree/container；
4. compactor 按事实类型合并 latest value，但保留 ancestry 与失败证据；
5. 恢复时重新打开 durable store，验证 snapshot digest、baseline 和 workspace；
6. 模型基于投影提出下一动作，Runtime 再做 schema、policy 和 preimage 检查；
7. patch 由独立 verifier 验证，结果回写 session；
8. 合并分支时使用代码层 merge 与 verifier，而不是让模型口头宣称“已合并”。

关键崩溃窗口位于“文件已改、事件未落盘”和“测试完成、结果未记录”之间。前者需通过 preimage/diff 与 workspace 扫描重建，后者只能重跑无副作用 verifier；两者都不能从模型记忆推断。

## 从原理到实现

本仓库的 `SessionLedger` 使用真实 SQLite 文件保存 session tree 与 typed facts；关闭连接后重新打开，再执行 compaction。核心代码不是字符串摘要，而是先恢复 ancestry，再在该路径上选择每个 `(kind,key)` 的最新事实：

```python
def compact(self, session_id: str) -> CompactSnapshot:
    ancestry = self.ancestry(session_id)
    placeholders = ",".join("?" for _ in ancestry)
    rows = self.connection.execute(
        f"select * from facts where session_id in ({placeholders}) order by event_id",
        ancestry,
    ).fetchall()
    latest = {}
    for row in rows:
        item = {"event_id": row["event_id"], "session_id": row["session_id"],
                "kind": row["kind"], "key": row["fact_key"],
                "value": json.loads(row["value_json"])}
        latest[(item["kind"], item["key"])] = item
    facts = tuple(sorted(latest.values(), key=lambda x: x["event_id"]))
    payload = {"session_id": session_id, "ancestry": ancestry, "facts": facts}
    return CompactSnapshot(session_id, ancestry, facts, _digest(payload))
```

创建分支时先验证父会话，失败即不写入任何 orphan row：

```python
ledger.create("root", goal="repair parser", baseline="abc123", workspace="worktree-root")
ledger.record("root", "failure", "test_empty", "IndexError")
ledger.create("branch", parent_id="root", goal="repair parser",
              baseline="abc123", workspace="worktree-branch")
ledger.close()

snapshot = SessionLedger(db_path).compact("branch")
assert snapshot.ancestry == ("root", "branch")
assert {x["kind"] for x in snapshot.facts} >= {"failure", "decision"}
```

实现位于 `src/agentlab/specialized_system.py`。它证明 SQLite durability 与 lineage gate；它不实现 Git merge、OS sandbox、真实模型 compaction 或分布式事务。

## 主流系统实现对照与源码阅读入口

| 系统 | 应观察的公开边界 | 不应从客户端现象推断的内容 |
|---|---|---|
| [OpenAI Codex](https://github.com/openai/codex) | 本地 workspace、命令/补丁工具、sandbox/approval/config、会话与事件入口 | 未公开托管调度器、内部 policy 或容量架构 |
| Pi Coding Agent | session tree、branching、compaction、extension/skill 与极简 harness | 包名兼容不代表各版本状态格式兼容 |
| Claude Code 类工具 | permission、hook、subagent/worktree 与长任务实践的公开契约 | 服务端模型路由和未公开执行实现 |
| SWE-agent / mini-SWE-agent | issue—trajectory—patch—test 的最小研究闭环 | 单个 demo 不能代表 SWE-bench 分数 |

源码阅读顺序应是：session schema → workspace identity → tool dispatch → permission gate → compaction → verifier → resume。先找谁拥有不可逆状态，再看模型 prompt；否则容易把产品 UI 当作系统语义。

## 设计方案与方法对比

| 方案 | 可恢复性 | 隔离 | 主要代价 |
|---|---:|---:|---|
| 单聊天 + 单目录 | 低 | 低 | 简单，但长任务极易漂移 |
| JSON snapshot + worktree | 中 | 中 | 需处理原子写、版本与迁移 |
| 事件日志 + SQLite + worktree/container | 高 | 高 | schema、GC、artifact 管理更复杂 |
| 远程 workspace + Agent Server | 可横向扩展 | 可做强隔离 | 网络、租户、租约与观测成本更高 |

模型摘要可提高 token 效率，但不能独占 compaction；纯规则 compaction 可审计，却可能遗漏语义关联。生产方案通常是“结构化必保字段 + 模型生成辅助摘要 + 回源指针 + 机器验证”。

## 可复现实验

### Lab 21A — 正常路径

```bash
PYTHONPATH=src python examples/chapters/ch21_coding_harness.py
```

本发布包实际输出的关键观察为：`ancestry=[root,branch]`、`fact_kinds=[constraint,failure,decision]`、`reopened_from_sqlite=true`，证据等级 `L1_MECHANISM`。验收要求退出码 0、snapshot digest 存在，并且重开数据库后仍保留失败事实。完整步骤见 [Lab 21A](../../../labs/core/lab-21A-coding-harness.md)。

### Lab 21B — 故障注入

```bash
PYTHONPATH=src python examples/chapters/ch21_coding_harness.py --fault
```

实际输出包含 `error=parent_session_missing`、`orphan_rows=0`、`evidence_level=L3_CONTAINED`。关键断点是 `SessionLedger.create` 的 parent lookup 与 commit：异常必须发生在 insert 之前。完整步骤见 [Lab 21B](../../../labs/core/lab-21B-coding-harness-fault.md)。

**实验语义边界。** 这两条实验真实创建、关闭并重开 SQLite，但没有调用 Codex/Pi/Claude Code，也没有测 SWE-bench；因此只能声称 session lineage 机制被执行，不能声称某个 Coding Agent 更强。

## 工程场景与系统设计

以“修复解析器并补回归测试”为例，root session 记录 issue、baseline 与失败测试；两个 branch 分别探索 guard 和 parser rewrite，各自绑定独立 worktree。合并候选前，Harness 对比 changed files、测试集合、dependency diff 与 unresolved facts。若 baseline 已移动，则重新计算 patch applicability，而不是直接复用旧批准。

模型可由[附录 A](../appendix-a-environment.md)的本地小模型或 OpenAI Responses adapter 提供 proposal。无论使用哪种模型，session/branch 创建、文件作用域、审批、测试与完成状态仍由确定性软件拥有；API key 只来自环境变量且不得进入 trace。

## 故障模型、失败模式与排错

- **压缩丢失负面证据**：比较 full replay 与 compacted replay 的 failure/constraint 集合；
- **共享 workspace 写穿**：记录 workspace identity、baseline、dirty digest，并阻断跨 branch path；
- **批准对象漂移**：对 command、patch、scope、baseline 和 policy version 做 canonical digest；
- **恢复到旧 schema**：snapshot 带 schema version，迁移失败则只读打开；
- **测试误报**：保存命令、解释器、退出码、stdout/stderr 与 artifact digest，不只保存“通过”。

排错顺序是 durable session → repo/workspace → event tail → pending approval → verifier artifact，最后才看模型自然语言。

## 性能、可靠性与工程化

需要同时测 session 恢复成功率、compaction regression rate、branch conflict rate、每任务 tool steps、测试重跑成本、orphan workspace 数和 unknown-outcome duration。Context token 降低不等于系统优化：若压缩让失败路径重复，整体时间和成本反而更高。

事件表按 session/sequence 建索引；大 stdout、镜像和构建产物进入 content-addressed artifact store，日志只存 digest 与 locator。GC 必须尊重活跃 branch、审计保留期和法律保全，不可按“最近未聊天”删除工程证据。

## 技术边界与设计取舍

本实现没有 Git object database、真实 worktree、container 和 secret broker；SQLite 单机 durability 也不等于跨主机高可用。它刻意隔离 lineage/compaction 不变量。若将实验升级到 L5，应锁定上游版本，真实创建仓库与隔离 workspace，执行 patch/test/恢复，并归档完整 trajectory 与环境指纹。

“自动合并所有成功分支”不是合理默认值。测试通过只证明已覆盖 oracle；不同分支可能引入互斥语义。高风险仓库仍需要代码所有者审批、供应链扫描和发布门禁。

## 前沿研究与演进方向

前沿问题已从单轮代码生成转向长程 harness：如何让 context compaction 保真，如何在多分支探索中分配预算，如何用独立 verifier 降低 reward hacking，如何把交互 trajectory 转为可复现实验，以及如何在不泄露源码/secret 的前提下形成训练反馈。

### 深度审计与研究证据链

截至本书知识截止日 2026-09-11，本章只把公开源码/文档用于机制对照；仓库 Core Lab 提供本地 SQLite 行为证据。任何真实模型成功率、SWE-bench 得分或商业产品内部架构都必须来自单独锁定的外部运行与官方结果，不从本实验外推。

## 本章总结与进阶实践

Coding Harness 的本质是“可恢复工程状态 + 受治理执行”，不是更长的 prompt。合格实现必须让 ancestry、约束、失败、diff、权限与 verifier 在模型上下文之外仍然成立。

进阶问题（答案见[附录 J](../appendix-j-part4-solutions.html#ch21)）：

1. 为什么保存完整聊天记录仍不能恢复一个 Coding Agent？
2. 哪些事实允许模型压缩，哪些必须结构化保留？
3. branch 与 worktree 为什么必须分别建模？
4. 如何验证 compaction 没有改变任务语义？
5. 如何把本章 L1/L3 实验升级为可公开复核的 Coding Agent benchmark？
