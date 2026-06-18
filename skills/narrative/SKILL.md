---
description: "叙述型章节写作（Introduction / Literature Review / Discussion 三 section 分别支持，按 section= 参数路由）：Introduction 与 Literature Review 先生成/更新 blueprint md 并 checkpoint，再写 manuscript.tex；Discussion 直接基于 Methodology/Results 写 tex。逐子节交互式生成英文段落，用户句子级 review。"
---

# Narrative Workflow — 叙述型章节写作

Introduction 与 Literature Review 先从 `idea.md` 和 citation pools 生成/更新对应 blueprint md，checkpoint 通过后再写入 `manuscript.tex`。Discussion 直接读 `manuscript.tex` 的 Methodology/Results 并写回 `manuscript.tex`。逐子节生成英文段落，用户句子级 review，确认后写入 tex。

**核心原则**：
1. **blueprint-first for Introduction/LR**：`structure/1_introduction/introduction.md` 和 `structure/2_literature/literature.md` 是逻辑合约，先于正文写入；`manuscript.tex` 仍是最终正文正本。
2. **tex-in / tex-out for Discussion**：Discussion 必须锚定实际 Methodology/Results，因此不强制中间 md。
3. **直接生成英文句子**，不走"中文要点 → 翻译"两步——避免信息损耗和机械翻译失真。
4. **句子级 review**：用户在交互中直接看英文句子流，逐句确认/修改/重写——这是最后一轮人工把关。
5. **三 section 路由**：`section=introduction|literature|discussion` 内部走不同的必备元素和文献池策略。

**与相关 skill 的边界**：
- `/method-audit` = 技术型章节（methodology/results/simulation）的写作蓝图来源；本 skill 不动技术型章节
- `/technical` = 技术型章节直接 tex 生成（基于 method-audit 的写作蓝图）
- `/polish` = 段落级语言润色，跑在 `/narrative` 之后人工改完之后（任意时机调用）
- `/finalize` = 收尾时写 Conclusion/Abstract/Cover Letter，不重叠

**输入** `$ARGUMENTS`：`section=introduction|literature|discussion`（必须）

---

## 步骤 0：前置准备

### 0.1 参数解析

提取 `section` 参数，必须为 `introduction` / `literature` / `discussion` 之一。

不在范围 → AskUserQuestion 让用户选择。

设置全局变量 `{SECTION_TYPE}` ∈ {`"intro"`, `"litrev"`, `"discussion"`}。

### 0.2 项目文件路径

