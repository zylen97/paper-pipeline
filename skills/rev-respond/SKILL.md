---
description: "交互式逐条审稿回复闭环（策略对齐 → 内容起草 → 语言润色 → 执行），每步用户确认后推进"
---

# Rev-Respond — 交互式逐条审稿回复

对单条审稿意见执行完整的交互式闭环：策略对齐 → 内容起草 → 语言润色 → 执行。每一步都需要用户确认后才推进到下一步。

**核心原则**：AI 只提方案，用户拍板。确认前不写文件、不改稿件、不填回复。

**回退原则**：任何轮次中，如果用户的反馈表明需要调整前序轮次的决策，流程可以回退。回退时，从目标轮次重新开始，后续轮次全部重走。具体回退触发条件在各轮次的用户交互环节中定义。

## 输入说明

`$ARGUMENTS` 格式：
- Comment 编号：`R1-1` / `R1-m2` / `R2-3` 等
- 可选附加指令用 `|` 分隔：`R2-3 | 重点说明 fsQCA 校准问题`
- 空参数 → 停止，提示用户指定 Comment 编号

编号映射到 response-letter.tex：
- `R1-1` → `Comment \#1-1`
- `R1-m1` → `Comment \#1-m1`
- `R2-3` → `Comment \#2-3`

---

## Step 0: 上下文加载

### 0a. 解析输入

从 `$ARGUMENTS` 中提取：
- Comment ID（如 `R2-3`）
- 可选用户附加指令（`|` 后的内容）

验证格式：`R` + 数字 + `-` + 数字或 `m`+数字。无效 → 停止，提示正确格式。

### 0b. 前置环境检查 + 轮次检测

从 CLAUDE.md 的 `## 项目阶段` 字段提取当前轮次 `{ROUND}`（如 `revision-R2` → `ROUND=2`）。当前轮次的工作目录为 `revision-R{ROUND}/`。

检查 `/rev-init` 是否已执行：
- 确认 `revision-R{ROUND}/comment-letter-clean.md` 存在
- 确认 `revision-R{ROUND}/revision-guide.md` 存在
- 确认 `response-letter.tex` 存在

任一文件缺失 → **停止**，提示用户："请先运行 `/rev-init` 初始化修改工作流。"

### 0c. 读取项目上下文

依次读取以下文件：
1. `revision-R{ROUND}/comment-letter-clean.md` → 定位该 Comment 的完整评论文本
2. `revision-R{ROUND}/revision-guide.md` → 找到所属 Cluster、核心问题、修改计划、锚点信息
3. `manuscript.tex` → 全文（重点关注与该 Comment 相关的 section）
4. 项目 `.bib` 文件 → 可用引用（从 CLAUDE.md 或 `manuscript.tex` 的 `\bibliography{}` 确认文件名）
5. `response-letter.tex` → 定位该 Comment 的填写位置，同时检查哪些 Comment 的 `[TO BE FILLED]` 已被替换（= 已完成）
6. 如 `supplemental-materials.tex` 存在 → 读取（该 Comment 可能涉及补充材料修改）

### 0d. 检查同 Cluster 上下文

扫描 `revision-R{ROUND}/drafts/` 目录：
- 查找同 Cluster 的 `Proposal_*.md` 和 `Comment_*.md`
- 如有 → 读取已确认的策略和回复，保持一致性
- 判断交叉引用类型：
  - **同审稿人**（如 R1-4 和 R1-1 同属 C1）→ 回复中可直接引用（"As discussed in our response to Comment #1-1 above..."）
  - **跨审稿人**（如 R2-1 和 R1-1 同属 C1）→ **必须自含式回复**，不可引用其他 Reviewer 的 Comment

### 0e. 防护检查

