# Lab 36A — 部署工程：镜像身份、端口、健康与多架构契约｜正常路径

## 实验目标

读取仓库真实 `production/agentops_service/Dockerfile`、`docker-compose.yml` 与 `IMAGE_LOCK.json`，而非构造 Hello World。验证 base image digest 与锁一致、服务/镜像/Compose 端口、`/healthz`、非 root UID、source digest，以及 `linux/amd64` / `linux/arm64` 在锁文件中的声明同时闭合。声明不证明镜像已为两个架构构建或运行。

## 可证伪假设与不变量

不变量：只有构建身份、运行身份、端口和健康语义一致的 artifact 才能进入发布。`docker build` 成功不证明容器可接流量，更不证明它来自预期源码。

## 环境与版本

- Python 3.11–3.13；macOS/Linux，x86_64 或 arm64；
- 标准库读取/解析真实部署文件，不需要 Docker daemon、网络或 API key；
- 真正发布时仍须另跑多平台 build、镜像扫描、签名、SBOM 与运行时 smoke test，本实验不伪装成那些证据。

## 环境准备

```bash
python -m pip install uv==0.10.0
uv sync --locked --all-groups --no-install-project
```

## 实验代码

```python
root = Path.cwd()
gate = DeploymentGate()
evidence = gate.inspect_repository(root)
decision = gate.verify(evidence)
assert decision.release_allowed
assert evidence.exposed_port == evidence.command_port == evidence.compose_container_port == 8010
assert evidence.run_as_user == "65532:65532"
```

## 执行步骤

```bash
PYTHONPATH=src uv run python examples/chapters/ch36_deployment.py
```

## 实际验证输出（本发布源码执行所得）

```json
{"status":"STATIC_CONTRACT_READY","checks":{"base_digest_pinned":true,"port_contract":true,"semantic_healthcheck":true,"non_root":true,"multi_arch_declared":true,"image_lock_matches":true,"source_fingerprint_present":true},"ports":{"exposed":8010,"command":8010,"compose_host":8010,"compose_container":8010},"health_path":"/healthz","run_as_user":"65532:65532","evidence_level":"L1_MECHANISM"}
```

## 调试断点

- `DeploymentGate.inspect()` 的 `FROM`、`EXPOSE`、`CMD --port` 与 Compose port 解析；
- `source_digest` 是否随任一部署文件改变；
- `verify()` 的 hard checks；
- `IMAGE_LOCK.json` 的平台声明与真实 registry image index 是否在外部发布流水线复核。

## 验收标准

退出码 0；七项 check 全真；四个端口字段闭合；health 为 `/healthz`；运行身份非 root；状态为 `STATIC_CONTRACT_READY`。L1 只证明源码级 preflight，不声明镜像已在任何 registry/cluster 实际运行。

## 反例与进阶注入

- 用 `docker buildx imagetools inspect` 验证 registry 中确有 amd64/arm64 manifests；
- 在干净 runner 生成 SBOM、签名和 SLSA provenance，再由独立 job 验证；
- 启动容器后让数据库只读，证明 readiness 能失败而 liveness 不误杀进程。
