# 上游行为复现：DeepSeek Harness

- 合同 ID：`UPSTREAM-DSH-001`
- 核验状态：`EXTERNAL_NOT_RUN_IN_THIS_RELEASE`
- 固定版本：`@deepseek-ai/dsh 0.1.2-rc.1 reproducibility pin`
- 官方来源：https://github.com/deepseek-ai/deepseek-harness
- 机制焦点：**RC harness session/tool execution evidence**

> **证据边界**：本文件定义“未来真实复现必须证明什么”，不代表本次离线发行已经运行第三方框架。安装成功最多记为 L1；只有完成下面的行为、故障与独立 verifier，并保存证据包，才能升级为 L5_EXTERNAL。

## 行为合同

### 正常场景

在临时 workspace 中运行 pinned RC 的官方最小可执行路径，调用一个确定性本地 tool/command 并保存 session/harness 输出与 artifact。

### 故障场景

让 tool/command 以确定性非零状态失败；验证 harness 显式记录失败，不把 artifact 缺失包装成成功。

### 独立 Verifier

npm/package version、完整命令、event/session log、exit code、artifact/hash。

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

这是 release-candidate 历史复现 pin；即使合同通过，也只能说明该 RC 的观测行为，不能宣称 API 稳定或生产成熟。
