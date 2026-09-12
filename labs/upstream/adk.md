# 上游行为复现：Google Agent Development Kit

- 合同 ID：`UPSTREAM-ADK-001`
- 核验状态：`EXTERNAL_NOT_RUN_IN_THIS_RELEASE`
- 固定版本：`google-adk==2.1.0 @ 6d15e19`
- 官方来源：https://github.com/google/adk-python
- 机制焦点：**session state + tool/event trajectory**

> **证据边界**：本文件定义“未来真实复现必须证明什么”，不代表本次离线发行已经运行第三方框架。安装成功最多记为 L1；只有完成下面的行为、故障与独立 verifier，并保存证据包，才能升级为 L5_EXTERNAL。

## 行为合同

### 正常场景

运行 pinned ADK 官方最小 agent/tool 路径，给 tool 一个确定性输入，保存 session/state 与完整 event trajectory，并用业务侧 artifact 验证 tool 的实际结果。

### 故障场景

让同一 tool 返回受控错误（禁止依赖网络抖动）；验证错误以显式 event/result 进入轨迹，且 session 中不存在伪造的成功 artifact。

### 独立 Verifier

版本输出 + event log + session/state dump + 独立 artifact/hash。

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

合同不要求真实模型质量；若使用 stub/model fixture只能证明 runtime integration，不能宣传 provider/model E2E。
