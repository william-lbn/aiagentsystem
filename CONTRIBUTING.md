# Contributing to AI Agent Systems

感谢你改进教材、运行时、协议实验和复现基础设施。项目接受 issue、勘误、文档、代码、测试与外部证据贡献。

## 开始之前

1. 阅读 [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md) 与 [`SECURITY.md`](SECURITY.md)。安全漏洞不要提交公开 issue。
2. 较大的功能、章节重构或新依赖请先创建 issue，说明目标、证据边界和维护成本。
3. Fork 仓库并从 `main` 创建主题分支；一个 PR 只解决一类问题。

## 本地环境

需要 Python 3.11–3.13、`uv==0.10.0`。完整出版还需要 Pandoc、XeLaTeX、Graphviz、Poppler、Noto CJK 字体和 Rust/Cargo；也可以使用锁定的 Docker builder。

```bash
git clone https://github.com/william-lbn/aiagentsystem.git
cd aiagentsystem
uv sync --locked --all-groups --no-install-project
make core-validate
make source-qa source-lock-qa l5-evidence-qa external-benchmark-contract-qa repo-qa
```

影响书籍、图、Workbook、Slides 或 Website 的修改还必须运行：

```bash
make validate
```

## 内容与实验标准

- 理论结论必须连接到系统不变量、失败模式或可证伪假设。
- 示例不得只是 Hello World；至少包含真实业务状态、边界条件和机器可判定结果。
- 新实验必须区分 fixture、官方实现、真实 provider、真实 benchmark 和生产环境，不得把低等级证据外推到高等级声明。
- 外部框架、协议与论文必须记录版本、官方来源、观察日期和 claim ceiling。
- 需要凭据的实验必须通过环境变量或 CI secret 注入；严禁提交 token、cookie、账号、真实用户数据或未脱敏轨迹。
- 新的副作用路径必须说明幂等键、UNKNOWN outcome、重试和恢复语义。

## Pull Request 要求

- 描述问题、方案、风险和已运行的验证命令。
- 新增行为必须有测试；修复缺陷应包含回归测试。
- 不提交 `.venv/`、`.build/`、`dist/`、生成站点或本机缓存。
- 保持提交粒度清晰，避免混入无关格式化。
- 所有提交必须包含 DCO sign-off：`git commit -s`。其含义见 [`DCO`](DCO)。

维护者将根据正确性、证据质量、安全性、兼容性、可维护性和项目范围审查贡献。CI 通过是合并的必要条件，但不是充分条件。
