---
description: "初始化论文项目骨架（多出版社+多方法类型 + Git + GitHub + structure/三层文档系统 + Writing Pipeline）"
---

## 核心使命

从零搭建一个标准化的 LaTeX 论文项目，支持多出版社（Elsevier/ASCE/Emerald/SAGE/IEEE/Wiley）和多研究方法类型（建模/问卷/面板回归），复用经过验证的最佳实践：structure/ 三层文档系统、版本化 idea 管理、编译自动化。

## 参数解析

从 `$ARGUMENTS` 提取论文编号 `{ID}`（如 `zy15`）。

- `$ARGUMENTS` 的值为：`$ARGUMENTS`
- 如果为空或未提供，使用 AskUserQuestion 询问论文编号
- `{ID}` 将用于所有命名：`{ID}.bib`、`paper_{ID}`（GitHub 仓库名）、`{ID}_latexfile/`（内层目录名）等

此外，使用 AskUserQuestion 询问**外层项目文件夹名** `{OUTER_DIR}`（如 `zy18_供应链数字化转型溢出_IJPE`）。

## 项目目录结构（两层嵌套）

论文项目采用两层嵌套结构：

```
{OUTER_DIR}/                  ← 外层项目文件夹（不纳入 git）
├── raw literature/           ← 原始文献 PDF（不纳入 git）
└── {ID}_latexfile/           ← 内层 LaTeX 项目（git 仓库）
    ├── .git/
    ├── CLAUDE.md
    ├── manuscript.tex
    ├── structure/
    └── ...
```

- **外层文件夹**：放原始文献等非 git 管理内容，在 `{PROJECT_PARENT_DIR}` 下创建（见下方说明）
- **内层 `{ID}_latexfile/`**：git 仓库，包含所有 LaTeX 文件、structure/ 三层文档系统、submission/ 等
- 后续所有步骤（Step 2-5）的工作目录均为 `{ID}_latexfile/`

### 项目创建位置 `{PROJECT_PARENT_DIR}`

项目创建位置取决于当前工作目录：

- **如果当前在 idea-mine 批次目录**（自动检测：目录下同时存在 `ideas/`、`idea-review/`、`papers/`）：当前目录不适合建项目。根据全局 CLAUDE.md 中的科研项目目录配置，自动推导 `{PROJECT_PARENT_DIR}`：
  - 如果当前路径包含 `Zylen paper`：`{PROJECT_PARENT_DIR}` = 路径中 `Zylen paper` 对应的完整目录（如 `~/Dropbox/02-Research/Zylen paper`）
  - 如果当前路径包含 `_gym paper`：`{PROJECT_PARENT_DIR}` = 路径中 `_gym paper` 对应的完整目录
  - 其他情况：使用 AskUserQuestion 询问项目创建位置
- **如果当前不在 batch 目录**：`{PROJECT_PARENT_DIR}` = 当前工作目录

## 前置检查

1. 检测当前目录是否为 idea-mine 批次目录（`ideas/` + `idea-review/` + `papers/` 同时存在），确定 `{PROJECT_PARENT_DIR}`
2. 检查 `{PROJECT_PARENT_DIR}/{OUTER_DIR}` **是否已存在**。如果已存在，**停止并询问用户**，避免覆盖
3. 确认 `gh` CLI 可用（`gh --version`）
4. 确认 `latexmk` 可用（`latexmk --version`）

## 出版社选择

使用 AskUserQuestion 询问目标出版社：

```
目标出版社？
  [1] elsevier — Elsevier期刊（AiC, IJPM, JCP, SCS等）· elsarticle · 双盲
  [2] asce — ASCE期刊（JME, JCEM等）· ascelike · 单盲
  [3] emerald — Emerald期刊（ECAM等）· standard article + natbib · 双盲
  [4] sage — SAGE期刊（Urban Studies, PMJ等）· sagej · 双盲
  [5] ieee — IEEE期刊（IEEE TEM等）· IEEEtran · 双盲
  [6] wiley — Wiley期刊（BSE等）· WileyNJDv5 · 双盲/三盲
```

记录用户选择为 `{PUBLISHER}`（elsevier / asce / emerald / sage / ieee / wiley）。

出版社决定：
- manuscript.tex 的文档类和格式
- cls/bst 文件
- submission/ 目录的文件组成

## 方法类型选择

使用 AskUserQuestion 询问研究方法类型：

```
研究方法类型？
  [1] modeling — 建模类方法（博弈论/网络分析/AI/仿真等）
  [2] survey-sem — 问卷调查+SEM/回归
  [3] panel-regression — 二手数据+面板回归
```

