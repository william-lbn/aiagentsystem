# Lab 36B — 部署工程：镜像身份、端口、健康与多架构契约｜故障注入

## 实验目标

只在内存中把 Compose 容器端口从 8010 改为 8000，保持 Dockerfile 的 `EXPOSE` 与启动命令不变。验证发布 gate 在构建之前明确指出 `port_contract=false` 并阻断 release。

## 可证伪假设与故障位置

故障位于 service discovery 与进程监听边界。若 CI 只验证 YAML 可解析或镜像能 build，错误会推迟到上线后才暴露；被测 gate 必须自己检测并 fail closed。

## 环境与版本

与 Lab 36A 相同。不会改写磁盘上的 Compose 文件，也不依赖 Docker daemon；fault fixture 的 source digest 与正常路径不同，可供审计。

## 环境准备

```bash
python -m pip install uv==0.10.0
uv sync --locked --all-groups --no-install-project
```

## 实验代码

```python
import json
from pathlib import Path

root = Path.cwd()
dockerfile_path = root / "production/agentops_service/Dockerfile"
compose_path = root / "docker-compose.yml"
lock_path = root / "production/agentops_service/IMAGE_LOCK.json"
dockerfile = dockerfile_path.read_text()
compose = compose_path.read_text().replace('"8010:8010"', '"8010:8000"')
image_lock = json.loads(lock_path.read_text())
evidence = DeploymentGate().inspect(dockerfile, compose, image_lock=image_lock)
decision = DeploymentGate().verify(evidence)
assert decision.status == "BLOCKED"
assert decision.checks["port_contract"] is False
```

## 执行步骤

```bash
PYTHONPATH=src uv run python examples/chapters/ch36_deployment.py --fault
```

## 实际验证输出（本发布源码执行所得）

```json
{"status":"BLOCKED","checks":{"base_digest_pinned":true,"port_contract":false,"semantic_healthcheck":true,"non_root":true,"multi_arch_declared":true,"image_lock_matches":true,"source_fingerprint_present":true},"ports":{"exposed":8010,"command":8010,"compose_host":8010,"compose_container":8000},"system_detected":true,"contained":true,"evidence_level":"L3_CONTAINED"}
```

## 调试断点

- fault replacement 后磁盘文件保持不变；
- `compose_container_port=8000` 而 exposed/command 仍为 8010；
- `release_allowed` 从 true 变 false；
- 输出只包含配置证据，不包含环境 secret。

## 验收标准

退出码 0；恰由 `port_contract` 失败触发 `BLOCKED`；`system_detected=true`、`contained=true`、`evidence_level=L3_CONTAINED`。这证明错误发布被阻断，不证明线上已有旧版本被自动回滚。

## 反例与进阶注入

- 删除 base digest、改回 root、移除 healthcheck，确认每个原因可独立定位；
- 镜像支持 amd64 但漏 arm64 manifest，确认外部 registry gate 阻断；
- 模拟 probe 只检查 TCP 端口而数据库不可写，比较 liveness/readiness 的差异。