- `revision-R{ROUND}/drafts/Proposal_{Comment_ID}.md` 或 `Comment_{Comment_ID}.md` 已存在 → AskUserQuestion："该 Comment 已有草稿文件：**1** = 覆盖重做 / **2** = 跳过"
- `response-letter.tex` 中该 Comment 的 `\response{[TO BE FILLED]}` 已被替换（即已有实质回复内容）→ 警告用户，AskUserQuestion："该 Comment 已有回复内容：**1** = 覆盖重做 / **2** = 跳过"
- 该 Cluster 依赖的其他 Cluster 尚未完成（检查方法：revision-guide.md 中依赖 Cluster 的 Comments 在 response-letter.tex 中仍有 `[TO BE FILLED]`）→ 警告（非阻断）："⚠️ C2 依赖 C1，但 C1 尚未完成。建议先处理 C1。"

---

## Round 1: 策略对齐

### 1a. 生成策略提案

在对话中展示策略提案（**不写文件**）：

```
## 策略提案 — {Comment ID}

### 审稿人原文
> [从 comment-letter-clean.md 摘录该 Comment 的完整原文]

### 审稿人的真正关切
[1-2 句话提炼审稿人本质上在问什么——不是转述原话，而是分析后的核心]

### 所属 Cluster
C{N}: {名称} | 角色: {Anchor/Satellite} | 同 Cluster 已确认: {列出或"无"}

### 修改方向
- [要点 1: 改什么、在哪里]
- [要点 2: 补什么]
- [要点 3: 回复怎么论证]

### 影响位置
- manuscript.tex: {Section Name}, Lines {XXX--YYY}
- supplemental-materials.tex: {如涉及}

### 风险/权衡
- [风险 1: 如 "新增定义可能与 Eq.(3) 冲突"]
- [风险 2: 如 "审稿人可能期望超出我们数据支撑的内容"]

### 回复策略
- 论证路径: [怎么构建论证——用什么逻辑、从哪个角度]
- 文献支撑: [具体可引用的文献]
- 与同 Cluster 关系: [需要与哪些已确认策略协调/完全独立]
```

### 1b. 用户交互

AskUserQuestion：

```
以上是 {Comment ID} 的策略提案。请审阅：
- 方向是否正确？
- 有无遗漏的关键点？
- 对风险的判断是否合理？
- 有无要补充的信息/约束？

**1** = 确认策略，或直接输入调整意见。
```

用户输入调整意见 → 根据反馈修改策略，重新展示 → 再次 AskUserQuestion。**迭代直到用户输入 1**。

### 1c. 保存确认的策略

写入 `revision-R{ROUND}/drafts/Proposal_{Comment_ID}.md`：

```markdown
# 策略提案 — {Comment ID}

> **审稿人**: Reviewer #{X}
> **所属集群**: C{N} — {Cluster 名称}
> **角色**: {Anchor/Satellite}
> **确认日期**: {当前日期}

## 审稿人原文
> {从 comment-letter-clean.md 摘录的完整原文}

## 审稿人的真正关切
{确认的内容}

## 修改方向
{确认的内容}

## 影响位置
{确认的内容}

## 回复策略
{确认的内容}

## 用户附加指令
{用户在讨论中提出的额外要求，如有}
```

---

## Round 2: 内容起草

### 2a. 生成两部分内容

基于确认的策略，生成：

#### Part A — Response Letter 文本（LaTeX）

完整的回复文本，可直接粘贴到 `response-letter.tex`：

```latex
\responseheader

\response{[感谢/认同 — 1-2句，措辞独特]}

\response{First, [第一方面回应]. [展开 2-3 句].}

\manuscriptquote{[修改后的稿件文本] \lineref{Lines XXX--YYY}}

\response{Second, [第二方面回应]. [展开].}

\manuscriptquote{[修改后的稿件文本] \lineref{Lines XXX--YYY}}

\response{[总结句]}
```

