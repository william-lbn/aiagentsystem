# Build System 1.1.2 — Quarto/Pandoc AST 长期出版基线

Build System 1.1.2 的目标是把出版系统冻结成一个可长期维护的 Docs-as-Code / Course-as-Code 基线：**一份 canonical source tree，通过标准 AST publisher 生成书籍、网站、实验手册和发布包。**

## 1. Canonical sources

| 内容 | 权威源 | 约束 |
|---|---|---|
| 构建元数据 | `course.toml` | 版本、publisher、Quarto version/image、SOURCE_DATE_EPOCH、规模期望 |
| 书籍顺序 | `book/zh/SUMMARY.md` | 唯一章节/附录顺序 |
| 正文 | `book/zh/chapters/*.md` + appendices | 不在 Quarto YAML 复制正文结构 |
| 图 | `book/assets/diagrams/*.dot` | DOT canonical；SVG/PNG/PDF 为派生物 |
| Core Labs | `labs/core/` + `examples/` + `src/agentlab/` | 本地可复现机制验证 |
| External sources | `integrations/SOURCE_LOCK.json` | course pin/latest observed/status 分离 |
| Python deps | `pyproject.toml` + `uv.lock` | runtime/build/test/publish 精确解析图 |

`.build/quarto/**/_quarto.yml`、`book/build/`、`site/`、`workbook/build/`、PPTX 和 Release ZIP 全部是生成物。

## 2. 出版架构

```text
SUMMARY + Markdown + Labs + DOT + course.toml
                    |
                    v
          prepare_quarto.py
                    |
        +-----------+-----------+
        |           |           |
        v           v           v
   Quarto Book   Quarto Site  Quarto Workbook
     PDF/EPUB       HTML       PDF/EPUB/HTML
        \           |           /
         \          |          /
          +---- Pandoc AST ----+
                    |
           format-specific filter
          SVG(HTML/EPUB) / PDF(LaTeX)
```

Canonical release publisher 是 Quarto 1.11.1。Quarto Book project 生成主书/Workbook 的 PDF 与 EPUB，Quarto Website project 生成完整课程站点；由于 HTML Book 是多页网站而发布契约还需要一份可下载的整书 HTML，该单文件由同一 Quarto 发行版的 `quarto pandoc` 生成。`scripts/publish.py --engine pandoc` 是开发机 compatibility publisher，也走 Pandoc AST；它不是另一套 Markdown renderer。

## 3. 为什么 Book / Website / Workbook 分成三个 Quarto project

三者共享 canonical sources，但输出职责不同：主书需要 40 章 + 6 附录；课程站点需要章节、附录和 80 Labs 的导航；Workbook 只组织 80 Labs。三个 `_quarto.yml` 均由脚本临时生成，因此不会形成第二套内容源。

## 4. Dependency bootstrap

```bash
make bootstrap
make bootstrap-check
```

`make bootstrap` 从 `uv.lock` 创建/同步环境；`make bootstrap-check` 离线验证 lock 与 `pyproject.toml` 一致。lock 同时记录 sdist 与受支持平台 wheel 的哈希；有匹配 wheel 时不要求本地原生编译工具，只有回退到 sdist 的平台才需要相应 C/C++ 或 Rust toolchain。外部 framework integrations 不并入核心 build lock，避免出版基线随上游 Agent 框架生态频繁漂移。

## 5. 构建入口

```bash
make toolchain          # 本地 Pandoc compatibility toolchain
make build              # compatibility book/site/workbook + slides
make build-canonical    # 要求 Quarto 1.11.1
make core-validate      # 80 Labs + pytest + 69 examples
make qa                 # 所有内容/输出 QA
make validate           # 本地完整门
make validate-canonical # Quarto canonical 完整门
make release            # deterministic local release
```

## 6. PDF 图与字体

