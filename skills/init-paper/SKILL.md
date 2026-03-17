---
description: "初始化论文项目骨架（多出版社+多方法类型 + Git + GitHub + structure/三层文档系统 + Writing Pipeline）"
---

## 核心使命

从零搭建一个标准化的 LaTeX 论文项目，支持多出版社（Elsevier/ASCE/Emerald）和多研究方法类型（博弈论/问卷/面板回归），复用经过验证的最佳实践：structure/ 三层文档系统、版本化 idea 管理、编译自动化。

## 参数解析

从 `$ARGUMENTS` 提取论文编号 `{ID}`（如 `zl15`）。

- `$ARGUMENTS` 的值为：`$ARGUMENTS`
- 如果为空或未提供，使用 AskUserQuestion 询问论文编号
- `{ID}` 将用于所有命名：`{ID}.bib`、`paper_{ID}`（GitHub 仓库名）等

## 前置检查

1. 确认当前工作目录为项目根目录
2. 检查目录是否为空（或仅有 `.git`）。如果已有文件，**停止并询问用户**，避免覆盖已有项目
3. 确认 `gh` CLI 可用（`gh --version`）
4. 确认 `latexmk` 可用（`latexmk --version`）

## 出版社选择

使用 AskUserQuestion 询问目标出版社：

```
目标出版社？
  [1] elsevier — Elsevier期刊（AiC, IJPM, JCP等）· elsarticle · 双盲
  [2] asce — ASCE期刊（JME, JCEM等）· ascelike · 单盲
  [3] emerald — Emerald期刊（ECAM等）· standard article + natbib · 双盲
```

记录用户选择为 `{PUBLISHER}`（elsevier / asce / emerald）。

出版社决定：
- manuscript.tex 的文档类和格式
- cls/bst 文件
- submission/ 目录的文件组成

## 方法类型选择

使用 AskUserQuestion 询问研究方法类型：

```
研究方法类型？
  [1] game-theory — 博弈论建模+数值仿真
  [2] survey-sem — 问卷调查+SEM/回归
  [3] panel-regression — 二手数据+面板回归
```

记录用户选择为 `{METHOD_TYPE}`（game-theory / survey-sem / panel-regression）。

方法类型决定：
- 是否创建 `structure/5_simulation/` 目录（仅 game-theory）
- 使用哪套 methodology/results/progress 模板
- CLAUDE.md 中 structure 表格的内容

## 模板目录