- 从 `CLAUDE.md` 获取 `manuscript.tex` 主文件和 `.bib` 文件路径
- Fallback：Glob `*.tex` 找含 `\documentclass` 的主文件（排除 supplementary/appendix/*.cls）
- 记录 `{TEX_PATH}`、`{BIB_PATH}`

### 0.3 Section tree 解析（Python 脚本）

```bash
python3 ~/.claude/skills/shared/tex_section.py section-tree --tex {TEX_PATH}
```

输出 `_section_tree.json`。VERIFY 必须为 PASS。

### 0.4 Section 匹配

```bash
python3 ~/.claude/skills/shared/tex_section.py match-section \
  --tree _section_tree.json --query "{SECTION_TYPE}"
```

输出 `_section_match.json`。从中读取 `{SECTION_NODE}`（顶层 section 节点信息），包括 line range（用于后续写入定位）。

**匹配失败处理**（VERIFY: FAIL）：自动按 IMRaD 顺序在 `\begin{document}` 之后、`\end{document}` / `\bibliography` / `\printbibliography` 之前的合理位置插入空 `\section{...}` 骨架：

| `{SECTION_TYPE}` | 锚点 |
|:---|:---|
| `intro` | `\begin{document}` 之后（abstract 环境之后，如有） |
| `litrev` | `\section{Methodology}` 之前；若无则 `\section{Introduction}` 之后 |
| `discussion` | `\section{Results}` 之后；若 Results 不存在 → 🔴 BLOCK（discussion 不该在 results 前写） |

插入后刷新 section tree（按步骤 0.3 / 0.4 重跑），覆盖 json，再继续。

### 0.5 上下文加载

读取以下 5 类源（仅这些是 skill 信任的输入）：

1. **`structure/0_global/idea.md`** — 全局纲领，提取：
   - 研究主题 / Gap 列表 / RQ 列表 / 理论框架 / 目标期刊 / 创新点
2. **`manuscript.tex` 已有内容** — 提取：
   - 当前 section 已有内容（如有，作为修改基线）
   - 其他 section 的关键句（用于跨章节一致性）
   - `\journal{...}` 或 abstract 中的期刊信息
3. **`structure/2_literature/citation_pool/`** — 引用池：
   - 按标签分组（BG / GAP / METHOD / LR / DISC / COMP）
   - 每条目：citation key + 引用场景 + 分级
   - 含 `master.bib`（步骤 4.3 bib 同步源）
4. **`{BIB_PATH}`** — 项目 bib，验证 citation key 存在性
5. **section 特异源**（按 `{SECTION_TYPE}` 加载）：
   - **intro**：`structure/1_introduction/introduction.md`（若不存在或明显过时，先按 1.0A 生成/更新）
   - **litrev**：`structure/2_literature/literature.md`（若不存在或明显过时，先按 2.0A 生成/更新）
   - **litrev**：`structure/2_literature/direction*report*.md` + `master_report.md` + `*search_plan*.md`（如存在）
   - **discussion**：从 `manuscript.tex` 读 `\section{Methodology}` 和 `\section{Results}` 的实际内容（关键发现、Fig/Table 编号、命题等）

显示加载状态：
```
📂 上下文加载完成：
- 纲领: structure/0_global/idea.md
- manuscript.tex 现状: section "{title}" 现有 {N} 字符
- 引用池: {citation_pool 文件列表}
- 期刊: {journal name}
[仅 litrev]: - 方向报告: {direction reports 列表}
[仅 discussion]: - Methodology / Results 已加载（用于发现回扣）
```

### 0.6 路由判定

```
IF {SECTION_TYPE} == "intro"       → 跳到 步骤 1
IF {SECTION_TYPE} == "litrev"      → 跳到 步骤 2
IF {SECTION_TYPE} == "discussion"  → 跳到 步骤 3
```

每个子模式完成后统一进入 步骤 4（写入）。

---

## 步骤 1：Introduction 子模式

### 1.0A Blueprint 生成/更新（必须）

目标文件：`structure/1_introduction/introduction.md`。

若文件不存在、仍为 TODO 模板、或与 `idea.md` 的 Gap/RQ 明显不一致，先生成/更新 blueprint。blueprint 必须严格从 `idea.md` 和 citation pools 提取信息，不凭空扩展主题。结构：

1. **行业背景与实践难题**：宏观情境 → 研究主题 → 总体性实践挑战。第一段或前两段必须先讲清楚真实实践难题，再进入文献 gap。
2. **Gap段落×N**：每个 Gap 对应一个 RQ；每段按 5 步写清楚：
   - ① 引子：自然过渡到本 Gap 涉及的研究方向；
   - ② 已有成果：现有文献做了什么、发现了什么；
   - ③ Gap：仍未充分解决什么；
   - ④ So what：不解决会带来什么理论/实践问题；
   - ⑤ Objective：本文旨在做什么，必须是陈述句，不是 RQ 问句。
3. **方法论概述与 RQ**：方法如何服务目标，并显式列出 RQ。
4. **贡献**：理论贡献与实践贡献，与 `idea.md` 对齐。
5. **论文结构**：标准 remainder paragraph。

写入正文前展示 blueprint checkpoint：
- 前 1--2 段是否先讲实践问题，再讲文献 gap；
- Gap/RQ/Objective 是否一一映射；
- 每个 Gap 是否包含 5 步；
- citation pool 是否覆盖关键 claim；
- 是否有过度绝对化 claim。

### 1.1 固定子节骨架

Introduction 的子节结构由必备元素决定，不需要用户选择：

| # | Subsection | 字数 | 引用密度 |
|:-:|:---|:---:|:---:|
| 1 | Background | ~250 | 高（≥85%） |
| 2 | Gap | ~400（按 Gap 数量分配，每 Gap 100-150） | 高（≥85%） |
| 3 | Methodology overview & RQ | ~250 | **白名单豁免** |
| 4 | Contributions | ~150 | 低（多为本文论点 `[—]`） |
| 5 | Paper organization | ~50 | 0 |

**总字数硬约束**：1000-1200 词。

### 1.2 Gap 数量适配（与 RQ 数量对齐）

从 `idea.md` `## 2`（或对应 Gap 区块）读取 Gap 数量和 RQ 数量。

- Gap → RQ 通常 1:1 映射
- 若 N:M 多对多，按 RQ 数量展开 Gap 段（每个 RQ 对应至少一个 Gap 段）
- 显示给用户："基于 idea.md，Introduction 将含 {N} 个 Gap 段（对应 {M} 个 RQ）"

### 1.3 各子节英文段落生成

逐子节交互：

```
FOR each subsection IN [Background, Gap1, Gap2, ..., MethodologyOverviewRQ, Contributions, PaperOrganization]:
  1. 主 agent 严格依据 introduction.md blueprint + idea.md + citation pool + 现有 tex，生成该子节英文段落
  2. 严格遵循引用规则:
     - [citep] / [citet] / [—] 标记内嵌（仅 skill 内部使用，最终输出 tex 时只保留 \citep{}/\citet{}）
     - Gap 段必须用 hedge 措辞（见 1.4）
     - 末句陈述句（不允许 RQ 问号）
  3. 显示完整段落（含 \citep{}/\citet{}）+ 引用密度自检结果
  4. AskUserQuestion: 确认 / 修改 / 重写
  5. 用户提出修改 → 主 agent 调整 → 再展示 → 直到确认
END FOR
```

### 1.4 Gap 段 Hedge 措辞硬约束

**禁绝对性声明**：
- ❌ "X is unexplored" / "no prior research" / "the first study to..." / "completely absent"
- ❌ "本文是首个..." / "目前没有任何研究..." / "完全空白"

**用 hedge 表述**：
- ✅ "remains insufficiently explored"
- ✅ "to the best of our knowledge"
- ✅ "few studies have addressed"
- ✅ "represents a notable research gap"

**Gap 段末句必须用陈述句**（标记 `[—]`），不允许直接列 RQ 问号。RQ 问号统一在 "Methodology overview & RQ" 子节中以 `\begin{itemize}` 或编号列表呈现。

**RQ 列表写入硬约定**（步骤 3.1 Discussion 路由的 BLOCK 检测依赖此约定）：
- 用 `\begin{itemize}` 或 `\begin{enumerate}` 包裹，每条 `\item` 含字面问号 `?`
- 必须用 `\textbf{RQ\d:}` 前缀，例如：
  ```
  \begin{itemize}
    \item \textbf{RQ1:} How does X affect Y under condition Z?
    \item \textbf{RQ2:} What mechanisms explain the relationship between X and Y?
  \end{itemize}
  ```

### 1.5 引用密度自检

每个子节生成后自动统计：
- `density` = 含 `\citep` 或 `\citet` 的句子数 / 总句子数
- 目标 ≥85%

**白名单豁免**（标题模糊匹配，不触发自动修复）：
- "Methodology overview / RQ"
- "Contributions"
- "Paper organization"

**不在白名单且 density < 80%** → 自动修复：列出无引用的句子，从 citation pool 匹配补充。修复后重新展示。

### 1.6 子节级 review 完成 → 进入步骤 4

---

## 步骤 2：Literature Review 子模式

### 2.0A Blueprint 生成/更新（必须）

目标文件：`structure/2_literature/literature.md`。

若文件不存在、仍为 TODO 模板、或不能覆盖 Introduction 的 Gap/RQ，先生成/更新 LR blueprint。blueprint 必须包含：

1. **LR 方向结构**：按理论功能/文献流组织，不做 chronological notes；
2. **Gap/RQ 覆盖矩阵**：每个方向对应哪些 Gap/RQ；
3. **引用池使用计划**：每个方向预分配核心 citation keys；
4. **定位表计划**：本文与最相关文献的情境、理论、方法、变量差异。

写入正文前展示 blueprint checkpoint：
- LR 是否覆盖 Introduction 的全部 Gap/RQ；
- 是否按理论功能组织，而不是论文流水账；
- 是否预先安排 `LR/GAP/METHOD/COMP` citation pools；
- 是否包含 literature positioning；
- 是否没有凭空新增不在 `idea.md` 的研究主线。

### 2.1 方向确定（用户交互确认）

读取以下素材：
- direction reports（如有）
- master_report（如有）
- idea.md 的 Gap/RQ
- citation pool（按标签分组）
- manuscript.tex 中 `\section{Introduction}` 的 Gap 段（用于覆盖检查）

**自动提议 N 个方向**（写作风格规则，固定，不让用户改）：

1. **第一个方向 = 研究主题本身**（最大主题）
2. **后续方向 = 围绕主题的子议题**，按文献发展逻辑组织（宏观→微观 / 共识→争议）
3. 每个方向标注对应的 Gap 编号
4. 末方向（最接近核心 Gap）权重 ×1.2 字数
5. 末尾自动加 "Literature positioning"（定位表）作为独立 subsection

输出格式：

```
📚 LR 方向提议（基于 idea.md + {M} 个 direction reports）

| # | 方向标题（英文） | 核心内容 | 对应 Gap | 主要文献来源 |
|:-:|:---|:---|:---:|:---|
| 1 | {title} | {核心} | G{x} | {direction report} |
| 2 | ... | ... | ... | ... |
| + | Literature positioning | 本文 vs {M} 篇最相关文献多维对比 | 全局 | — |

Gap 覆盖检查：G1→{N}, G2→{N}, ...（全覆盖 ✓/✗）

确认这个方向划分？(1) 确认 (2) 调整 (3) 讨论某方向
```

AskUserQuestion 等待用户确认。**循环**：不满意 → 修改 → 再展示 → 直到确认。

记录 `{LR_DIRECTIONS}` = 方向列表。

### 2.2 写作蓝图（每方向）

**LR 内部结构**（比重固定）：

| 部分 | 比重 |
|:---|:---:|
| 综述主体 | ~85% |
| 指出不足 + 连接 Gap | ~15%（约 50 词，2-3 个句子） |

**综述主体内的引用形式**（交替使用）：
- **形式 A（主题驱动）**：`\citep{}`，多文献概括性陈述
- **形式 B（作者驱动）**：`\citet{}`，highlight 单篇文献的具体发现

**落脚规则**：
- 跨行业一般文献 → 综述主体末尾子主题必须落脚到本文研究情境（含至少 3-4 个要点）
- 本文情境直接综述 → 不需额外落脚

为每方向构建写作蓝图：
- 子主题列表 + 每个子主题的引用形式（A/B）
- 从 citation pool 预分配具体 citation keys
- bib 验证 citation key 存在性

展示蓝图（每方向一组）：
```
### 方向 {i}: {title} → G{x}
**比重**: 综述主体 ~85% | 不足+Gap ~15%
**子主题展开**:
- 子主题 A（形式 A）: \citep{key1, key2, key3}
- 子主题 B（形式 B）: \citet{key4} - {贡献摘要}; \citet{key5} - {贡献摘要}
- [落脚] 子主题 C（形式 A/B）: \citep{key6} 或 \citet{key7}
**指出不足**（~50 词）: {基于综述自然引出}
**连接 Gap**: → G{x}
```

AskUserQuestion 让用户确认所有方向蓝图。**循环**：不满意 → 修改 → 再展示 → 直到确认。

### 2.3 各方向英文段落生成

逐方向交互：

```
FOR each {direction} IN {LR_DIRECTIONS}:
  1. 主 agent 基于 2.2 确认的写作蓝图，直接生成英文段落
     - 每个子主题约 3-4 个英文句子
     - 综述主体 + 不足 + Gap 连接句
     - 引用预分配的 citation keys（保留 \citep / \citet 区分）
  2. 显示完整方向段落 + 引用密度自检
  3. AskUserQuestion: 确认 / 修改 / 重写
  4. 循环至确认
END FOR
```

**引用密度目标**：每方向 ≥85%（LR 不豁免）

**字数硬约束**：LR 总字数 1500 词，按各方向 + 末方向 ×1.2 权重分配。

### 2.4 定位表生成

读取 manuscript.tex 是否已有 `\subsection*{Literature positioning}`：
- **不存在** → 从零生成（执行下方步骤 1-4）
- **已存在** → AskUserQuestion：(1) 覆盖重生成（推荐，LR 重写后定位表也应同步）/ (2) 跳过保留 / (3) 基于现有交互式增删

生成步骤：
1. 从 citation pool / direction reports 筛选 5-8 篇最具可比性文献
2. 默认对比维度（可调整）：Method / Context / Level / Node type / Key variables / Key findings
3. 展示候选 + 让用户确认文献选择和维度
4. 确认后生成完整 markdown 表格 → 转换为 LaTeX 表格

定位表写入位置：LR 末尾，作为 `\subsection*{Literature positioning}`（带 `*` 不编号子节），步骤 4.2 整体写入时一并落地。

### 2.5 LR 完成 → 进入步骤 4

---

## 步骤 3：Discussion 子模式

### 3.1 加载 Discussion 必需上下文

**前置依赖检查**（硬约束）：

Discussion 必须基于已写好的 Methodology + Results 才能进行。在加载上下文前先检查：

```
检查 manuscript.tex：
  1. \section{Methodology} 和 \section{Results} 各至少含 1 个 \subsection 且正文 ≥ 300 字符
  2. \section{Introduction} 中能提取至少 1 条 RQ：
     - 含 \begin{itemize} 或 \begin{enumerate} 环境，且含 `\textbf{RQ\d:}` 前缀的 \item 含字面问号 `?`
```

不通过 → 🔴 BLOCK：
```
⚠️ Discussion 需要基于已完成的 Methodology + Results。请先 /technical 完成它们；
   RQ 缺失 → 请先 /narrative section=introduction 写入 Methodology overview & RQ 子节。
```

通过后，除步骤 0.5 已加载的内容外，**额外读取**：
- `manuscript.tex` 的 `\section{Introduction}` 中的 RQ 列表 → `{RQ_LIST}`
- `manuscript.tex` 的 `\section{Literature review}` 全文 → 提取所有 `\citep{...}` / `\citet{...}` keys → `{LR_CITED_REFS}`（用于 discussion 回扣）
- `manuscript.tex` 的 `\section{Methodology}` → 提取模型设定、关键假设、命题
- `manuscript.tex` 的 `\section{Results}` → 提取关键发现、Fig/Table 编号、统计结果
- `citation_pool/DISC.md`（如存在）→ discussion 扩展对话伙伴文献

显示：
```
📂 Discussion 上下文：
- RQ 列表: {N} 个
- LR 已用文献: {M} 个 keys（用于回扣）
- Methodology 关键设定: {模型/假设摘要}
- Results 关键发现: {N} 个（含 Fig/Table 编号）
- DISC 文献池: {K} 个候选扩展引用
```

### 3.2 子节固定三段式

| 子节 | 字数 | 引用密度 | 写作格式 |
|:---|:---:|:---:|:---|
| Discussion on the research questions（按 N 个 RQ 切 subsubsection） | 1000-1500 | 按需，常规约束 | 段落式深度讨论 |
| Theoretical implications | 400-500 | **≤3 引用** | 总起句 + First/Second/Third |
| Practical implications | 400-500 | **尽量 0 引用** | 总起句 + First/Second/Third |

**总字数硬约束**：1800-2500 词。

### 3.3 Discussion on RQ 子节生成（RQ-by-RQ 交互）

```
FOR each RQ IN {RQ_LIST}:
  3.3.1 抽取该 RQ 的相关 results 发现
  3.3.2 推荐"高价值结果"（用户确认）
  3.3.3 直接生成英文段落（用户句子级 review）
  3.3.4 用户确认后进入下一个 RQ
END FOR
```

#### 3.3.1 抽取该 RQ 的相关 results 发现

主 agent 综合 RQ 文本 + Methodology + Results 内容，提取：
- 直接回答 RQ 的核心发现（数值 / 模型解 / 实证结论）
- 相关的 Fig/Table 编号
- 是否有"出其不意"的发现（counterintuitive）
- 是否有"重要"的发现（核心机制揭示）
- 是否有"有意思"的发现（nuanced details）

#### 3.3.2 推荐高价值结果

```
🔍 RQ{i}: "{RQ 文本}"

📊 该 RQ 的所有 results 发现 ({N} 项):
  1. {发现描述} (Fig.X) — [价值: 普通]
  2. {发现描述} (Table Y) — [价值: ⭐ 出其不意 — 与{某文献}预期相反]
  3. {发现描述} — [价值: ⭐ 重要 — 揭示核心机制]
  4. {发现描述} — [价值: 有意思 — 不对称效应]

💡 建议深入讨论: 第 2、3、4 项

确认这个深度讨论清单？(1) 采纳 (2) 增删某项 (3) 自由指定
```

AskUserQuestion 确认。

#### 3.3.3 直接生成英文段落

主 agent 基于已确认的高价值结果清单，直接生成英文段落：

**写作内核**：

```
对每个高价值结果:
  1. 简答 RQ（1-2 句，标 [—]）
  2. 深入讨论（3-5 句）— 必须满足以下两点之一或两点：
     A. **扩展现有文献**: "we extend prior work on X by..."
     B. **与现有文献不同**: "in contrast to prior findings on X..."
     C. **其他深度形式**：理论解释 / 实例印证 / 机制揭示
  3. 必须**回扣 LR 已用文献**（{LR_CITED_REFS}）—— 与综述形成对话闭环
  4. 可扩展引用 DISC 文献池作为新增对话伙伴
  5. 段落小结（如有需要）
```

展示完整 RQ 段落（含 \citep / \citet）+ 引用密度统计 + 文献回扣检查：

```
### 5.1.{i} RQ{i}: {简短主题}

[完整英文段落，约 300-500 词]

📊 引用密度: {N}/{M} = {density}%
🔗 LR 文献回扣: 引用了 {K} 个 LR 已用 keys / 总 LR 文献池 {L} 个 → 回扣率 {K/L}%
🔬 Results 发现锚点: 引用 {Fig.X, Table.Y, ...} ({P} 处)

确认 / 修改某句 / 全段重写？
```

AskUserQuestion 句子级 review。**循环**：不满意 → 改 → 再展示 → 直到确认。

#### 3.3.4 进入下一个 RQ

显示进度："✓ RQ{i}/{N} done"。所有 RQ 完成后进入 3.4。

### 3.4 Theoretical implications 子节生成

#### 3.4.1 自动推荐组织粒度

读取三类信号：
- **目标期刊**（`\journal{}` 或 idea.md）→ 期刊方法论倾向
- **Results 章节核心产出** → 论文贡献类型（工具 / 模型推论 / 实证发现）
- **LR 章节主要对话学科** → 理论根基

输出推荐：
```
🎯 Theoretical implications 粒度推荐

基于:
  - 目标期刊: {journal name}
  - 核心贡献类型: {工具开发 / 模型推论 / 实证发现}
  - LR 主要对话学科: {学科}

建议组织粒度: **{按理论视角 / 按学科对话 / 按技术维度}**
理由: {一句话}

具体 3-4 个论点:
  1. {论点 1 标题}
  2. {论点 2 标题}
  3. {论点 3 标题}

确认？(1) 确认 (2) 调整
```

AskUserQuestion 确认。**循环**：用户选 (2) → 接收调整 → 重新展示 → 直到 (1)。

#### 3.4.2 直接生成英文段落

**写作格式硬约束**：

```
[总起句: 1 句话陈述本研究的整体理论贡献，标 [—]]

First, {论点 1 详述, 2-3 句, 含 0-1 个 \citep}.

Second, {论点 2 详述, 2-3 句, 含 0-1 个 \citep}.

Third, {论点 3 详述, 2-3 句, 含 0-1 个 \citep}.

[可选: Fourth, ...]
```

**字数 400-500 词**，**引用密度 ≤3 个 \citep 总数**。

#### 3.4.3 用户句子级 review

展示 + AskUserQuestion 确认 / 修改 / 重写。循环至确认。

### 3.5 Practical implications 子节生成

#### 3.5.1 自动推荐组织粒度

输出推荐：
```
🎯 Practical implications 粒度推荐

建议组织粒度: **{按利益相关者 / 按工具/工作流 / 按决策情境}**
理由: {基于本文是工具开发 / 模型推论 / 实证发现的不同性质}

具体 3 个建议:
  1. {建议 1 标题}
  2. {建议 2 标题}
  3. {建议 3 标题}

确认？(1) 确认 (2) 调整
```

AskUserQuestion 确认。

#### 3.5.2 直接生成英文段落

**写作格式硬约束**：

```
[总起句: 1 句话, 标 [—]]

First, {建议 1, 3-4 句, 0 个引用}.

Second, {建议 2, 3-4 句, 0 个引用}.

Third, {建议 3, 3-4 句, 可有 1 个 \citep 锚定关键参考}.
```

**字数 400-500 词**，**引用密度尽量 0**（绝对上限 1 个 \citep）。

实践建议必须**具体可操作**，避免空洞 rhetoric：
- ❌ "Project managers should leverage digital tools more effectively."
- ✅ "Project managers should organise project knowledge by source and form before deploying any LLM-assisted decision support; textual assets such as regulations and contract templates should enter a versioned retrieval pool, while computational assets such as schedule estimators should be encoded as parameterised callable functions."

#### 3.5.3 用户句子级 review

展示 + AskUserQuestion 确认 / 修改 / 重写。循环至确认。

### 3.6 Discussion 完成 → 进入步骤 4

---

## 步骤 4：写入 manuscript.tex

所有子节英文段落确认后，写入 manuscript.tex。

### 4.1 写入前最后确认

```
📝 即将写入 {TEX_PATH} 的 \section{...}：

总字数: {N} 词（目标: {target} 词）
总引用: {N_citep} \citep + {N_citet} \citet
新增 bib keys: {list}（将自动同步到项目 bib）

子节预览（每节首句）:
  - {subsection 1}: "{首句..."}"
  - {subsection 2}: "{首句..."}"
  - ...

[discussion 特有]: 文献回扣率: 引用了 {K}/{L} 个 LR 已用 keys

确认写入？(1) 写入 (2) 回退到某子节修改 (3) 取消
```

AskUserQuestion 等待用户最终确认。

### 4.2 写入

用户确认后：

1. 用 Edit 工具替换 `manuscript.tex` 中 `\section{...}` 到下一个 `\section`（或 `\bibliography` / `\printbibliography` / `\end{document}` 中最先出现的一行）之间的内容
2. **保留** `\section{...}` 行本身和 `\label{...}`（如有）
3. 写入新内容（含 `\subsection{}` / `\subsubsection{}` / `\citep{}` / `\citet{}` / 必要的 `\begin{table}` 等）

**LR 特殊处理**：
- 各方向用 `\subsection{}` 编号子节
- 定位表用 `\subsection*{Literature positioning}`（不编号）
- 定位表内含 `\begin{table}[!htbp] ... \end{table}`

**Discussion 特殊处理**：
- Discussion on RQ 子节用 `\subsection{Discussion on the research questions}`
- 内部按 RQ 用 `\subsubsection{}` 切分（如 `\subsubsection{RQ1: ...}`）
- Theoretical implications: `\subsection{Theoretical implications}`
- Practical implications: `\subsection{Practical implications}`

### 4.3 bib 同步

写入 tex 后，立即同步 bib：

1. 用正则提取本次写入的所有 `\citep{...}` / `\citet{...}` 中的 citation keys → 去重
2. 检查每个 key 是否已在项目 `{BIB_PATH}` 中
3. 不在的 → 从 `structure/2_literature/citation_pool/master.bib` 中提取对应条目，追加到项目 bib 末尾
4. master.bib 中也找不到 → 标记 ⚠️（用户可能手动添加 / 或是 (ref) 占位待补）

显示同步结果：
```
📚 bib 同步: 共 {N} 个 keys，新增 {M} 条到项目 bib
[如有] ⚠️ 找不到的 keys（master.bib 也无）: {list}
```

---

## 步骤 5：完成提示

```
✅ /narrative section={SECTION_TYPE} 完成

📊 写入摘要:
- {section title}: {N} 词
- 子节数: {M}
- 总引用: {citep} \citep + {citet} \citet
- bib 新增: {K} 条
[discussion 特有]:
- 文献回扣率: {K}/{L} = {%}
- Results 发现锚点: {P} 处

💡 后续:
- 你可以在 manuscript.tex 中亲自再改一轮（最后一轮人工把关）
- 改完后可调用 /polish 做段落级语言润色
- 全部三节叙述型完成后 → /finalize 收尾
```

---

## 共享约束（所有 section 通用）

### 引用规则

- **引用形式标记 `[citep]/[citet]/[—]`**：内部生成时用于标识，最终 tex 输出时**只保留 `\citep{}` / `\citet{}`**（标记不出现在 tex 中）
- **每个引用必须 bib 验证**：unverified 的 key 不允许进入最终 tex
- **优先复用 LR 已用文献**（discussion 必须，intro/litrev 视情况）
- **Hedge 措辞规范**：避免绝对性声明，全 section 适用

### 用户交互节奏

- **逐子节确认**（不批量）：每个子节生成后立即让用户 review，避免"全部生成完才发现方向错"
- **句子级 review**：用户可以指定"第 N 句改成..."而不需要整段重写
- **循环至满意**：每个交互节点都允许多轮修改，不限次数

### 失败模式

- **空 section 检测**：步骤 0.4 自动建空 `\section{}` 骨架
- **Citation key 缺失**：bib + master.bib 都找不到 → 标记 (ref) 占位 + 警告，不阻塞
- **Discussion 前置依赖不满足**（Methodology/Results 空 / Introduction 无 RQ）：步骤 3.1 BLOCK

### 与 /polish 的接力

`/narrative` 完成后，`manuscript.tex` 已是可读英文。如需进一步语言打磨：
```
/polish section={section title}
```
`/polish` 走 strict-reviewer + language-polisher pipeline，与 `/narrative` 完全解耦。

---

## 设计原则备忘

1. **Introduction/LR 保留 blueprint md**——先锁定逻辑合约再写 tex；Discussion 不强制中间 md
2. **不走"中文要点 → 翻译"**——直接英文段落生成，避免双重损耗
3. **句子级 review 是最后人工把关**——skill 不追求"一键完美"，目标是把人工修改成本降到最低
4. **Discussion 内核统一**（不让用户选机制风格）——三篇 benchmark 论文的写法本质相同：深度思考 + 结合文献深入讨论
5. **T/P implications 自动推荐粒度**——基于期刊+results+LR 学科自动推断，不让用户做选择题
6. **字数 / 引用密度硬约束**——写入 prompt 强制遵守，不允许 LLM 自由发挥