记录用户选择为 `{METHOD_TYPE}`（modeling / survey-sem / panel-regression）。

方法类型决定：
- 是否创建 `structure/5_simulation/` 目录（仅 modeling）
- 使用哪套 methodology/results 模板
- CLAUDE.md 中 structure 表格的内容

## Idea-mine 导入（可选）

**自动检测**：如果前置检查中已检测到当前目录为 idea-mine 批次目录，则自动启用导入，`{BATCH_DIR}` = 当前工作目录，跳过下方的询问。

**手动触发**：如果当前目录不是 batch 目录，使用 AskUserQuestion 询问：

```
是否从 idea-mine 批次导入源材料？
  [1] 是 — 从 idea-mine 批次复制源论文、paper note、idea 文件和审稿评分
  [2] 否 — 跳过，从空白 idea.md 开始
```

如果选择"是"且当前不在 batch 目录，额外询问 `{BATCH_DIR}`（idea-mine 批次目录的绝对路径）。

**无论哪种方式启用导入，都需收集以下参数**：

- `{PAPER_ID}`：源论文编号（如 `12`，对应 P12）
- `{IDEA_SHORT}`：idea 简称（如 `绿色创新溢出`，用于匹配文件名中的 `idea_{PAPER_ID}_{IDEA_SHORT}_*.md`）

### 导入内容与目标位置

所有导入内容放入 `{ID}_latexfile/structure/0_global/idea-mine-ref/` 子目录，与 `idea.md` 同级，作为立项参考资料（纳入 git，随项目版本管理）：

```
{OUTER_DIR}/
├── raw literature/           ← 源论文 PDF 复制到这里
└── {ID}_latexfile/
    └── structure/0_global/
        ├── idea.md           ← 从选中的 idea 文件重组写入
        └── idea-mine-ref/    ← idea-mine 产出复制到这里
            ├── paper-note.md
            ├── idea_12_绿色创新溢出_IJPE.md
            ├── idea_12_绿色创新溢出_JCP.md
            ├── idea_12_绿色创新溢出_...md
            ├── review_IJPE_P12.md
            ├── review_JCP_P12.md
            └── review_..._P12.md
```

### 导入操作（在 Step 1 创建目录后、Step 2 之前执行）

1. **复制源论文 PDF**：在 `{BATCH_DIR}/papers/` 中根据 `{BATCH_DIR}/paper-notes/` 的文件列表匹配源论文编号对应的 PDF，复制到 `{PROJECT_PARENT_DIR}/{OUTER_DIR}/raw literature/`
   - 匹配方式：`{BATCH_DIR}/paper-notes/` 中的文件按目录顺序排列，第 `{PAPER_ID}` 个文件对应的作者名即为源论文。在 `{BATCH_DIR}/papers/` 中找到同名（仅扩展名不同 `.pdf` vs `.md`）的 PDF 复制

2. **复制 paper note**：将匹配到的 `{BATCH_DIR}/paper-notes/{对应文件名}.md` 复制到 `{PROJECT_PARENT_DIR}/{OUTER_DIR}/{ID}_latexfile/structure/0_global/idea-mine-ref/`

3. **复制所有 idea 文件**：`{BATCH_DIR}/ideas/idea_{PAPER_ID}_{IDEA_SHORT}_*.md`（glob 匹配所有期刊版本），全部复制到 `{PROJECT_PARENT_DIR}/{OUTER_DIR}/{ID}_latexfile/structure/0_global/idea-mine-ref/`

4. **复制所有 review 文件**：`{BATCH_DIR}/idea-review/review_*_P{PAPER_ID}.md`（glob 匹配所有期刊版本），全部复制到 `{PROJECT_PARENT_DIR}/{OUTER_DIR}/{ID}_latexfile/structure/0_global/idea-mine-ref/`

5. **重组写入 idea.md**：读取用户选中的那个 idea 文件（由目标期刊决定，如 `idea_12_绿色创新溢出_IJPE.md`），将其 §1-§5 的内容按 `idea.md.tmpl` 的结构重组写入 `{ID}_latexfile/structure/0_global/idea.md`，映射规则：
   - idea 文件 §1 灵感来源 → idea.md §1 灵感来源 & 参考论文
   - idea 文件 §2 行业背景/Gap/RQ → idea.md §2（行业背景、文献不足、Gap→Objective→RQ 表格）
   - idea 文件 §3 方法论 → idea.md §3 方法论选择论证（只保留方向和论证，具体公式/推导不放）
   - idea 文件 §4 贡献意图 → idea.md §4 贡献意图（理论+实践分开）
   - idea 文件 §5 风险评估 → idea.md §5 风险评估表格