**格式规则**（铁律）：
- `\response{}`、`\manuscriptquote{}`、`\lineref{}` **不可嵌套**
- `\response{}` 在 `\manuscriptquote{}` 之前关闭，之后重新打开
- `\response{}` **内部不能有空行**（会导致 `\par` 错误）
- `\lineref{}` 放在 `\manuscriptquote{}` 的**内容末尾**
- `\lineref{}` **一律写 `\lineref{Lines [TBD]}`**，不在逐条处理时填真实行号。原因：`\lineref{}` 中的行号 = 编译后 PDF 的 running line numbers（由模板 cls 自动生成），不是 .tex 源文件行号；且每次改稿后行号会漂移。所有 Comment 完成后在 Round 4e 批量回填
- Section 引用格式：`the ``Introduction'' section`（section 名称加引号，小写 section）

**引用格式**（response-letter.tex 不使用 natbib）：
- `(Author et al., Year)` 替代 `\citep{}`
- `Author et al. (Year)` 替代 `\citet{}`
- 两位作者写全：`(Smith and Jones, 2023)`
- 三位及以上用 et al.：`(Wang et al., 2024)`
- 从项目 `.bib` 文件查找实际作者和年份

**感谢措辞**（每条 Comment 不同）：
- "We thank the reviewer for this comment on [具体话题]."
- "We appreciate the reviewer's attention to [具体方面]."
- "This is a constructive observation. We address it as follows."
- "The reviewer raises a valid concern about [具体问题]."
- "Thank you for the careful examination of [具体方面]."
- 检查 `revision-R{ROUND}/drafts/` 中已有回复，确保不重复

**跨审稿人引用规则**：
- **同审稿人内**：可直接引用，如 "As discussed in our response to Comment #1-1 above, ..."
- **跨审稿人**：**禁止**。必须自含式回复。可用软性措辞："This concern was also noted by other reviewers, and we have addressed it in the revised manuscript." 但实质内容不能依赖此句。

**论证要求**：
- 使用 First/Second/Third 结构
- 不要只说"我们改了"，要说明**为什么这样改**和**如何解决审稿人的问题**
- 引用具体文献支持论证
- 对方法论/假设类问题，从学科理论基础和文献先例两个角度论证
- 审稿人建议无法完全采纳 → 礼貌但坚定解释原因 + 提出替代改进

#### Part B — 稿件修改方案

逐条列出具体修改（pen-polish 风格）：

```
### 修改 1: [简述]
**文件**: manuscript.tex
**位置**: {Section Name}, Lines {XXX--YYY}
**类型**: Rewrite / Insert / Delete

**当前文本**:
> [从 manuscript.tex 精确摘录的当前文本]

**修改为**:
> [提议的新文本]

**理由**: [为什么这样改]

### 修改 2: [简述]
**文件**: supplemental-materials.tex（如涉及）
**位置**: ...
...
```

修改文本同样遵循科技写作纪律。方法描述中的被动语态（如 "samples were collected"）属学科惯例，可保留。

如不需要修改原稿（纯解释类回复），明确声明："本条意见无需修改原稿。"

**生成完成后，执行质量自检（见文末 4 项清单），仅在发现问题时修正后再展示给用户。**

### 2b. 用户交互

展示 Part A 和 Part B 给用户。

AskUserQuestion：

```
以上是 {Comment ID} 的完整草稿。请审阅：

【回复信文本】措辞、论证逻辑、承诺程度
【修改方案】范围、具体措辞

**1** = 确认，或直接输入修改意见。
```

用户输入修改意见 → 根据调整性质分两种处理：

**内容调整**（修改措辞、调整论证、增删修改条目）：
主 Agent 按用户意见修改 Part A 和/或 Part B，重新展示，再次 AskUserQuestion。

**策略回退**（发现论证方向根本性错误、需要重新定义修改范围或回复策略）：
**回退到 Round 1**。重新对齐策略（1a），用户确认后（1b），再重新进入 Round 2 起草内容。已保存的 `Proposal_{Comment_ID}.md` 将被新版本覆盖。