```
~/.claude/skills/init-paper/
├── common/              # 通用章节模板（所有方法共享）
│   ├── introduction.md.tmpl
│   ├── literature.md.tmpl
│   └── discussion.md.tmpl
├── game-theory/         # 博弈论专用模板
│   ├── methodology.md.tmpl
│   ├── results.md.tmpl
│   ├── simulation.md.tmpl
│   └── progress.md.tmpl
├── survey-sem/          # 问卷专用模板
│   ├── methodology.md.tmpl
│   ├── results.md.tmpl
│   └── progress.md.tmpl
├── panel-regression/    # 面板回归专用模板
│   ├── methodology.md.tmpl
│   ├── results.md.tmpl
│   └── progress.md.tmpl
├── publishers/          # 出版社专用模板
│   ├── elsevier/        # manuscript + submission files
│   ├── asce/
│   └── emerald/
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
6. 将 CLAUDE.md.tmpl 中的 `{SUBMISSION_FILES}` 替换为对应出版社的投稿附件列表：
   - elsevier → `coverletter.tex, declaration.tex, highlights.tex, titlepage.tex`
   - asce → `coverletter.tex`
   - emerald → `coverletter.tex, titlepage.tex`
7. 写入目标路径

### {STRUCTURE_TABLE} 替换内容

**game-theory**：
```
| 子目录 | 内容 | 核心文件 |
|:-------|:-----|:---------|
| `0_global/` | 跨章节纲领、进度追踪、参考PDF库 | `idea.md`（纲领）, `progress.md`（进度）, `pandoc_header.tex` |
| `1_introduction/` | Introduction 素材 | `introduction.md` |
| `2_literature/` | 文献综述素材、RIS、检索报告 | `literature.md` |
| `3_methodology/` | 模型设定（符号、假设、框架） | `methodology.md` |
| `4_results/` | 均衡求解、命题、比较静态 | `results.md` |
| `5_simulation/` | 仿真脚本、图表 | `simulation.md` |
| `6_discussion/` | Discussion 素材 | `discussion.md` |
```

**survey-sem**：
```
| 子目录 | 内容 | 核心文件 |
|:-------|:-----|:---------|
| `0_global/` | 跨章节纲领、进度追踪、参考PDF库 | `idea.md`（纲领）, `progress.md`（进度）, `pandoc_header.tex` |
| `1_introduction/` | Introduction 素材 | `introduction.md` |
| `2_literature/` | 文献综述素材、RIS、检索报告 | `literature.md` |
| `3_methodology/` | 研究设计（框架、问卷、抽样） | `methodology.md` |
| `4_results/` | 信效度、模型拟合、假设检验 | `results.md` |
| `5_discussion/` | Discussion 素材 | `discussion.md` |
```

**panel-regression**：
```
| 子目录 | 内容 | 核心文件 |
|:-------|:-----|:---------|
| `0_global/` | 跨章节纲领、进度追踪、参考PDF库 | `idea.md`（纲领）, `progress.md`（进度）, `pandoc_header.tex` |
| `1_introduction/` | Introduction 素材 | `introduction.md` |
| `2_literature/` | 文献综述素材、RIS、检索报告 | `literature.md` |
| `3_methodology/` | 研究设计（数据、变量、模型） | `methodology.md` |
| `4_results/` | 回归结果、稳健性检验 | `results.md` |
| `5_discussion/` | Discussion 素材 | `discussion.md` |
```

## 执行步骤

严格按以下顺序执行，每步完成后确认无误再进入下一步。

---

### Step 1: Git 初始化 + GitHub 仓库

```bash
git init  # 如果尚未初始化
gh repo create zylen97/paper_{ID} --private --source=. --remote=origin
```

---

### Step 2: 创建目录结构

**game-theory**：
```bash
mkdir -p structure/0_global structure/1_introduction structure/2_literature structure/3_methodology structure/4_results structure/5_simulation/figures structure/6_discussion submission .vscode .claude/hooks
```

**survey-sem / panel-regression**：
```bash
mkdir -p structure/0_global structure/1_introduction structure/2_literature structure/3_methodology structure/4_results structure/5_discussion submission .vscode .claude/hooks
```

---

### Step 3: 创建所有骨架文件

**所有 `{ID}` → 实际论文编号，`{TODAY}` → 当前日期，`{STRUCTURE_TABLE}` → 方法类型表格。**

#### 项目配置文件

| # | 模板文件 | 目标路径 |
|---|---------|---------|
| 1 | `CLAUDE.md.tmpl` | `CLAUDE.md` |
| 2 | `gitignore.tmpl` | `.gitignore` |
| 3 | `vscode-settings.json.tmpl` | `.vscode/settings.json` |
| 4 | `claude-settings.json.tmpl` | `.claude/settings.local.json` |
| 5 | `unicode-guard.sh.tmpl` | `.claude/hooks/unicode-guard.sh` |

#### LaTeX 文件（根据 {PUBLISHER} 选择）

| # | 模板文件 | 目标路径 |
|---|---------|---------|
| 6 | `publishers/{PUBLISHER}/manuscript.tex.tmpl` | `manuscript.tex` |
| 7 | `bib.tmpl` | `{ID}.bib` |
| 8 | `latexmkrc.tmpl` | `latexmkrc` |

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
| 17 | `{METHOD_TYPE}/progress.md.tmpl` | `structure/0_global/progress.md` |
| 18 | `{METHOD_TYPE}/methodology.md.tmpl` | `structure/3_methodology/methodology.md` |
| 19 | `{METHOD_TYPE}/results.md.tmpl` | `structure/4_results/results.md` |

**仅 game-theory**：

| # | 模板文件 | 目标路径 |
|---|---------|---------|
| 20 | `game-theory/simulation.md.tmpl` | `structure/5_simulation/simulation.md` |

#### Discussion（目录编号因方法类型而异）

| 方法类型 | 模板文件 | 目标路径 |
|---------|---------|---------|
| game-theory | `common/discussion.md.tmpl` | `structure/6_discussion/discussion.md` |
| survey-sem | `common/discussion.md.tmpl` | `structure/5_discussion/discussion.md` |
| panel-regression | `common/discussion.md.tmpl` | `structure/5_discussion/discussion.md` |

#### 设置 hook 可执行权限

```bash
chmod +x .claude/hooks/unicode-guard.sh
```

#### 空目录占位（仅 game-theory）

```bash
touch structure/5_simulation/figures/.gitkeep
```

---

### Step 4: 编译验证

```bash
latexmk manuscript.tex
```

确认输出 `manuscript.pdf` 且无致命错误。

---

### Step 5: Git 初始提交 + 推送

根据 {PUBLISHER} 调整 git add 的文件列表：

**elsevier**：
```bash
git add .gitignore CLAUDE.md manuscript.tex {ID}.bib latexmkrc elsarticle.cls elsarticle-harv.bst structure/ submission/ .vscode/ .claude/
```

**asce**：
```bash
git add .gitignore CLAUDE.md manuscript.tex {ID}.bib latexmkrc ascelike.cls ascelike.bst structure/ submission/ .vscode/ .claude/
```

**emerald**：
```bash
git add .gitignore CLAUDE.md manuscript.tex {ID}.bib latexmkrc structure/ submission/ .vscode/ .claude/
```

```bash
git commit -m "Initialize {ID} paper skeleton ({PUBLISHER} + {METHOD_TYPE})"
git push -u origin main
```

---

### Step 6: 输出摘要

向用户报告：

1. **创建完成** — 列出所有生成的文件（树状图）
2. **GitHub 仓库** — `https://github.com/zylen97/paper_{ID}`（Private）
3. **出版社** — `{PUBLISHER}`
4. **研究方法类型** — `{METHOD_TYPE}`
5. **编译验证** — ✅ 通过
6. **项目结构说明**：
   - `structure/` 三层文档系统：idea.md（纲领）→ 各章节md（素材）→ manuscript.tex（产出）
   - 研究推进顺序见 `structure/0_global/progress.md`
7. **下一步操作建议**：
   - 填写 `CLAUDE.md` 中的 TODO 项目信息（英文标题、方法、目标期刊）
   - 开始撰写 `structure/0_global/idea.md`（研究纲领）
   - idea 确定后运行 `/lit-plan` 规划文献检索方向
   - WoS 检索完成后运行 `/lit-review` 分析筛选文献