## 模板目录

```
~/.claude/skills/paper-init/
├── common/              # 通用章节模板（所有方法共享）
│   ├── introduction.md.tmpl
│   ├── literature.md.tmpl
│   └── discussion.md.tmpl
├── modeling/            # 建模类方法专用模板
│   ├── methodology.md.tmpl
│   ├── results.md.tmpl
│   └── simulation.md.tmpl
├── survey-sem/          # 问卷专用模板
│   ├── methodology.md.tmpl
│   └── results.md.tmpl
├── panel-regression/    # 面板回归专用模板
│   ├── methodology.md.tmpl
│   └── results.md.tmpl
├── publishers/          # 出版社专用模板
│   ├── elsevier/        # manuscript + submission files
│   ├── asce/
│   ├── emerald/
│   ├── sage/
│   └── ieee/
└── *.tmpl               # 其他通用模板（CLAUDE.md, bib, gitignore 等）
```

创建文件时：
1. 使用 Read 工具读取对应的 `.tmpl` 文件
2. 将内容中的 `{ID}` 替换为实际论文编号
3. 将内容中的 `{TODAY}` 替换为当前日期（YYYY-MM-DD）
4. 将 CLAUDE.md.tmpl 中的 `{STRUCTURE_TABLE}` 替换为对应方法类型的 structure 表格
5. 将 CLAUDE.md.tmpl 中的 `{TEMPLATE_CLASS}` 替换为对应出版社的模板类：
   - elsevier → `Elsarticle (preprint)`
   - asce → `ascelike (Journal)`
   - emerald → `Standard article + natbib`
   - sage → `sagej (Harvard)`
   - ieee → `IEEEtran (journal, onecolumn)`
   - wiley → `WileyNJDv5 (APA, Times1COL)`
6. 将 CLAUDE.md.tmpl 中的 `{SUBMISSION_FILES}` 替换为对应出版社的投稿附件列表：
   - elsevier → `coverletter.tex, declaration.tex, highlights.tex, titlepage.tex`
   - asce → `coverletter.tex`
   - emerald → `coverletter.tex, titlepage.tex`
   - sage → `coverletter.tex`
   - ieee → `coverletter.tex`
   - wiley → `coverletter.tex, titlepage.tex`
7. 将 CLAUDE.md.tmpl 中的 `{TECHNICAL_SECTIONS}` 替换为对应方法类型的技术型章节列表：
   - modeling → `Methodology, Results, Simulation`
   - survey-sem → `Methodology, Results`
   - panel-regression → `Methodology, Results`
8. 写入目标路径

### {STRUCTURE_TABLE} 替换内容

**modeling**：
```
| 子目录 | 内容 | 核心文件 |
|:-------|:-----|:---------|
| `0_global/` | 跨章节纲领、参考PDF库 | `idea.md`（纲领）, `pandoc_header.tex` |
| `1_introduction/` | Introduction 素材 | `introduction.md` |
| `2_literature/` | 文献综述素材、RIS、检索报告 | `literature.md` |
| `3_methodology/` | 模型设定（符号、假设、框架） | `methodology.md`（成稿）, `methodology_dev.md`（过程文件） |
| `4_results/` | 均衡求解、命题、比较静态 | `results.md`（成稿）, `results_dev.md`（过程文件） |
| `5_simulation/` | 仿真脚本、案例数据 | `simulation.md`（成稿）, `simulation_dev.md`（过程文件） |
| `6_discussion/` | Discussion 素材 | `discussion.md` |
| `figures_tables/` | 图表集中管理 | `index.md`（注册表）, `tables.tex`（所有表格）, `figures/`（所有图片） |
```

**survey-sem**：
```
| 子目录 | 内容 | 核心文件 |
|:-------|:-----|:---------|
| `0_global/` | 跨章节纲领、参考PDF库 | `idea.md`（纲领）, `pandoc_header.tex` |
| `1_introduction/` | Introduction 素材 | `introduction.md` |
| `2_literature/` | 文献综述素材、RIS、检索报告 | `literature.md` |
| `3_methodology/` | 研究设计（框架、问卷、抽样） | `methodology.md`（成稿）, `methodology_dev.md`（过程文件） |
| `4_results/` | 信效度、模型拟合、假设检验 | `results.md`（成稿）, `results_dev.md`（过程文件） |
| `5_discussion/` | Discussion 素材 | `discussion.md` |
| `figures_tables/` | 图表集中管理 | `index.md`（注册表）, `tables.tex`（所有表格）, `figures/`（所有图片） |
```

