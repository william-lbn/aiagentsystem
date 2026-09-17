# 附录 A：统一实验环境、调试与复现

核心实验只依赖 Python 3.11–3.13 与本仓库包。统一安装：

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python scripts/run_core_labs.py
pytest -q
```

调试时优先在 `examples/chapters/chXX_*.py::main`、`src/agentlab/course_scenarios.py` 对应函数，以及 `runtime.py::AgentRuntime.run` 设置断点。对持久化实验同时观察 `.agentlab/` 或临时目录中文件。

外部框架复现必须另建虚拟环境，并记录 `python --version`、`pip freeze`、仓库 tag/commit、模型/provider 和 API 区域。核心实验 PASS 不代表外部框架实验已执行。

## A.1 Core Lab 的证据等级与 claim ceiling

本书把“代码能跑”“测试看到故障”“系统阻断故障”“系统完成恢复”“真实上游互操作”严格拆开。所有 Core Lab 的 JSON 输出至少包含 `passed / oracle_detected / system_detected / contained / recovered / invariant_holds / evidence_level`；`passed=true` 只表示该 lab 自己的 oracle 命中，不自动代表系统已经恢复。

| 等级 | 可以声称什么 | 不能声称什么 |
|---|---|---|
| L0_SOURCE | 源码或 fixture 存在、可检查 | 代码可运行 |
| L1_MECHANISM | 确定性正常路径满足机制断言 | 故障会被系统发现 |
| L2_ORACLE_ONLY | 独立 oracle 能看到被注入的坏结果 | 被测系统自身检测/阻断了故障 |
| L2_DETECTED | 被测组件自身识别了故障 | 受保护不变量一定未被破坏 |
| L3_CONTAINED | 故障被 fail-closed/约束，受保护不变量保持 | 业务状态已经恢复到期望结果 |
| L4_RECOVERED | recovery 后经 observation/verifier 证明状态收敛 | 未执行的外部 SDK/provider 也具有相同行为 |
| L5_EXTERNAL | 在锁定的真实上游 SDK/provider/环境执行指定行为并归档证据 | 跨版本、跨环境无条件推广 |

Core Lab 使用 deterministic fixture 是为了隔离机制，而不是模拟真实 provider 性能。任何延迟、QPS、成功率或 benchmark 结论只有在固定模型、数据集、资源、并发、缓存、网络区域、重复次数和统计方法后才能对外报告。

## A.2 统一复现记录

每次实验至少保存：代码版本、Python/OS/arch、依赖 lock、完整命令、stdout/stderr、随机种子（若有）、fixture/数据版本、开始/结束时间以及 verifier 结果。外部实验还必须记录 provider/region/model、上游 tag/commit 和网络依赖。安装或 `--version` 成功最多只能算环境准备，不能代替行为验证。

## A.3 三层模型运行方式

本书把“系统机制是否正确”和“某个模型是否擅长任务”分开测量。默认 Core Lab 使用 `ScriptedModel` 或确定性 policy，使状态机、权限、持久化和 verifier 在无网络、无密钥、arm64/x86_64 上都能回归；这不是伪装成大模型的模拟结果，而是软件机制基线。第二层可接本机小模型，第三层才接云模型。更换模型只能改变 proposal，不能绕过 action schema、policy、effect gate 与 verifier。

安装可选客户端时单独创建环境，避免改变发布锁：

```bash
python -m venv .venv-provider
source .venv-provider/bin/activate
python -m pip install openai
```

OpenAI 官方 Python SDK 的 `OpenAI()` 默认从进程环境读取 `OPENAI_API_KEY`；不要把密钥写入源码、`.env` 示例值、notebook 输出、trace、截图或 CI artifact。模型名也不应硬编码为“最新”，而应由运行者选择其账户实际可用、并在实验记录中锁定的模型：

```bash
export OPENAI_API_KEY='在本机安全设置，禁止提交'
export OPENAI_MODEL='填写账户实际可用且已记录版本的模型'
```

```python
import os
from openai import OpenAI

client = OpenAI()  # SDK 从环境读取 OPENAI_API_KEY
response = client.responses.create(
    model=os.environ["OPENAI_MODEL"],
    input=[
        {"role": "developer", "content": "只提出候选动作；最终成功由外部 verifier 决定。"},
        {"role": "user", "content": "给出下一步动作及理由。"},
    ],
)
proposal_text = response.output_text
```

这段代码只取得模型 proposal；生产代码还必须把 proposal 解码为有版本的结构化 action，再经过本书 Runtime。接口语义以[OpenAI Responses API 官方参考](https://developers.openai.com/api/reference/cli/resources/responses/methods/create)为准。

本地小模型可通过所选推理服务器的 OpenAI-compatible endpoint 接入同一 adapter。是否支持 Responses、JSON Schema、tool call、并行调用和流式事件要逐项探测，不能因为 URL 兼容就推断语义兼容：

```bash
export OPENAI_BASE_URL='http://127.0.0.1:8000/v1'
export OPENAI_API_KEY='local-placeholder'
export OPENAI_MODEL='本地服务器实际加载的模型标识'
```

```python
client = OpenAI(
    base_url=os.environ["OPENAI_BASE_URL"],
    api_key=os.environ["OPENAI_API_KEY"],
)
```

建议先用能在机器内存中稳定运行的小型 instruct/coder 模型验证 schema、工具选择与恢复路径，再用目标云模型做能力评测。报告至少分开给出：机制测试结果、模型任务成功率、无效结构率、工具误选率、成本、时延以及人工复核率；不能用离线 Core Lab 的 PASS 替代模型质量结论。
