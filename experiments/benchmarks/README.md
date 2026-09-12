# 外部 Agent Benchmark 执行契约

这里的 `catalog.json` 只声明**可执行契约**，不声明成绩。预检通过也不等于 benchmark 通过。

## 编码 Agent：SWE-bench Lite smoke

固定官方 harness commit，先用 gold patch 验证 Docker 评测环境，再让官方 `swebench infer`/mini-SWE-agent 对同一真实 issue 生成补丁，最后交给官方 evaluator 执行仓库测试。0 分仍是有效的真实结果；缺少 evaluator 原始文件则不是结果。

本地预检：

```bash
python scripts/preflight_external_benchmarks.py --benchmark swebench-lite-agent-smoke
```

## Browser Agent：WebArena smoke

WebArena 必须使用自托管站点，而非公开 demo；执行前须重置站点、生成 task config、取得登录 cookie。仓库只提交任务范围和官方 runner commit，站点未就绪时必须保持 `NOT_EXECUTED_IN_THIS_RELEASE`。

本地预检：

```bash
python scripts/preflight_external_benchmarks.py --benchmark webarena-official-agent-smoke
```

完整运行入口是 `.github/workflows/external-agent-benchmarks.yml`，它要求带 `agent-benchmark` 标签的隔离 self-hosted runner。密钥只作为进程环境变量注入；日志步骤禁止 `set -x`，证据中只记录变量是否存在，不记录值。
