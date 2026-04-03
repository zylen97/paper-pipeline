---
description: "投稿前终检：引用完整性、自引率、格式合规、图表规范、符号一致性（Pre-submission Checklist）"
---

# Pre-Submit — 投稿前终检

全自动扫描 manuscript.tex 和关联文件，生成红黄绿三级检查报告。**不修改任何文件**，只报告问题。

**输入** `$ARGUMENTS`：无参数。直接运行 `/pre-submit`。

---

## 步骤 0：上下文加载

### 0.1 读取项目配置

- 读取 `CLAUDE.md` → 提取：
  - `{MAIN_TEX}`（主文件路径，通常为 `manuscript.tex`）
  - `{BIB_FILE}`（bib 文件路径）
  - `{TARGET_JOURNAL}`（目标期刊）
  - `{PUBLISHER}`（出版社）
  - `{METHOD_TYPE}`（方法类型）
- Fallback：Glob(`*.tex`) 查找含 `\documentclass` 的文件；Glob(`*.bib`) 查找 bib 文件

### 0.2 读取文件

- 读取 `{MAIN_TEX}` 全文
- 读取 `{BIB_FILE}` 全文
- 扫描 `submission/` 目录下的所有 `.tex` 文件（coverletter, titlepage, highlights, declaration 等）
- 检查 `drafts/method_audit_report.md` 是否存在（用于流程完整性检查）

---

## 步骤 1：引用完整性检查

### 1.1 正文 → bib 方向（幽灵引用）

扫描 `{MAIN_TEX}` 中所有 `\citep{}`、`\citet{}`、`\cite{}` 命令，提取所有 citation key。

对每个 key，检查是否存在于 `{BIB_FILE}` 中：
- **存在** → ✅
- **不存在** → 🔴 幽灵引用（Ghost Citation）：正文引了但 bib 里没有

### 1.2 bib → 正文方向（孤立条目）

对 `{BIB_FILE}` 中的每个条目，检查其 key 是否出现在 `{MAIN_TEX}` 正文中：
- **出现** → ✅
- **未出现** → 🟡 孤立条目（Orphan Entry）：bib 里有但正文没引

### 1.3 bib 条目质量

对每个 bib 条目检查：
- **缺少必填字段**：title, author, year, journal/booktitle → 🔴
- **年份格式异常**：非 4 位数字、含字母、与 key 中年份不一致 → 🟡
- **重复条目**：相同 title+year 或相同 DOI → 🟡
- **DOI 缺失**：article 类型无 doi 字段 → 🟢（建议补充）

### 1.5 bib 深度清洗检查

#### 期刊名一致性
扫描所有 `journal` 字段，检查同一期刊是否有不同写法：
- 缩写 vs 全称混用（如 "J. Manag. Eng." vs "Journal of Management in Engineering"）→ 🟡
- 大小写不一致（如 "automation in construction" vs "Automation in Construction"）→ 🟡
- 列出所有检测到的期刊名变体组，供用户统一

#### Citation key 格式
检查所有 key 是否符合项目规范（`auth.lower + year + shorttitle(1,1)`，见 CLAUDE.md）：
- 不符合规范 → 🟢（仅提示，不阻断——可能是外部导入的条目）

#### 年份分布
统计引用文献的年份分布，报告：
- 近 5 年占比
- 最早年份和最晚年份
- 如果近 5 年占比 < 30% → 🟡（部分期刊要求引用新文献）

### 1.4 自引率

统计正文中引用的 unique citation key 总数 `{TOTAL_REFS}`。

从 CLAUDE.md 中提取作者列表（全名，如 "Zilun Wang"）。对 bib 中每个被引用的条目，检查其 author 字段是否包含任一作者的**全名**（"姓, 名" 或 "名 姓" 格式均需匹配）。仅姓氏匹配不算自引——常见姓氏（如 Wang, Zhang, Li, He, Hu）会导致严重误报。

自引率 = `{SELF_REFS}` / `{TOTAL_REFS}` × 100%

- ≤ 10% → ✅ 正常
- 10-15% → 🟡 偏高，建议关注
- \> 15% → 🔴 过高，编辑可能质疑

> **注意**：自引率计算需要从 CLAUDE.md 中提取作者全名列表。如果 CLAUDE.md 中没有作者信息，跳过此项并提示用户补充。

---

## 步骤 2：格式合规检查

### 2.1 字数统计

使用 `texcount` 或手动估算（正文单词数，排除公式、表格、参考文献）：