**判断标准**：如果用户的反馈涉及"换个角度回复""这个方向不对""策略要改"等，属于策略回退；其余属于内容调整。如不确定，AskUserQuestion 确认。

**迭代直到用户输入 1**。

### 2c. 保存确认的草稿

写入 `revision-R{ROUND}/drafts/Comment_{Comment_ID}.md`：

```markdown
# Comment {Comment_ID} 回复

> **审稿人**: Reviewer #{X}
> **意见编号**: {Comment ID} — {简短标题}
> **所属集群**: C{N} — {Cluster 名称}
> **角色**: {Anchor/Satellite}
> **确认日期**: {当前日期}

---

## 审稿人原文
> {从 comment-letter-clean.md 摘录的完整原文}

---

## Part 1: 策略（来自 Proposal）

{从 Proposal 文件复制确认的策略}

---

## Part 2: 回复正文 (LaTeX)

以下文本可直接粘贴到 `response-letter.tex`。

```latex
{确认的 LaTeX 回复文本}
```

---

## Part 3: 原稿修改

{确认的修改方案，或 "本条意见无需修改原稿。"}

---

## 交叉引用

- **同审稿人相关意见**: {可直接引用的 Comment}
- **跨审稿人相关意见**: {必须自含式的 Comment}
```

---

## Round 3: 语言润色

### 3a. 准备润色文本

从 Round 2 确认的内容中提取所有英文文本：
- **Part A**: Response Letter 回复正文（`\response{}` 内的英文文本）
- **Part B**: 稿件修改方案中"修改为"部分的英文文本

将两部分合并为一个润色请求，保留 LaTeX 命令结构（`\response{}`、`\manuscriptquote{}`、`\lineref{}` 等不动，只润色其中的英文内容）。

### 3b. 调用 language-polisher agent

使用 Agent 工具调用 language-polisher（Mode B — Ad-hoc）：

```
Agent(
  subagent_type: "language-polisher",
  prompt: "Mode B (Ad-hoc). Polish the following academic English text.
           This is a response letter and manuscript revision for
           {期刊名，从 revision-guide.md Section 1 或 CLAUDE.md 读取}.
           Preserve all LaTeX commands exactly as-is.

           IMPORTANT: Text inside \manuscriptquote{} in Part A is a direct
           quotation from the revised manuscript. It MUST remain identical
           to the corresponding revised text in Part B. If you polish a
           sentence in Part B, apply the exact same change inside the
           matching \manuscriptquote{} in Part A.

           --- Part A: Response Letter ---
           {Part A 文本}

           --- Part B: Manuscript Revisions ---
           {Part B 修改文本}"
)
```

### 3c. 展示润色结果

将 language-polisher 返回的内容展示给用户：
- 润色后的 Part A（完整 LaTeX 回复文本）
- 润色后的 Part B（修改方案中的新文本）
- Change Summary（language-polisher 自动生成：总改动数、分类统计、Chinglish 修复表、Top 3 改动）

AskUserQuestion：

```
以上是 language-polisher 润色后的版本。请审阅：

【Part A 回复信】语言是否自然流畅？
【Part B 稿件修改】润色是否改变了原意？

**1** = 确认，或直接输入调整内容。
```

用户输入调整内容 → 根据调整幅度分三种处理：

**场景 A — 语言微调**（换个词、删一句、调语序）：
主 Agent 直接修改对应文本，不重新调用 polisher。修改后重新展示，再次 AskUserQuestion。

**场景 B — 局部重写**（加了新句子、重写了一段、补充了新论点）：
主 Agent 先按用户意见修改文本，然后**仅将改动部分**重新丢给 language-polisher agent 润色。将润色结果整合回完整文本后重新展示，再次 AskUserQuestion。

