# Security Policy

AI Agent Systems 涉及工具执行、文件修改、浏览器自动化、外部 API、凭据和持久状态。安全问题包括但不限于命令/提示注入、路径逃逸、越权工具调用、凭据泄露、不安全反序列化、SSRF、任意代码执行和重复副作用。

## 支持范围

| Version | Supported |
|---|---|
| 1.x | Yes |
| < 1.0 | No |

教材中的教学 fixture 不等于生产安全保证；各实验的 claim ceiling 以 `EXPERIMENT_STATUS.md` 和证据目录为准。

## 私密报告漏洞

请使用 GitHub 仓库的 **Security → Report a vulnerability** 私密通道提交报告。不要在公开 issue、discussion、PR、日志或示例数据中披露漏洞细节、利用代码、凭据或个人数据。

报告请包含：

- 受影响的 commit/tag 和文件；
- 前置条件、最小复现步骤与实际影响；
- 是否涉及凭据、网络、文件系统或不可逆副作用；
- 建议修复或缓解方案；
- 可安全联系你的 GitHub 账号。

维护者目标是在 3 个工作日内确认收到，在完成影响评估后协调修复与披露。该时间是响应目标，不构成服务等级协议。

## 凭据与测试数据

- 只通过本地环境变量或 GitHub Actions encrypted secrets 注入 provider key。
- 不提交 `.env`、token、session cookie、真实业务数据库和未脱敏 agent trace。
- 安全测试应默认使用临时目录、最小权限、合成数据和不可联网 fixture。
- 如果凭据曾进入 Git 历史，应立即在提供方撤销并轮换；仅删除文件不足以消除泄露。

## 发布安全

正式发布必须来自受保护的 `main`、通过 required checks，并附带校验和与 GitHub artifact attestation。依赖、容器和 Action 更新应由单独 PR 审查。