```bash
texcount -1 -sum -merge {MAIN_TEX} 2>/dev/null || echo "texcount not available"
```

如果 `texcount` 不可用，用正则粗估（去除 LaTeX 命令后的单词数）。

报告：
- 正文字数（估算）
- 参考文献数量（bib 条目数）
- 图表数量（`\begin{figure}` + `\begin{table}` 计数）

### 2.2 结构完整性

检查 `{MAIN_TEX}` 中是否包含以下必备结构：

| 检查项 | 匹配模式 | 缺失级别 |
|--------|---------|---------|
| Abstract | `\begin{abstract}` | 🔴 |
| Keywords | `\begin{keyword}` 或 `\keywords` | 🔴 |
| Introduction | `\section{Introduction}` 或类似 | 🔴 |
| Conclusion | `\section{Conclusion` | 🔴 |
| References | `\bibliography` 或 `\begin{thebibliography}` | 🔴 |
| Acknowledgments | `\section*{Acknowledg` 或类似 | 🟡 |
| CRediT / Author contributions | `CRediT` 或 `Author contribution` | 🟡（部分期刊必须） |
| Declaration of interest | `declaration` 或 `conflict` | 🟡 |

### 2.3 TODO / 占位符残留

扫描 `{MAIN_TEX}` 和 `submission/` 下所有 `.tex` 文件，查找：
- `TODO`（大小写不敏感）
- `XXX`、`FIXME`、`TBD`
- `\textcolor{red}`（红色标记文本）
- `???`、`000`（占位数字）

每处命中 → 🔴（投稿前必须清除）

### 2.4 LaTeX 编译检查

```bash
latexmk {MAIN_TEX} 2>&1 | tail -50
```

检查输出中的：
- `Warning` → 🟡（列出前 10 条）
- `Error` / `!` → 🔴
- `Overfull \hbox` 超过 20pt → 🟡（可能导致文字溢出页边距）
- 编译成功且无 Error → ✅

---

## 步骤 3：符号与术语一致性

### 3.1 符号一致性

扫描正文中的数学符号（`$...$` 和 `\(...\)` 内的内容），检查：
- 同一概念是否在不同位置使用了不同符号（如 $\lambda$ vs $\Lambda$）
- 符号是否在首次使用时有定义

**实现方式**：提取所有行内公式，按 section 分组，对比各 section 中出现的符号集合，标记不一致之处。

> 这是启发式检查，可能有误报。标记为 🟡，提醒用户人工确认。

### 3.2 术语一致性

检查常见的术语不一致：
- 同一概念的不同写法（如 "game-theoretic" vs "game theoretic"，"decision-making" vs "decision making"）
- 缩写首次出现时是否有全称定义
- 缩写使用是否一致（定义后是否始终用缩写而非全称）

---

## 步骤 4：图表检查

### 4.1 图表引用完整性

扫描所有 `\label{fig:*}` 和 `\label{tab:*}`，检查是否在正文中被 `\ref{}`/`\autoref{}`/`\cref{}` 引用：
- 有 label 无 ref → 🟡 未引用的图表
- 有 ref 无 label → 🔴 引用了不存在的图表

### 4.2 图表编号连续性

检查 Figure 和 Table 编号是否连续（1, 2, 3...），有无跳号。

### 4.3 图片文件检查

扫描所有 `\includegraphics{}` 的文件路径：
- 文件不存在 → 🔴
- 文件存在但格式不推荐（如 `.jpg` 用于线图、`.bmp`）→ 🟡（建议用 PDF/EPS 矢量图或 300dpi PNG）

---

## 步骤 5：submission/ 文件检查

### 5.1 Cover letter

检查 `submission/coverletter.tex`：
- 不存在 → 🔴
- 存在但含 TODO → 🔴（未填写）
- 存在且无 TODO → ✅

### 5.2 其他投稿附件

根据 `{PUBLISHER}` 检查必要文件：

**elsevier**：coverletter, declaration, highlights, titlepage
**asce**：coverletter
**emerald**：coverletter, titlepage
**sage**：coverletter
**ieee**：coverletter
**wiley**：coverletter, titlepage

缺少必要文件 → 🔴

---

## 步骤 6：贡献一致性检查

从 `{MAIN_TEX}` 中提取两处贡献声称，交叉比对：

### 6.1 提取贡献点