**panel-regression**：
```
| 子目录 | 内容 | 核心文件 |
|:-------|:-----|:---------|
| `0_global/` | 跨章节纲领、参考PDF库 | `idea.md`（纲领）, `pandoc_header.tex` |
| `1_introduction/` | Introduction 素材 | `introduction.md` |
| `2_literature/` | 文献综述素材、RIS、检索报告 | `literature.md` |
| `3_methodology/` | 研究设计（数据、变量、模型） | `methodology.md`（成稿）, `methodology_dev.md`（过程文件） |
| `4_results/` | 回归结果、稳健性检验 | `results.md`（成稿）, `results_dev.md`（过程文件） |
| `5_discussion/` | Discussion 素材 | `discussion.md` |
| `figures_tables/` | 图表集中管理 | `index.md`（注册表）, `tables.tex`（所有表格）, `figures/`（所有图片） |
```

## 执行步骤

严格按以下顺序执行，每步完成后确认无误再进入下一步。

---

### Step 1: 创建项目目录 + Git 初始化 + GitHub 仓库

```bash
# 在 {PROJECT_PARENT_DIR} 下创建外层项目文件夹和内层 LaTeX 项目目录
mkdir -p "{PROJECT_PARENT_DIR}/{OUTER_DIR}/{ID}_latexfile"
mkdir "{PROJECT_PARENT_DIR}/{OUTER_DIR}/raw literature"

# 如果启用 idea-mine 导入，还需创建参考资料目录
mkdir -p "{PROJECT_PARENT_DIR}/{OUTER_DIR}/{ID}_latexfile/structure/0_global/idea-mine-ref"   # 仅当导入时

# 进入内层目录，后续所有操作都在这里
cd "{PROJECT_PARENT_DIR}/{OUTER_DIR}/{ID}_latexfile"
git init
gh repo create zylen97/paper_{ID} --private --source=. --remote=origin
```

---

### Step 1.5: Idea-mine 导入执行（条件步骤，仅当选择导入时执行）

按照上方「Idea-mine 导入」章节的操作 1-4 执行文件复制。操作 5（重组写入 idea.md）在 Step 3 创建骨架文件后执行——因为需要先有 `idea.md.tmpl` 生成的空文件，再用 idea-mine 内容覆盖。

具体：
1. 匹配并复制源论文 PDF → `{PROJECT_PARENT_DIR}/{OUTER_DIR}/raw literature/`
2. 复制 paper note → `{PROJECT_PARENT_DIR}/{OUTER_DIR}/{ID}_latexfile/structure/0_global/idea-mine-ref/`
3. 复制所有 idea 文件（glob `idea_{PAPER_ID}_{IDEA_SHORT}_*.md`）→ `{PROJECT_PARENT_DIR}/{OUTER_DIR}/{ID}_latexfile/structure/0_global/idea-mine-ref/`
4. 复制所有 review 文件（glob `review_*_P{PAPER_ID}.md`）→ `{PROJECT_PARENT_DIR}/{OUTER_DIR}/{ID}_latexfile/structure/0_global/idea-mine-ref/`

> **操作 5（重组写入 idea.md）放在 Step 3 末尾执行**，见 Step 3 末尾的「Idea-mine 内容写入」。

---

### Step 2: 创建目录结构

> 以下命令均在 `{ID}_latexfile/` 内执行。

**modeling**：
```bash
mkdir -p structure/0_global structure/1_introduction structure/2_literature structure/3_methodology structure/4_results structure/5_simulation structure/6_discussion structure/figures_tables/figures data/raw data/processed data/scripts data/models data/results data/robustness submission .claude/hooks
```

**survey-sem / panel-regression**：
```bash
mkdir -p structure/0_global structure/1_introduction structure/2_literature structure/3_methodology structure/4_results structure/5_discussion structure/figures_tables/figures data/raw data/processed data/scripts data/models data/results data/robustness submission .claude/hooks
```

---

### Step 3: 创建所有骨架文件

> 以下所有文件的目标路径均相对于 `{ID}_latexfile/`。

**所有 `{ID}` → 实际论文编号，`{TODAY}` → 当前日期，`{STRUCTURE_TABLE}` → 方法类型表格。**

#### 项目配置文件

