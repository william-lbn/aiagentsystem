# 附录 I：第三篇问题参考答案

> 本附录回答第十四至二十章的 35 个问题。答案的重点是可验证边界；若读者给出不同设计，但明确了状态、故障窗口、反例和证据，也可能同样成立。

## 第十四章答案：有限循环与验证 {#part3-solutions-ch14}

### 题一：Finish 为什么只是提案

模型只能根据有限上下文生成 `finish`，可能遗漏失败、引用不存在的 artifact 或把工具报错解释为成功。Runtime 必须让独立 verifier 检查外部可观察后置条件；只有 verifier 通过才进入 `FINISHED`，否则是 `VERIFICATION_FAILED` 或继续受预算控制。

### 题二：Evidence Gain

不要比较措辞变化。可把新 source span、未覆盖 claim 减少、测试状态变化、artifact digest 变化、冲突解析或外部 receipt 作为结构化增益；连续相同 action+observation digest 计为无进展。阈值应在任务数据上校准。

### 题三：预算分层

Run 层限制总 turns/token/cost/deadline/effects；tenant 层限制并发和周期配额；tool 层限制单次 timeout、payload、retry 和危险操作数量。预算扣减由 Runtime 记录，模型不能自行重置。

### 题四：写超时后的状态

超时只说明客户端没收到确定响应，远端可能已提交。继续下一轮或重试可能重复效果；应记录 action identity，把状态设为 UNKNOWN，并用幂等键、receipt 或权威查询对账。

### 题五：恢复等价

定义对外可观察投影：最终 artifact、effect 集合、授权记录和终态。对同一输入运行无崩溃轨迹与在各 durable point kill/restart 的轨迹，要求投影相同或都停在显式 UNKNOWN；内部模型调用次数可以不同。

## 第十五章答案：并发与取消 {#part3-solutions-ch15}

### 题一：First-completed 与 First-success

最先结束的 task 可能失败、超时或返回不满足业务条件的空结果。First-success 必须对结果运行 oracle；若不合格就继续等待其余任务，并最终聚合失败原因。

### 题二：取消后的 UNKNOWN

只要请求已越过本地 dispatch 点且远端没有可证明的撤销协议，coroutine 的 `CANCELLED` 就不能推出 effect 未发生。此时 task state 是 cancelled，business effect state 是 UNKNOWN，两者应分别保存。

### 题三：可恢复流式序列

事件至少携带 run/task ID、单调 sequence、event type、payload digest 与 producer version；消费者保存 offset/去重键。恢复从已确认 offset 继续，重复事件幂等处理，gap 或乱序显式报错。

### 题四：TaskGroup 的边界

它提供单进程父子生命周期和异常/取消传播，能减少 orphan coroutine；不能撤销 HTTP/数据库效果，不能跨进程持久化，也不提供分布式 lease、消息去重或 crash recovery。

### 题五：并发优化的等价性

在相同输入、权限和版本上比较串行/并行输出的 canonical artifact、effect 集与 verifier；故障注入乱序、慢请求、取消和部分失败。共享 state 必须用确定 reducer/CAS，否则结果可能依赖调度。

## 第十六章答案：持久授权 {#part3-solutions-ch16}

### 题一：编辑必须新建 Action

批准的是旧参数摘要。编辑后继续复用批准会破坏“看到什么、批准什么”的承诺；应生成新 action ID/digest，旧决定保留为 rejected/superseded 证据，并重新授权。

### 题二：授权与正确性

审批只证明某主体允许该动作，不证明动作会达到目标、参数无误或外部系统正确执行。Verifier 检查后置条件，effect journal 记录事实；三者不能互相替代。

### 题三：策略或资源变化

审批绑定 policy/state/resource version。恢复时重读当前版本；不一致就使旧批准过期，重新生成 preview/action。不能因原批准者权限曾经有效就跳过当前授权。

### 题四：批量审批

Canonicalize 完整成员集合及每项参数，digest 覆盖数量、顺序规则和 scope；UI 显示总数、风险汇总及可展开明细。执行时拒绝额外成员或集合漂移，必要时拆成多个 action。

### 题五：并发消费测试

让两个 worker 同时用同一 approval/action version 恢复；通过 CAS/唯一约束只允许一个从 WAITING 转为 EXECUTING，另一个得到 conflict。Verifier 断言工具 effect 和 journal receipt 只有一次。

## 第十七章答案：执行隔离 {#part3-solutions-ch17}

### 题一：TOCTOU

`resolve()` 与后续 `open()` 之间，攻击者可能替换路径组件为 symlink。更强做法是从可信目录 fd 开始逐级打开，使用 `O_NOFOLLOW`、`openat2 RESOLVE_BENEATH` 等原子解析约束，并让不可信代码处于 OS sandbox。

### 题二：容器内 Root

容器共享宿主内核；过宽 capability、host mount、Docker socket、特权模式或内核漏洞可扩大权限。应使用非特权 UID/user namespace、drop capabilities、只读挂载、seccomp/LSM 和最小设备/网络。

### 题三：网络 Allowlist

