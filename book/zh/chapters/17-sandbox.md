# Sandbox 与能力安全：限制 Agent 的真实爆炸半径

> **本章命题**：Sandbox 不是临时目录，也不是一句“运行在 Docker 中”。可靠隔离必须同时约束身份、文件、进程、系统调用、网络、资源、secret 和生命周期；应用层路径门禁只是其中一层。

![从工具门禁到 OS/容器/微虚拟机的纵深隔离](../../assets/diagrams/17-sandbox-architecture.svg)

## 问题背景与学习目标

Coding Agent 会执行模型生成的命令、读取仓库并访问网络。即使没有恶意用户，错误命令、依赖安装脚本、prompt injection 或测试夹具都可能读取宿主凭据、覆盖仓库外文件、fork bomb、扫描内网。安全目标不是“相信模型谨慎”，而是让越界动作在模型意图之外仍不可达。

本章要求读者建立 capability + isolation 的威胁模型；理解路径规范化与 symlink/TOCTOU 风险；区分容器和虚拟机隔离；设计 rootfs、network、secret、resource 与 process policy；正确解释本书 `PathSandbox` 的严格 claim ceiling。

## 核心概念与系统直觉

能力安全用不可伪造、最小范围的 capability 表示权限，而不是先给全权再靠 prompt 禁止。一个执行单元的有效权限可写为：

$$
C_{effective}=C_{subject}\cap C_{task}\cap C_{tool}\cap C_{sandbox}\cap C_{policy}
$$

隔离则限制 capability gate 出错后的影响。防线包括非特权 UID、独立 mount/user/pid/network namespaces、只读 rootfs、显式 writable workspace、capability drop、seccomp/LSM、cgroup 配额、egress allowlist、短期 secret broker 与销毁/取证。

## 原理与理论基础

路径检查必须在 I/O 前把用户路径解析到可信根，并拒绝绝对路径、`..`、symlink/junction 逃逸。仅做字符串前缀比较会把 `/work-safe` 误认为 `/work` 子路径；先检查后打开仍可能遭 TOCTOU。更强实现应使用目录句柄相对操作、`openat2`/`RESOLVE_BENEATH` 等 OS primitive。

OCI Runtime Specification 的 Linux 配置展示 namespaces、cgroups、capabilities、LSM 与 filesystem jail 等不同维度；缺一并不等于另一层自动补齐。核心不变量是：**任何 I/O 或执行都必须持有显式 capability，解析后的对象位于授权边界内，并且未路由到 gate 的原生代码由 OS 级隔离承接。**

> **Invariant**: an operation needs an explicit capability and a target resolved inside its authorized boundary before any I/O occurs.

## 关键机制与执行流程

![Sandbox 请求从 capability 检查到审计回执的流程](../../assets/diagrams/17-sandbox-flow.svg)

1. 为任务创建新 workspace/sandbox identity，不复用宿主开发者身份；
2. 只挂载所需输入，rootfs/源码默认只读，输出目录单独可写；
3. tool request 先查 capability，再 canonicalize/resolve 路径；
4. command 使用 argv 而非 shell 拼接，并做 executable/working-dir/env allowlist；
5. 网络默认拒绝，只开放明确 destination/protocol；
6. secret 通过 broker 按用途临时注入，不进入 prompt、文件快照或 trace；
7. CPU/memory/pids/disk/time 受配额约束；
8. 输出生成 digest、修改清单与 policy decision，随后销毁或隔离保留。

## 从原理到实现

教学 `PathSandbox` 先检查 capability，再解析真实路径并验证位于 root 下：

```python
def _resolve(self, relative: str, capability: str) -> Path:
    if capability not in self.policy.capabilities:
        raise SandboxViolation(f"capability_denied:{capability}")
    candidate = self.root / relative
    resolved = candidate.resolve(strict=False)
    if resolved != self.root and self.root not in resolved.parents:
        raise SandboxViolation("path_outside_workspace")
    return resolved
```

写入限制大小、使用最小权限并在支持的平台添加 `O_NOFOLLOW`，随后 `fsync`：

```python
flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
if hasattr(os, "O_NOFOLLOW"):
    flags |= os.O_NOFOLLOW
fd = os.open(target, flags, 0o600)
with os.fdopen(fd, "wb") as handle:
    handle.write(payload)
    handle.flush()
    os.fsync(handle.fileno())
```

这不是 OS sandbox：任意 Python/native code 可绕过该对象。它只证明通过此工具入口的路径与 capability gate；教材明确禁止把它描述为生产隔离。

## 主流系统实现对照与源码阅读入口