HTML/EPUB 保留 SVG；PDF/XeLaTeX 通过 `scripts/filters/pdf_diagrams.lua` 在 AST 层把 SVG 引用替换为 Graphviz 生成的 vector PDF，避免依赖隐式 SVG raster converter。中文正文/无衬线/代码字体分别使用 Noto Serif CJK SC、Noto Sans CJK SC、Noto Sans Mono CJK SC。

## 6.1 PDF 书籍语义

PDF/Workbook 明确使用 `ctexbook`，Pandoc H1 以 chapter 语义处理。主书通过 `book_structure.lua` 把 canonical part heading 转成 `\part`、在附录边界进入 `\appendix`；print TOC depth 固定为 1，而 HTML/Website 可保留 depth 3。`book-style.tex` 负责章/节排版、页眉页脚、heading keep-with-next 与代码折行，不承载正文。

`qa_pdf_structure.py` 验证 7 个 part page、40 个唯一 chapter start page、A–F appendices、紧凑总目录和确定性 PDF metadata；`qa_workbook_structure.py` 验证 80 个 Lab ID 与 A/B 区分。

## 7. QA 不变量

Build System 1.1.2 不检查某个内容版本字符串。QA 检查的是长期不变量：章节/附录/Lab 数量、SUMMARY 顺序、本地链接、DOT→SVG 可重建、Quarto generated config、PDF/EPUB/HTML 结构、站内链接、PPTX 页数、语义证据块、source locks 和 repository contract。构建/QA 脚本不得硬编码 release-specific literal。

## 8. Reproducible release

`course.toml` 固定 `SOURCE_DATE_EPOCH`。Release ZIP 固定 entry timestamp、Unix file mode、路径排序与 compression level。`scripts/verify_reproducible_release.py` 在两个隔离临时目录中重复生成 release 并比较 SHA-256；`verify_source_clean.py` 确保 source-only 包不泄漏生成产物。

`verify_same_host_clean_rebuild.py` 还会把 SOURCE-CLEAN 独立解包两次，以调用验证器的同一 Python 和两个隔离 uv cache 冷启动；网络 bootstrap 最多进行三次有界重试，同一 cache 仅复用已校验的局部下载，包身份与 hash 仍由 `uv.lock` 决定。lxml、Pillow、python-pptx 与 Pydantic Core 必须先通过原生导入审计，随后 book/site/workbook/slides 的发布表面逐文件比对。它证明的是**同主机、同工具链的干净重建等价**。真正跨时间的 canonical Quarto bit-for-bit reproducibility 仍依赖完整 builder environment；仓库提供 digest-pinned Quarto base image 与 `Dockerfile.builder` 作为 CI hardening 路径，但不把本地 Docker 可用性当作内容正确性的替代物。

Canonical 预检调用 `quarto pandoc --version`，检查 Quarto 随发行版内置、且被 `quarto render` 实际调用的 Pandoc；宿主系统里同名的旧 Pandoc 不属于 canonical publisher。镜像显式安装 `ctex`、`fancyhdr`、`fvextra`、`needspace`、`enumitem`、`ragged2e` 与 `caption`，并在 build layer 用 `kpsewhich` 验证对应文件；Quarto PDF 的 `latex-auto-install` 被关闭，渲染期缺包会直接失败，不能静默修改工具链。PDF 构建同时把 Babel 的 LaTeX 语言名显式覆盖为 `chinese`，避开包含连字符的 `chinese-hans` 控制序列问题，但文档与可访问性元数据仍保持标准 IETF 标签 `zh-Hans`。Quarto base digest 与 Python lock 已固定，但 APT/CTAN 仍是构建时解析的仓库，因此不能宣称跨时间 bit-hermetic；tag release 必须保存实际 `dpkg` inventory、TeX Live package revision inventory、最终 image inspect 与工具链版本。

## 9. 冻结规则

Build System 1.1.2 发布后，正常内容迭代只允许更新 canonical content/code/labs/source locks 和必要的依赖锁。除非出现明确的出版能力、安全或可复现性缺口，不再新增自研 Markdown parser、不再复制章节结构、不再把版本常量写进 QA。