在解析和连接时校验最终 IP/端口/协议，防 DNS rebinding；限制 redirect 次数并对每跳重判；代理成为强制 egress 点；阻止 link-local/metadata/private ranges，记录 SNI/目标与 policy decision。

### 题四：Verifier 与 Secret 分离

Agent workspace 输出只读 artifact/diff；独立 verifier 容器使用最小环境和只读 source，不挂载模型/API 凭据。若测试确需 secret，由 broker 发放绑定 verifier identity、audience、scope 和 TTL 的独立凭据。

### 题五：多架构证据

分别记录 manifest digest 与平台 image digest、OS/kernel/runtime、CPU architecture、toolchain/lockfile、执行命令、测试日志和 artifact digest。跨架构哈希不同不必等于失败，但应定义 canonical 内容或按平台发布 attestation。

## 第十八章答案：持久状态与事件 {#part3-solutions-ch18}

### 题一：Parent Directory Fsync

文件 `fsync` 保证文件内容落盘，但 rename 更新的是目录项。掉电后若目录元数据未持久化，新名字可能消失；因此 atomic replace 后对父目录 fsync 才完成常见 POSIX 本地文件系统的 durable rename 流程。

### 题二：CAS 的能力边界

CAS 防 lost update、stale writer 和部分 split-brain state overwrite；它不能撤销已发出的外部请求，也不能证明 effect 是否提交。外部世界仍需 idempotency、receipt、fencing 或 reconciliation。

### 题三：观察等价

定义可观察投影并在多个 crash point 对比：最终状态、artifact digest、授权与外部 effect 集合相同；若无法确定则两者都不能声称成功。内部 event 数可不同，但不得多出业务效果。

### 题四：Compaction 与删除

先生成覆盖到 sequence N 的验证 snapshot，保存 Merkle/hash anchor、schema 和审计索引，再按 retention 删除已覆盖事件。隐私删除需要 crypto-shredding/redaction/tombstone 策略；不能保留可重建已删除 PII 的“审计副本”。

### 题五：模型调用的 Replay

若输出影响已发生的状态转移，应把 response/digest/provider metadata 作为 task result 持久化并复用；重新调用只适用于尚未提交的纯候选步骤。需要重算时创建新分支/version，不能把新输出伪装为原轨迹。

## 第十九章答案：宿主生命周期 {#part3-solutions-ch19}

### 题一：不可旁路内核

身份/租户、capability policy、approval、credential broker、effect journal、checkpoint versioning、audit 与终态 verifier 应在所有执行路径上强制。UI、model、retriever 和领域工具可作为 adapter/plugin。

### 题二：Dispose 不是回滚

Dispose 通常只释放本地 handle；插件可能已发送网络请求、写数据库或启动远程资源，逆序调用也无法原子撤销。每个外部 effect 仍需 journal、幂等/补偿和 cleanup debt。

### 题三：升级隔离

每个 run 绑定 immutable runtime snapshot：插件 digest、config/policy/schema version。旧 worker drain 并完成或 checkpoint/migrate；新 worker 只接新 run。不得让同一 run 中途解析到不同插件实现。

### 题四：Manifest 字段

至少包含 identity/publisher、semantic/API version、artifact digest/signature/SBOM、dependencies、runtime compatibility、requested capabilities、config/event schema、lifecycle hooks、state migration、owner、revocation 与 eval evidence。

### 题五：故障域比较

单进程调用低延迟但共享内存、权限和崩溃；远程服务可独立隔离/扩缩，却引入网络、auth、版本和最终一致。用 blast radius、SLO、数据敏感度、吞吐和运维能力选择，而非按流行度排名。

## 第二十章答案：代码变更闭环 {#part3-solutions-ch20}

### 题一：退出码与模型总结

退出码来自被指定的可执行 oracle，模型总结只是对日志的概率解释，可能忽略失败或被输出注入。退出码仍依赖测试质量，所以应同时保留命令、环境、stdout/stderr 和结构化测试报告。

### 题二：Preimage 的边界

唯一 preimage 防止目标缺失、重复和一部分上下文漂移；不能防读取后到写入前的并发修改，也不保护其他文件。需 worktree/lock、base commit、全文件 hash 或 compare-and-swap write。

### 题三：保护测试

将 verifier/hidden tests 放在只读或仓库外路径；限制 allowed files；对 test manifest 和命令做 digest；比较 baseline 与 patched run；审查测试删除、skip/xfail 和配置放宽。

### 题四：ARM 上的 SWE-bench 声明

官方 harness 已说明 ARM 支持边界时，应记录本地构建的 task image、platform 与失败类型；只与同一 dataset/harness/architecture 条件比较，不能把兼容性失败计为模型能力，也不能与 x86 官方榜单无条件横比。

### 题五：升级到 L5

锁定官方 SWE-bench repo/harness、dataset revision、真实 instance、base commit/task image；用真实模型或明确 agent 生成 prediction patch；运行官方 Docker evaluation；保存环境、命令、patch、build/eval logs、results.json、成本与独立 verifier。没有这些不得报告 benchmark 分数。