| 层级 | 公开来源/系统 | 能控制什么 | 不能单独保证什么 |
|---|---|---|---|
| 应用 gate | 本书 `PathSandbox` | 工具入口的 path/capability/size | 原生代码、系统调用、网络、race 完整隔离 |
| OCI 容器 | [OCI runtime-spec](https://github.com/opencontainers/runtime-spec) | namespaces、cgroups、capabilities、mount 与安全配置 | 错误配置下的宿主隔离、内核漏洞、业务授权 |
| Coding harness | [OpenAI Codex CLI](https://github.com/openai/codex) | 公开源码中的 sandbox/approval/config 边界 | 未公开托管组件与所有宿主策略 |
| 远程 workspace | [OpenHands SDK](https://github.com/OpenHands/software-agent-sdk) | Agent/Tool/Workspace/Event 服务边界 | 部署者的 network/secret 配置自动安全 |
| 云代码执行 | [Google ADK](https://github.com/google/adk-python) | code executor 与 Agent workflow 接口 | 仅凭 SDK 类型证明底层隔离等级 |

## 设计方案与方法对比

| 隔离 | 启动/密度 | 边界强度 | 典型选择 |
|---|---|---|---|
| 进程 + 应用 gate | 最轻 | 低 | 可信只读工具、本地教学 |
| 容器 + seccomp/LSM | 中 | 中，依赖配置与共享内核 | CI、受控代码执行 |
| rootless/container sandbox runtime | 中高 | 较强 | 多租户执行 |
| microVM/VM | 较重 | 强，独立内核/硬件边界 | 不可信代码、高价值租户 |
| 一次性远程 worker | 取决于平台 | 可强并便于销毁 | 大规模 Agent 服务 |

ARM/x86_64 都可使用，只要镜像和依赖锁定支持目标架构；架构差异会影响测试、二进制依赖与 benchmark 可比性，但不改变隔离原则。

## 可复现实验

### Lab 17A：授权路径 I/O

正常实验真实创建临时 workspace，经 capability gate 写入、`fsync` 并读回文件：

```bash
PYTHONPATH=src uv run python examples/chapters/ch17_sandbox.py
```

实际输出包含 `allowed=true`、目标 `artifacts/report.txt`、内容摘要和 `escaped_exists=false`，等级 `L1_MECHANISM`。

### Lab 17B：目录逃逸拒绝

```bash
PYTHONPATH=src uv run python examples/chapters/ch17_sandbox.py --fault
```

故障输入 `../escape.txt`，实际输出 `allowed=false`、`reason=path_outside_workspace`、`escaped_exists=false`、`contained=true`，等级 `L3_CONTAINED`。见 [Lab 17A](../../../labs/core/lab-17A-sandbox.md) 与 [Lab 17B](../../../labs/core/lab-17B-sandbox-fault.md)。

**关键断点**：capability 检查、`resolve` 后 containment、symlink 遍历、`os.open` 和 escaped-file oracle。**验收标准**：正常文件可读回，逃逸文件绝不存在；报告必须注明“路径 gate，不是 OS sandbox”。

## 工程场景与系统设计

真实 Coding Agent 应使用一次性 worktree/容器，仓库挂载范围明确，宿主 SSH、云凭据、Docker socket 和浏览器 profile 默认不可见。依赖下载走 egress proxy/registry mirror；测试需要云权限时，由 broker 发放绑定 run、audience、scope 和 TTL 的短期 token。

构建产物先进入 quarantine，由独立扫描/测试后再发布。sandbox 销毁不等于审计删除：保留 redacted command、exit status、resource usage、diff 和 artifact digest，但不保存 secret 或无关用户数据。

## 故障模型、失败模式与排错

- `../`/绝对路径逃逸：canonical path 与 root containment；
- symlink race：目录句柄相对打开、禁止不可信 symlink；
- 容器内 root：改用非特权 UID、user namespace、drop capabilities；
- Docker socket 暴露：视为宿主级权限并默认拒绝；
- 默认出网：egress deny-by-default、DNS/目标审计；
- secret 进日志：结构化脱敏、禁止环境 dump；
- fork bomb/磁盘耗尽：pids/cpu/memory/disk/time quotas；
- 跨任务污染：一次性 sandbox 或可信 snapshot reset。

## 性能、可靠性与工程化

测量 cold start、image pull/cache、workspace materialization、I/O、CPU throttling、OOM、pids exhaustion、egress deny、cleanup time 和 leaked sandbox。安全优化应以 policy regression suite 为门禁；为了加速而挂载宿主 cache 时，必须评估 cache poisoning 与跨租户泄漏。

镜像应按 digest 锁定并生成 SBOM/签名，基础镜像和内核补丁纳入升级测试。对于多架构发布，分别记录 image digest、platform 和实际运行证据，不能假设 manifest list 下所有架构行为完全一致。

## 技术边界与设计取舍

Core Lab 不启动 Docker，因为最小测试应在 macOS/Linux、ARM/x86_64 都能运行；它因此不声称验证 namespaces/seccomp/cgroups。生产隔离实验必须另行保存容器配置、宿主内核、runtime 版本、negative tests 与 verifier。容器也不是安全结论，只有实际配置和攻击面测试才是证据。

API key 通过本地未跟踪环境或 secret manager 注入。OpenAI key 不挂载到不需要模型调用的 verifier/test 容器；开源模型权重同样应只读并校验 digest。

## 前沿研究与演进方向

方向包括面向 Agent 的细粒度 capability token、可证明 egress policy、快照式 microVM、机密计算、跨工具信息流控制，以及能把 prompt-level intent 映射到 syscall/network trace 的审计系统。更难的问题是组合安全：每个工具单独安全，不代表工具序列不会产生越权效果。

### 深度审计与研究证据链

本章的负例 oracle 是 workspace 外文件确实不存在，而不只是捕获异常；这足以支持路径 gate 的 L3 结论。OCI、容器或 VM 安全则必须保存真实 runtime 配置、内核/平台、攻击测试和外部 verifier，本书不会用应用层测试代替它们。

## 本章总结与进阶实践

Sandbox 的价值是把模型和依赖的错误限制在可接受边界。路径门禁、容器和 VM 是不同强度的层，必须如实命名、组合防御并用负例验证。

进阶问题：

1. 为什么 `resolve()+prefix` 仍不能完全消除 TOCTOU？
2. 容器中的 root 为什么可能仍然危险？
3. 网络 allowlist 应如何处理 DNS、重定向和代理？
4. 怎样让 verifier 获得 artifact 而不继承 Agent 的 secret？
5. 多架构镜像的可复现与隔离证据应分别记录什么？

参考答案见[附录 I：第三篇问题参考答案](../appendix-i-part3-solutions.html#part3-solutions-ch17)。