- **Introduction 声称**：扫描 Introduction section 中含 "contribut" 的段落，提取声称的贡献列表
- **Discussion 声称**：扫描 Discussion section 中含 "contribut" / "implicat" 的段落，提取展开论述的贡献列表
- **idea.md 声称**（如存在）：从 `structure/0_global/idea.md` 提取贡献点

### 6.2 一致性检查

对比三处来源，检查：
- **Introduction 声称的贡献在 Discussion 中有对应展开吗？** 有声称但无展开 → 🟡（空头支票）
- **Discussion 展开的贡献在 Introduction 中有预告吗？** 有展开但无预告 → 🟡（突兀）
- **贡献数量是否一致？** Introduction 说 3 个，Discussion 只展开 2 个 → 🟡
- **贡献措辞是否匹配？** 提取关键短语对比，严重不一致 → 🟡

> 这是语义级检查，基于关键词和段落级匹配，可能有误判。标记为 🟡，供用户确认。

---

## 步骤 7：流程完整性检查

检查本项目是否按 pipeline 顺序执行了各关键步骤：

| 检查项 | 检查方式 | 缺失级别 |
|--------|---------|---------|
| method-audit | `drafts/method_audit_report.md` 存在？ | 🟡 |
| method-audit 红色项已清 | report 中无未修复的 🔴 | 🟡 |
| writing brief | `drafts/writing_brief.md` 存在？ | 🟢 |

---

## 步骤 8：生成报告

写入前确保目录存在（`/finalize` Phase 4 可能已清理 `drafts/`）：`mkdir -p drafts/`

将所有检查结果写入 `drafts/pre_submit_report.md`：

```markdown
# Pre-Submission Checklist — {PAPER_TITLE}

> Generated: {date}
> Target journal: {TARGET_JOURNAL} ({PUBLISHER})
> Manuscript: {MAIN_TEX}

---

## Summary

| 级别 | 数量 | 说明 |
|------|------|------|
| 🔴 MUST-FIX | {n} | 投稿前必须修复 |
| 🟡 WARNING | {n} | 建议修复 |
| 🟢 INFO | {n} | 供参考 |

## Statistics

| 指标 | 数值 |
|------|------|
| 正文字数（估算） | {n} |
| 参考文献数量 | {n} |
| 图表数量 | {n} Fig + {n} Tab |
| 自引率 | {n}% ({self}/{total}) |

---

## 🔴 MUST-FIX

### 1. [引用] 幽灵引用：{key}
正文 L{行号} 引用了 `{key}`，但 bib 中不存在。

### 2. [格式] TODO 残留
{文件名} L{行号}: `{匹配内容}`

...

## 🟡 WARNING

### 1. [引用] 孤立条目 ({n} 条)
以下 bib 条目未在正文中引用：
- `{key1}` — {title} ({year})
- `{key2}` — {title} ({year})

### 2. [符号] 可能的符号不一致
Section 3 使用 `$\lambda$`，Section 4 使用 `$\Lambda$`（同一概念？）

...

## 🟢 INFO

### 1. [引用] {n} 条 bib 条目缺少 DOI
...

---

## Verdict

{如果 🔴 = 0}:
✅ **READY TO SUBMIT** — 未发现必须修复的问题。建议检查 🟡 项后提交。

{如果 🔴 > 0}:
❌ **NOT READY** — 请先修复 {n} 条 🔴 问题。
```

### 展示报告

将报告完整展示给用户。**不执行任何修改**——pre-submit 是只读检查工具，修改由用户自行决定。

如果 🔴 = 0，提示：
```
✅ 检查通过！论文已准备好投稿。

更新项目阶段为 submitted？
(1) 确认（更新 CLAUDE.md 阶段为 submitted）
(2) 暂不更新（还有其他调整）
```

AskUserQuestion 等待用户确认。用户选 (1) → 在 CLAUDE.md 中更新 `状态: submitted`、`更新时间: {TODAY}`。用户选 (2) → 不更新。

> 这是 pre-submit 唯一的写操作——仅更新项目阶段元数据，不改稿件内容。

如果 🔴 > 0，提示：
```
❌ 发现 {n} 条必须修复的问题，请处理后重新运行 /pre-submit。
```

---

## 全局约束

### 只读
**pre-submit 不修改任何文件。** 只扫描、只报告。修改是用户的事。

### 幂等
可以反复运行。每次运行覆盖上一次的 `drafts/pre_submit_report.md`。

### 容错
单项检查失败（如 texcount 不可用、图片路径无法访问）不阻断整个流程，标记该项为 `⚠️ 检查跳过：{原因}` 并继续。