| # | 模板文件 | 目标路径 |
|---|---------|---------|
| 1 | `CLAUDE.md.tmpl` | `CLAUDE.md` |
| 2 | `gitignore.tmpl` | `.gitignore` |
| 3 | `claude-settings.json.tmpl` | `.claude/settings.local.json` |
| 4 | `unicode-guard.sh.tmpl` | `.claude/hooks/unicode-guard.sh` |
| 5 | `latex-compile.sh.tmpl` | `.claude/hooks/latex-compile.sh` |

> **注意**：不生成 `.vscode/settings.json`。LaTeX Workshop 配置已在 VS Code 全局 User Settings 中统一管理（onSave 编译、latexmk、outDir、files.exclude 等）。各项目编译差异由 `latexmkrc` 控制。

#### LaTeX 文件（根据 {PUBLISHER} 选择）

| # | 模板文件 | 目标路径 |
|---|---------|---------|
| 7 | `publishers/{PUBLISHER}/manuscript.tex.tmpl` | `manuscript.tex` |
| 8 | `bib.tmpl` | `{ID}.bib` |

#### manuscript.tex 方法类型适配（写入 manuscript.tex 后立即执行）

manuscript.tex 模板中 §3/§4 使用通用占位。写入后，根据 `{METHOD_TYPE}` 替换 section 名称和 subsection 结构：

**modeling**：
```latex
\section{Research method and modeling process}
\subsection{Research method}
% TODO: Write content here

\subsection{Modeling process}
% TODO: Write content here

\section{Equilibrium analysis}
\subsection{Equilibrium analysis}
% TODO: Write content here

\subsection{Comparative analysis}
% TODO: Write content here

\section{Numerical analysis}
\subsection{Numerical simulation}
% TODO: Write content here

\subsection{Simulation results}
% TODO: Write content here

\section{Discussion}
```

**panel-regression**：
```latex
\section{Research methods}
\subsection{Sampling and data collection}
% TODO: Write content here

\subsection{Measures}
% TODO: Write content here

\subsection{Methods of analysis}
% TODO: Write content here

\section{Results}
\subsection{Descriptive statistics and correlations}
% TODO: Write content here

\subsection{Hypothesis testing}
% TODO: Write content here

\subsection{Robustness checks}
% TODO: Write content here

\section{Discussion}
```

**survey-sem**：
```latex
\section{Methodology}
\subsection{Data collection}
% TODO: Write content here

\subsection{Bias mitigation and evaluation}
% TODO: Write content here

\subsection{Questionnaire development}
% TODO: Write content here

\subsection{Measures}
% TODO: Write content here

\subsection{Analytical methods}
% TODO: Write content here

\section{Results}
\subsection{Reliability and validity}
% TODO: Write content here

\subsection{Hypothesis testing}
% TODO: Write content here

\subsection{Robustness checks}
% TODO: Write content here

\section{Discussion}
```

即：用上面的对应块**整体替换** manuscript.tex 中从 `\section{Methodology}` 到 `\section{Discussion}`（不含）的内容。所有出版社模板均使用 `\section{Methodology}` 作为统一锚点。

#### submission/ 投稿附件（根据 {PUBLISHER} 选择）

**elsevier**：

| # | 模板文件 | 目标路径 |
|---|---------|---------|
| 9 | `publishers/elsevier/coverletter.tex.tmpl` | `submission/coverletter.tex` |
| 10 | `publishers/elsevier/declaration.tex.tmpl` | `submission/declaration.tex` |
| 11 | `publishers/elsevier/highlights.tex.tmpl` | `submission/highlights.tex` |
| 12 | `publishers/elsevier/titlepage.tex.tmpl` | `submission/titlepage.tex` |

**asce**：

| # | 模板文件 | 目标路径 |
|---|---------|---------|
| 9 | `publishers/asce/coverletter.tex.tmpl` | `submission/coverletter.tex` |

**emerald**：

| # | 模板文件 | 目标路径 |
|---|---------|---------|
| 9 | `publishers/emerald/coverletter.tex.tmpl` | `submission/coverletter.tex` |
| 10 | `publishers/emerald/titlepage.tex.tmpl` | `submission/titlepage.tex` |

**sage**：

| # | 模板文件 | 目标路径 |
|---|---------|---------|
| 9 | `publishers/sage/coverletter.tex.tmpl` | `submission/coverletter.tex` |

**ieee**：

| # | 模板文件 | 目标路径 |
|---|---------|---------|
| 9 | `publishers/ieee/coverletter.tex.tmpl` | `submission/coverletter.tex` |

**wiley**：

