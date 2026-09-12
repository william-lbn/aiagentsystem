# AI Agent Systems Course

[![CI](https://github.com/william-lbn/aiagentsystem/actions/workflows/ci.yml/badge.svg)](https://github.com/william-lbn/aiagentsystem/actions/workflows/ci.yml)
[![CodeQL](https://github.com/william-lbn/aiagentsystem/actions/workflows/codeql.yml/badge.svg)](https://github.com/william-lbn/aiagentsystem/actions/workflows/codeql.yml)
[![Release](https://img.shields.io/github/v/release/william-lbn/aiagentsystem)](https://github.com/william-lbn/aiagentsystem/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

**《AI Agent Systems：从模型、Runtime、协议到生产可靠性》**是一套面向工程师、研究者和高校课程的中文开源 Agent Systems 教材。课程从系统问题出发，将模型接口、Context、Tool、RAG/Memory、MCP/A2A、Runtime/Harness、Coding/Browser/Data/Research Agent、Multi-Agent、Evaluation、Security、Durable Execution、Recovery、Production、Post-training 与 Self-improvement 串成连续学习路径。

当前公开基线是 **内容版本 `v1.0.0` + Build System `1.1.1`**。知识与协议观察截止日期为 **2026-09-11（Asia/Shanghai）**。这是教材、实验与参考实现 monorepo，不是面向 PyPI 发布的通用 Agent SDK；`pyproject.toml` 用于锁定仓库运行环境。

项目坚持区分本地 deterministic fixture、官方 SDK 实跑、真实 provider、真实 benchmark 与生产环境。没有外部证据的部分会明确标记为 `DEFINED` 或 `NOT_EXECUTED`，不会生成替代分数。

## 1. Build System 1.1.1 原则

本仓库采用 **Single Source, Multiple Artifacts**：

- `course.toml`：课程版本、出版器、工具链和期望规模的唯一构建元数据源；
- `book/zh/SUMMARY.md`：书籍顺序唯一来源；
- `book/zh/chapters/*.md` 与附录 Markdown：正文权威源；
- `book/assets/diagrams/*.dot`：技术图权威源；
- `src/agentlab/`、`examples/`、`labs/`：代码与实验权威源；
- `integrations/SOURCE_LOCK.json`：外部框架/研究复现的版本证据；
- `uv.lock`：核心 Python runtime/build/test/publish 依赖锁。

`_quarto.yml` 不进入内容事实源。`scripts/prepare_quarto.py` 会从 `course.toml + SUMMARY.md + Markdown/Labs` 在 `.build/quarto/` 中生成 Book、Website、Workbook 三个临时 Quarto project。

Canonical publisher 是 **Quarto 1.11.1**；开发机没有 Quarto 时，可使用明确标记的 **Pandoc compatibility publisher**。PDF/EPUB/HTML/Website/Workbook 均经过 Pandoc/Quarto AST，不再使用自研 Markdown→ReportLab 或 Markdown→HTML parser。

完整设计见 [`docs/BUILD_SYSTEM.md`](docs/BUILD_SYSTEM.md)。

### PDF / Workbook 出版规范

Build System 1.1.1 使用 `ctexbook` 书籍语义而不是 `article`：独立书名页、紧凑总目录、7 个篇章分隔页、40 个章节强制章首新页、附录 A–F 原生编号；PDF 总目录只到“篇/章/附录”，HTML/Website 保留更深的局部导航。代码块通过 `fvextra` 自动折行，长行不会越过纸张边界；80 个 Lab 的 A/B 标题带稳定 ID 与“正常路径/故障注入”后缀，Workbook 目录不会再出现同名实验。

## 2. 当前已验证规模

- 40 章 + 6 附录；
- 80 个 Core Labs（每章 Normal + Fault）；
- 40 个章节示例 + 29 个支撑示例，合计 69 个 Python examples；
- 114 项 pytest，语句/分支综合覆盖率 **90%**（门槛 85%）；
- 100 个 external source locks；
- 80 张 canonical DOT 技术图；
- 主书 PDF / HTML / EPUB，当前 PDF **462 页 A4**；
- Course Website **127 个 HTML 页面**；
- 80-Lab Workbook PDF / HTML / EPUB，当前 PDF **164 页 A4**；
- **90 页 PPTX**。

完整实跑证据见 [`VALIDATION_REPORT.md`](VALIDATION_REPORT.md)。

## 3. Fresh bootstrap

需要 Python 3.11–3.13 和 `uv`。首次安装依赖需要访问公开 Python package index：

```bash
git clone https://github.com/william-lbn/aiagentsystem.git
cd aiagentsystem
make bootstrap
make bootstrap-check
```

`make bootstrap` 使用 `uv sync --locked --all-groups --no-install-project`，不会依赖已有 `.venv`。本仓库不再维护第二份 QA requirements 清单；核心 Python 构建/测试依赖以 `pyproject.toml + uv.lock` 为准。需要外部 API、浏览器、Node 或第三方框架的 upstream integrations 仍由 `integrations/` 与 source locks 单独管理，不混入出版系统锁。

## 4. 本机构建

先检查 Pandoc/XeLaTeX/Graphviz/Poppler/CJK 字体，以及从锁定 sdist 冷启动所需的 Cargo/Rust：

```bash
make toolchain
```

然后构建全部教学产物：

```bash
make build
```

默认 `make build` 运行经过本基线实测的 Pandoc compatibility 路径。生成：

```text
book/build/ai-agent-systems-course-v1.0.0.{pdf,html,epub}
site/index.html + 126 个子页面
workbook/build/agent-systems-lab-workbook-v1.0.0.{pdf,html,epub}
slides/AI-Agent-Systems-Course-v1.0.0.pptx
```

有 Quarto 1.11.1 时可以运行 canonical 路径：

```bash
make build-canonical
make validate-canonical
```

## 5. 验证与 Release

完整本地质量门：

```bash
make validate
```

覆盖：dependency lock consistency、toolchain、80 Core Labs、pytest、69 examples、出版构建、Quarto project generation QA、Source QA、Book QA、PDF Structure QA、Workbook Structure QA、Slides QA、Output QA、Content Semantics QA、Repository QA。

正式本地基线包：

```bash
make release
```

Release builder 使用 `SOURCE_DATE_EPOCH`、固定 ZIP entry timestamp、file mode、排序和压缩参数，并执行两次独立打包 SHA-256 比较与 SOURCE-CLEAN 污染检查。随后把 SOURCE-CLEAN 解包两次，以同一解释器、相互隔离的空依赖 cache 和锁定的 runtime + `publish` 依赖重建 book/site/workbook/slides；每次 bootstrap 都先导入审计 lxml/Pillow/python-pptx/Pydantic Core，再逐文件比较发布表面哈希。`quality` 工具不参与出版物重建，它们由 `make validate` 的 lint、coverage、dependency-audit 与索引门禁独立验证。

## 6. Docker / CI 的定位

`Dockerfile.builder`、`make release-container` 与 SHA-pinned GitHub Actions 已作为 canonical CI hardening 接口保留，但 **Docker 不是本地内容验证的阻断条件**。本机确认 Docker daemon `27.4.0` 为 `linux/arm64`；拉取固定 Quarto base digest 时 GHCR/daemon 链路连续 EOF/无响应，因此没有把 canonical container rebuild 写成已完成。Pandoc compatibility release 已完成两次独立冷 cache 的 SOURCE-CLEAN 重建并比对 134 个文件；跨 Ubuntu 22.04/24.04 workflow 尚无 compare artifact，所以仍不宣称 cross-host reproducibility。外部 benchmark 同样只完成 pinned execution contract，没有 SWE-bench/WebArena 分数。

六项 scoped 官方实现证据、真实 benchmark 的未运行边界与下一阶段验收标准见 [`docs/L5_EXTERNAL_EVIDENCE_AUDIT_2026-09-11.md`](docs/L5_EXTERNAL_EVIDENCE_AUDIT_2026-09-11.md)。

## 7. 长期演进规则

后续版本应遵循 Semantic Versioning，从 canonical sources 修改并执行 `make validate`。不要从 PDF、PPTX、Website 或 Release ZIP 反向修改内容；不要新增第二套章节列表、版本常量或 Markdown parser。如果出版系统本身没有新的硬性需求，应保持 Build System 1.1.1 的出版契约冻结。

## 8. 开源协作与安全

- 许可证和第三方边界：[`LICENSE`](LICENSE)、[`LICENSING.md`](LICENSING.md)、[`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md)
- 贡献与治理：[`CONTRIBUTING.md`](CONTRIBUTING.md)、[`GOVERNANCE.md`](GOVERNANCE.md)、[`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md)
- 安全报告：[`SECURITY.md`](SECURITY.md)；漏洞不得提交到公开 issue
- 支持入口：[`SUPPORT.md`](SUPPORT.md)
- 学术引用：[`CITATION.cff`](CITATION.cff)
- 发布流程：[`RELEASING.md`](RELEASING.md)

正式 release 由 tag 触发的 GitHub Actions 生成，包含校验和、CycloneDX Python SBOM 与 GitHub artifact attestation。本地生成物不直接提交到 `main`。