**场景 C — 方向推翻**（论证方向错误、内容策略需要调整、需要重新组织整体结构）：
**回退到 Round 2**。重新起草内容（2a），用户确认后（2b），再重新进入 Round 3 走完整润色流程。如果方向性调整涉及策略层面的改变，进一步回退到 Round 1 重新对齐策略。

**判断标准**：由主 Agent 根据用户反馈的性质判断属于哪种场景。如不确定，AskUserQuestion 确认："您的调整是语言层面的修改，还是内容方向需要调整？"

**迭代直到用户输入 1**。

### 3d. 更新草稿文件

用润色后的最终版本覆盖 `revision-R{ROUND}/drafts/Comment_{Comment_ID}.md` 中的 Part 2（回复正文）和 Part 3（原稿修改）。

---

## Round 4: 执行

### 4a. 应用稿件修改

从 `revision-R{ROUND}/drafts/Comment_{Comment_ID}.md`（Round 3 润色后的最终版本）读取 Part 3 原稿修改，使用 Edit 工具逐条应用（manuscript.tex 和/或 supplemental-materials.tex）。

**铁律**：仅改确认内容，不做额外修改。

### 4b. 填写回复信

从 `revision-R{ROUND}/drafts/Comment_{Comment_ID}.md`（Round 3 润色后的最终版本）读取 Part 2 回复正文，在 `response-letter.tex` 中定位该 Comment 的 `\response{[TO BE FILLED]}`，替换为润色后的回复文本。

如果该 Comment 的 `\response{[TO BE FILLED]}` 找不到（可能已被提前填写），告知用户并跳过。

### 4c. 编译验证

编译由 PostToolUse hook 自动触发（`/rev-init` Step 2 配置）：
- Edit/Write `.tex` 文件后自动编译
- 修改 `manuscript.tex` 时额外生成 track changes PDF

**主 Agent 无需手动执行编译命令。** 如果 hook 报告编译失败，告知用户错误信息，不自动修复。

### 4d. Commit 决策

AskUserQuestion：

```
{Comment ID} 已完成：
  ✅ manuscript.tex 已修改（{N} 处）
  ✅ response-letter.tex 已填写
  ✅ 编译 {通过/失败}

是否提交 Git commit？
  **1** = 提交
  **2** = 暂不提交
```

如用户输入 1：
```bash
git add manuscript.tex response-letter.tex \
       revision-R{ROUND}/drafts/
# 仅在修改了补充材料时才 add
git add supplemental-materials.tex 2>/dev/null || true
git commit -m "C{N} {Comment_ID}: {brief description}"
```

### 4e. 修改追踪报告（全部完成时触发）

扫描 `response-letter.tex` 中所有 `\response{[TO BE FILLED]}` 的数量：

- **仍有 `[TO BE FILLED]`** → 跳过此步骤，直接进入 4f 下一步提示
- **全部填完（0 个 `[TO BE FILLED]`）** → 自动生成修改追踪报告

**报告生成**：

1. **确认 baseline 文件**：读取 `.revision-baseline` 获取基准文件名（如 `manuscript-R0.tex`）；不存在则 fallback 到 `manuscript-original.tex`（遗留格式）
   - 均不存在 → 警告并跳过

2. **逐 section 差异对比**：对比基准文件和当前 `manuscript.tex`
   - 提取每个 `\section{}` 的内容，逐 section diff
   - 统计：新增字数、删除字数、净变化

3. **生成修改摘要**（写入 `revision-R{ROUND}/revision_summary.md`）：