| # | 模板文件 | 目标路径 |
|---|---------|---------|
| 9 | `publishers/wiley/coverletter.tex.tmpl` | `submission/coverletter.tex` |
| 10 | `publishers/wiley/titlepage.tex.tmpl` | `submission/titlepage.tex` |

#### cls/bst 文件（根据 {PUBLISHER} 复制）

**elsevier**：
```bash
EXISTING=$(find ~/Library/CloudStorage/Dropbox -name "elsarticle.cls" -maxdepth 8 -print -quit 2>/dev/null)
if [ -n "$EXISTING" ]; then
  cp "$EXISTING" .
  cp "$(dirname "$EXISTING")/elsarticle-harv.bst" . 2>/dev/null
fi
if [ ! -f elsarticle.cls ]; then
  TEXLIVE_CLS=$(kpsewhich elsarticle.cls 2>/dev/null)
  TEXLIVE_BST=$(kpsewhich elsarticle-harv.bst 2>/dev/null)
  [ -n "$TEXLIVE_CLS" ] && cp "$TEXLIVE_CLS" .
  [ -n "$TEXLIVE_BST" ] && cp "$TEXLIVE_BST" .
fi
```

**asce**：
```bash
EXISTING=$(find ~/Library/CloudStorage/Dropbox -name "ascelike.cls" -maxdepth 8 -print -quit 2>/dev/null)
if [ -n "$EXISTING" ]; then
  cp "$EXISTING" .
  cp "$(dirname "$EXISTING")/ascelike.bst" . 2>/dev/null
fi
```

**emerald**：无专用 cls/bst，不复制。

**sage**：
```bash
EXISTING=$(find ~/Library/CloudStorage/Dropbox -name "sagej.cls" -maxdepth 8 -print -quit 2>/dev/null)
if [ -n "$EXISTING" ]; then
  cp "$EXISTING" .
  cp "$(dirname "$EXISTING")/SageH.bst" . 2>/dev/null
fi
if [ ! -f sagej.cls ]; then
  TEXLIVE_CLS=$(kpsewhich sagej.cls 2>/dev/null)
  TEXLIVE_BST=$(kpsewhich SageH.bst 2>/dev/null)
  [ -n "$TEXLIVE_CLS" ] && cp "$TEXLIVE_CLS" .
  [ -n "$TEXLIVE_BST" ] && cp "$TEXLIVE_BST" .
fi
```

**ieee**：
```bash
EXISTING=$(find ~/Library/CloudStorage/Dropbox -name "IEEEtran.cls" -maxdepth 8 -print -quit 2>/dev/null)
if [ -n "$EXISTING" ]; then
  cp "$EXISTING" .
  cp "$(dirname "$EXISTING")/IEEEtran.bst" . 2>/dev/null
fi
if [ ! -f IEEEtran.cls ]; then
  TEXLIVE_CLS=$(kpsewhich IEEEtran.cls 2>/dev/null)
  TEXLIVE_BST=$(kpsewhich IEEEtran.bst 2>/dev/null)
  [ -n "$TEXLIVE_CLS" ] && cp "$TEXLIVE_CLS" .
  [ -n "$TEXLIVE_BST" ] && cp "$TEXLIVE_BST" .
fi
```

**wiley**：
```bash
EXISTING=$(find ~/Library/CloudStorage/Dropbox -name "WileyNJDv5.cls" -maxdepth 8 -print -quit 2>/dev/null)
if [ -n "$EXISTING" ]; then
  cp "$EXISTING" .
  cp "$(dirname "$EXISTING")/wileyNJD-APA.bst" . 2>/dev/null
fi
if [ ! -f WileyNJDv5.cls ]; then
  TEXLIVE_CLS=$(kpsewhich WileyNJDv5.cls 2>/dev/null)
  TEXLIVE_BST=$(kpsewhich wileyNJD-APA.bst 2>/dev/null)
  [ -n "$TEXLIVE_CLS" ] && cp "$TEXLIVE_CLS" .
  [ -n "$TEXLIVE_BST" ] && cp "$TEXLIVE_BST" .
fi
```

#### structure/ 通用文件

| # | 模板文件 | 目标路径 |
|---|---------|---------|
| 13 | `idea.md.tmpl` | `structure/0_global/idea.md` |
| 14 | `pandoc_header.tex.tmpl` | `structure/0_global/pandoc_header.tex` |
| 15 | `common/introduction.md.tmpl` | `structure/1_introduction/introduction.md` |
| 16 | `common/literature.md.tmpl` | `structure/2_literature/literature.md` |

#### structure/ 方法相关文件（根据 {METHOD_TYPE} 选择）

