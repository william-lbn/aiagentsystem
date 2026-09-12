# 上游行为复现：LangGraph

- 合同 ID：`UPSTREAM-LANGGRAPH-001`
- 核验状态：`EXTERNAL_NOT_RUN_IN_THIS_RELEASE`
- 固定版本：`langgraph==1.2.11 @ 644815f`
- 官方来源：https://github.com/langchain-ai/langgraph
- 机制焦点：**checkpointer + interrupt/resume**

> **证据边界**：本文件定义“未来真实复现必须证明什么”，不代表本次离线发行已经运行第三方框架。安装成功最多记为 L1；只有完成下面的行为、故障与独立 verifier，并保存证据包，才能升级为 L5_EXTERNAL。

## 行为合同

### 正常场景

用 pinned LangGraph 构造最小 StateGraph，配置 checkpointer 与固定 `thread_id`，在副作用前 `interrupt`；持久化后用 `Command(resume=...)` 恢复并验证状态从暂停点继续。

### 故障场景

在 interrupt 后模拟进程退出再重新加载同一 thread；验证恢复不会把已确认的前置节点重复计算成第二个外部副作用。若示例使用非幂等 effect，必须用独立计数器揭示重复。

### 独立 Verifier

checkpoint backend 内容/版本、节点执行计数、最终 state 与 event/stream 记录四者交叉验证。

## 环境与版本固定

在独立环境中安装/checkout 上述 pin；开始实验前必须记录 `OS/arch`、语言 runtime、package/tag/commit、模型/provider（若使用）、依赖锁文件与完整命令。若 pin 无法获取，实验应记为 `BLOCKED_PIN_UNAVAILABLE`，不得自动改用最新版。

## 最小证据包

每次真实运行必须至少保存：

- `environment.json`：OS/arch/runtime/package/tag/commit/provider；
- `commands.txt`：按执行顺序记录可复制命令；
- `stdout.log` / `stderr.log`：未经人工改写的输出；
- `verifier.json`：机器可读断言与实际值；
- `artifact-hashes.sha256`：状态、diff、wire capture 或业务 artifact 的哈希；
- 若涉及网络协议，再保存去密后的 raw request/response；若涉及副作用，再保存独立 side-effect counter/observation。

## 判定规则

- `PASS_L5_EXTERNAL`：正常场景、故障场景和独立 verifier 全部通过，且版本证据完整；
- `FAIL_BEHAVIOR`：框架实际行为与合同冲突；
- `BLOCKED_ENVIRONMENT`：缺少 Docker/API Key/浏览器/网络等外部条件；
- `BLOCKED_PIN_UNAVAILABLE`：指定版本无法获得；
- 不允许用“安装成功”“命令返回 0”“模型说完成了”替代行为证据。

## Claim Ceiling

只证明 pinned graph/checkpoint semantics；外部副作用的 exactly-once 仍取决于应用 idempotency/reconciliation。