```markdown
# Revision Summary

> Generated: {date}
> Baseline: {BASELINE}（从 .revision-baseline 读取）
> Current: manuscript.tex

## Overview

| 指标 | 数值 |
|------|------|
| 总 Comment 数 | {N} |
| 已回复 | {N} |
| 涉及稿件修改的 Comment | {M} |
| 纯解释（无修改） | {N-M} |

## Changes by Section

| Section | 新增 | 删除 | 净变化 | 涉及 Comment |
|---------|------|------|--------|-------------|
| Introduction | +{n} | -{n} | {±n} | R1-2, R2-1 |
| Literature Review | +{n} | -{n} | {±n} | R1-3 |
| ... | ... | ... | ... | ... |

## Comment → Modification Mapping

| Comment | 修改位置 | 修改类型 | 简述 |
|---------|---------|---------|------|
| R1-1 | Section 3, L120-135 | Rewrite | {从 Comment 草稿提取} |
| R1-2 | Section 1, L45-50 | Insert | {从 Comment 草稿提取} |
| R2-3 | — | 无修改 | 纯解释 |
| ... | ... | ... | ... |
```

4. **批量回填 `\lineref{}` 行号**：
   - 编译 `manuscript.tex` 生成最终 PDF
   - 打开 PDF，逐条定位每个 `\manuscriptquote{}` 对应段落的 PDF running line numbers
   - 在 `response-letter.tex` 中将所有 `\lineref{Lines [TBD]}` 替换为真实 PDF 行号
   - 同步更新 `revision-R{ROUND}/drafts/Comment_*.md` 中的 `[TBD]`
   - 重新编译 `response-letter.tex` 确认无误

5. **展示报告** 给用户，提示：
```
所有审稿意见已回复完毕！修改摘要已保存至 revision-R{ROUND}/revision_summary.md

下一步：
- 检查 response-letter.pdf 和 manuscript.pdf
- 运行 /pre-submit 做投稿前终检
- 确认后重新提交
```

### 4f. 下一步提示（仍有未完成 Comment 时）

展示：
- 当前 Cluster 剩余情况（从 revision-guide.md 获取 Cluster 成员列表，grep response-letter.tex 中对应 Comment 的 `[TO BE FILLED]` 计数）
- 推荐下一条 Comment（Cluster 内：锚点优先；Cluster 间：按 revision-guide.md 执行顺序）
- 依赖警告（如有）

---

## 科技写作纪律（指导 Round 2 起草）

> **定位**：此纪律指导 Round 2 内容起草的语言质量基线。Round 3 的 language-polisher agent 提供最终语言润色（Chinglish 消除、搭配校正、句式优化等）。起草阶段语言质量越高，润色阶段改动越小、风险越低。

**每一句**回复和修改文本必须通过以下检查：

| # | 规则 | 要求 | ❌ → ✅ |
|---|------|------|---------|
| 1 | 简单主动句式 | 一句一意，主语做动作 | "X was revised" → "We revised X" |
| 2 | 逻辑清晰 | First/Second/Third | "Moreover,...Furthermore,..." → "First,...Second,..." |
| 3 | 短句 | 目标 15-20 词，上限 25 | 长句 → 拆分 |
| 4 | 克制修饰 | 删除不传递信息的副词/形容词 | "significantly improved" → "improved" |
| 5 | 中式英语防治 | 检查动宾搭配 | "improve the level" → enhance |
| 6 | 压缩冗余 | 名词化→动词，删空洞修饰 | "carry out an investigation" → investigate |
| 7 | 破折号纪律 | em dash 每页≤2 | `---such as A, B---` → `, such as A and B,` |

> 感谢语句允许一个描述性形容词（如 "constructive feedback"），正文严格执行。

---

## 质量自检（4 项）

> **执行时机**：Round 2 内容起草完成后、展示给用户之前。AI 内部自检，仅在发现问题时报告给用户。

1. **Part A ↔ Part B 一致性**：`\manuscriptquote{}` 中引用的文本必须与 Part B 的实际修改文本完全一致
2. **跨审稿人自含性**：不同 Reviewer 的回复不可引用对方的 Comment 编号，必须自含式
3. **同 Cluster 一致性**：与同 Cluster 已确认的回复在立场和措辞上保持一致
4. **LaTeX 格式正确**：`\response{}`、`\manuscriptquote{}`、`\lineref{}` 不嵌套；`\response{}` 内无空行