| # | 模板文件 | 目标路径 |
|---|---------|---------|
| 17 | `{METHOD_TYPE}/methodology.md.tmpl` | `structure/3_methodology/methodology.md` |
| 18 | `{METHOD_TYPE}/methodology_dev.md.tmpl` | `structure/3_methodology/methodology_dev.md` |
| 19 | `{METHOD_TYPE}/results.md.tmpl` | `structure/4_results/results.md` |
| 20 | `{METHOD_TYPE}/results_dev.md.tmpl` | `structure/4_results/results_dev.md` |

**仅 modeling**：

| # | 模板文件 | 目标路径 |
|---|---------|---------|
| 21 | `modeling/simulation.md.tmpl` | `structure/5_simulation/simulation.md` |
| 22 | `modeling/simulation_dev.md.tmpl` | `structure/5_simulation/simulation_dev.md` |

#### Discussion（目录编号因方法类型而异）

| 方法类型 | 模板文件 | 目标路径 |
|---------|---------|---------|
| modeling | `common/discussion.md.tmpl` | `structure/6_discussion/discussion.md` |
| survey-sem | `common/discussion.md.tmpl` | `structure/5_discussion/discussion.md` |
| panel-regression | `common/discussion.md.tmpl` | `structure/5_discussion/discussion.md` |

#### 图表管理文件（所有方法类型通用）

| # | 操作 | 目标路径 |
|---|------|---------|
| 20 | 直接创建空注册表 | `structure/figures_tables/index.md` |
| 21 | 直接创建空表格文件 | `structure/figures_tables/tables.tex` |
| 22 | 空目录占位 | `structure/figures_tables/figures/.gitkeep` |

**index.md 初始内容**：
```markdown
# 图表注册表 — {ID}

> 所有图片存放于 `figures/` 子目录，所有表格统一写在 `tables.tex` 中。
> 定稿时将 `tables.tex` 内容贴到 manuscript.tex 末尾。

---

## Figures

| 编号 | 文件名 | 标题 | 所属章节 | 生成方式 | 素材来源 | 状态 |
|:--:|:------|:-----|:--------|:---------|:--------|:--:|

---

## Tables

| 编号 | 标题 | 所属章节 | 内容来源 | 状态 |
|:--:|:-----|:--------|:--------|:--:|

---

## 说明

- **状态定义**: planned → drafted → in-manuscript → finalized
- **Figure 文件命名**: `figXX_shortname.pdf`
- **tables.tex**: 所有表格的 LaTeX 代码统一存放，定稿时贴到 manuscript.tex 末尾
- 新增/修改图表时，必须同步更新此注册表
```

**tables.tex 初始内容**：
```latex
% tables.tex -- {ID} all tables in one file
% Paste content to the end of manuscript.tex when finalizing
```

#### 设置 hook 可执行权限

```bash
chmod +x .claude/hooks/unicode-guard.sh .claude/hooks/latex-compile.sh
```

#### Idea-mine 内容写入（条件步骤，仅当选择导入时执行）

此步骤对应「Idea-mine 导入」章节的操作 5。在 Step 3 所有模板文件创建完成后执行：

读取用户选中的 idea 文件（目标期刊对应的版本，如 `{PROJECT_PARENT_DIR}/{OUTER_DIR}/{ID}_latexfile/structure/0_global/idea-mine-ref/idea_{PAPER_ID}_{IDEA_SHORT}_{TARGET_JOURNAL}.md`），按以下映射关系重组内容，**覆盖写入**已由模板生成的 `structure/0_global/idea.md`：

| idea 文件章节 | → idea.md 章节 | 处理方式 |
|:-------------|:--------------|:---------|
| §1 灵感来源 | §1 灵感来源 & 参考论文 | 保留主论文摘要 + 迁移动机 + 迁移方向选择 |
| §2 行业背景 | §2 行业背景与实践难题 | 直接迁移 |
| §2 Gap 分析 | §2 文献不足（简述） | 压缩为每个 Gap 1-2 句话的简述 |
| §2 RQ | §2 Gap→Objective→RQ 表格 | 重组为表格形式，从每个 Gap 提炼 Objective |
| §3 方法论 | §3 方法论选择论证 | 只保留方法选择的论证和总体框架描述，**不放具体公式和推导细节**（那些属于 methodology_dev.md） |
| §4 贡献意图 | §4 贡献意图 | 拆分为理论贡献和实践贡献，精简为要点式 |
| §5 风险评估 | §5 风险评估 | 转为表格形式（风险/等级/应对） |

> **注意**：idea.md 只放"为什么"和"方向"，不含具体公式/推导/数值。idea 文件 §3 中的详细模型设定（决策变量定义、收益函数、求解过程等）不写入 idea.md，后续填入 `methodology_dev.md`。

---

### Step 4: 编译验证

> 在 `{ID}_latexfile/` 内执行。

```bash
latexmk manuscript.tex
```

确认输出 `manuscript.pdf` 且无致命错误。

---

### Step 5: Git 初始提交 + 推送

> 在 `{ID}_latexfile/` 内执行。

根据 {PUBLISHER} 调整 git add 的文件列表：

**elsevier**：
```bash
git add .gitignore CLAUDE.md manuscript.tex {ID}.bib elsarticle.cls elsarticle-harv.bst structure/ submission/ .claude/
```

**asce**：
```bash
git add .gitignore CLAUDE.md manuscript.tex {ID}.bib ascelike.cls ascelike.bst structure/ submission/ .claude/
```

**emerald**：
```bash
git add .gitignore CLAUDE.md manuscript.tex {ID}.bib structure/ submission/ .claude/
```

**sage**：
```bash
git add .gitignore CLAUDE.md manuscript.tex {ID}.bib sagej.cls SageH.bst structure/ submission/ .claude/
```

**ieee**：
```bash
git add .gitignore CLAUDE.md manuscript.tex {ID}.bib IEEEtran.cls IEEEtran.bst structure/ submission/ .claude/
```

**wiley**：
```bash
git add .gitignore CLAUDE.md manuscript.tex {ID}.bib WileyNJDv5.cls wileyNJD-APA.bst structure/ submission/ .claude/
```

```bash
git commit -m "Initialize {ID} paper skeleton ({PUBLISHER} + {METHOD_TYPE})"
git push -u origin main
```

---

### Step 6: 输出摘要

向用户报告：

1. **创建完成** — 列出两层目录结构的树状图（外层文件夹 + `{ID}_latexfile/` 内部文件）
2. **GitHub 仓库** — `https://github.com/zylen97/paper_{ID}`（Private）
3. **出版社** — `{PUBLISHER}`
4. **研究方法类型** — `{METHOD_TYPE}`
5. **编译验证** — ✅ 通过
6. **项目结构说明**：
   - 外层 `{OUTER_DIR}/`：放原始文献 PDF 等非 git 管理内容（`raw literature/`）
   - 内层 `{ID}_latexfile/`：git 仓库，包含 LaTeX 文件和 `structure/` 三层文档系统
   - `structure/` 三层文档系统：idea.md（纲领）→ 各章节md（素材）→ manuscript.tex（产出）
   - 研究推进顺序见 `CLAUDE.md` 中的"研究推进顺序"
7. **Idea-mine 导入报告**（如果执行了导入）：
   - 列出复制到 `raw literature/` 的源论文 PDF 文件名
   - 列出复制到 `idea-mine-ref/` 的所有文件（paper note、idea 文件 × N 个期刊版本、review 文件 × N 个期刊版本）
   - 说明 `idea.md` 已从选中的 idea 文件重组写入，版本号设为 v0.1
8. **下一步操作建议**：

   **如果执行了 idea-mine 导入**：
   - 审阅 `structure/0_global/idea.md`，确认 Gap/RQ/贡献是否需要调整
   - 运行 `/lit-plan` 规划文献检索方向
   - WoS 检索完成后运行 `/lit-review`(筛选) → `/lit-tag`(打标签) → `/lit-pool`(引用池 + 方法论综述)
   - 文献工作流完成后运行 `/idea-refine` 迭代优化 idea 和方法设计，直至满意
   - 填写 _dev.md 过程文件后运行 `/method-audit`（方法论审计 + 结构确认）
   - 审计通过后运行 `/method-end`（从 _dev.md 凝练到成稿 md）
   - 技术型章节：`/method-end` → `/pen-draft`(初稿) → `/pen-polish`(打磨)
   - 叙述型章节：`/pen-outline`(大纲) → `/pen-draft`(初稿) → `/pen-polish`(打磨)
   - 论文主体定稿后运行 `/finalize`(Conclusion → Abstract → Cover Letter) → `/pre-submit`(投稿终检) → 投稿

   **如果未导入（空白项目）**：
   - 填写 `CLAUDE.md` 中的 TODO 项目信息（英文标题、方法、目标期刊）
   - 开始撰写 `structure/0_global/idea.md`（研究纲领）
   - idea 确定后运行 `/lit-plan` 规划文献检索方向
   - 后续同上
