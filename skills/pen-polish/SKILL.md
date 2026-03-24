---
description: "交互式打磨已有论文段落（Pipeline：journal-scout → strict-reviewer → 用户确认 → 主agent直接修改 → language-polisher）"
---

# Polish Workflow — 交互式打磨已有文本

调用 agent 对已有文本进行质量提升。与 Draft 不同，Polish 保持原文逻辑结构，不从零撰写。

**核心特征**：
- **不拆分 subsection**：无论输入包含多少 `\subsection`，都作为一个整体交给 reviewer
- **交互式审稿**：reviewer 给出编号意见 → **用户逐条确认** → 主 agent 生成修改方案并执行用户确认的意见
- **Citation 保护**：不得增删改任何 citation key 和引用形式

**输入** `$ARGUMENTS`：用户选中的已有文本（LaTeX），可选 `section=XXX`。空或 < 50 字符 → 停止提示用户选中文本。

## 步骤 0：前置准备

### 0.1 解析 `$ARGUMENTS`

- 提取主体内容和 `section` 参数
- 空或 < 50 字符 → 停止，提示用户选中文本

### 0.2 获取项目文件路径

- 从 CLAUDE.md 获取主文件和 bib 文件路径
- Fallback：Glob("*.tex") 查找含 `\documentclass` 的文件（排除 supplementary/appendix/*.cls）
- 读取主文件了解论文结构

### 0.3 构建 Section Tree（Python 脚本）

**由 Python 脚本自动完成**：

```bash
python3 ~/.claude/skills/shared/tex_section.py section-tree --tex {主文件路径}
```

输出 `_section_tree.json`。VERIFY 必须为 PASS。

### 0.4 定位 Section（Python 脚本 + 主 Agent）

从输入文本中提取 section 命令，或使用 `section=XXX` 参数：

```bash
python3 ~/.claude/skills/shared/tex_section.py match-section \
  --tree _section_tree.json --query "{section标题}"
```

从 `_section_match.json` 读取匹配结果。记录 `{SECTION_TITLE}` 和位置信息。**不拆分**——整体处理。

### 0.5 字数基准

- 原文字数 → `{ORIGINAL_WORD_COUNT}`
- 目标字数 = 原文字数 ± 10%

### 0.6 创建工作目录 + 保存原文

**`normalize(title)`**：空格→下划线，Capitalized_Words 风格，> 40 字符在最后完整单词边界截断。

创建 `{WORK_DIR}`，保存原始文本 → `{WORK_DIR}/01_original_text.md`

## 步骤 1：生成 Writing Brief

1. **复用检查**：读取 `drafts/writing_brief.md`，检查时间戳（> 24h→重新生成）和字数变化（> 20%→重新生成）。两项通过→复用
2. **如需生成**：Web 搜索期刊 Guide for Authors → 调用 journal-scout → 保存到 `drafts/writing_brief.md`
3. **展示**：期刊名称、期刊画像摘要

## 步骤 2：第1轮审稿

### 2.1 strict-reviewer 审稿

调用 strict-reviewer（`subagent_type: "strict-reviewer"`），prompt 要素：

```
Read `drafts/writing_brief.md` for journal conventions and style guidance. Pay special attention to the Journal Profile section for the journal's aesthetic preferences.

Read `structure/0_global/idea.md` for the research context (Gap/RQ/contributions).

## Section: {SECTION_TITLE}
## Position in paper: {一句话位置描述，如 "Literature review, between Introduction and Methodology"}
## Mode: Polish — give numbered improvement suggestions only

## Text to Review
Read `{WORK_DIR}/01_original_text.md`

## Review Instructions
- Output a NUMBERED list of specific, actionable improvement suggestions
- Each suggestion must reference the specific paragraph it applies to
- Focus on:
  - **Language**: clarity, sentence structure, academic tone, word choice precision
  - **Logic coherence**: paragraph-to-paragraph transitions, argument progression, no logical jumps between claims, no missing intermediate steps in reasoning chains
  - **Cross-subsection coherence**: whether subsections connect naturally, whether the overall narrative has a clear arc from beginning to end
  - **Domain grounding**: arguments grounded in the specific industry context, not generic theory that could apply to any field
- Do NOT suggest adding, removing, or changing any citations
- Do NOT give an overall verdict (accept/reject/revise) — just list concrete suggestions
- Word count reference: {ORIGINAL_WORD_COUNT} (target ± 10%)

## Output Format
1. [Para X] {issue description} → Suggestion: {specific fix}
2. [Para X] {issue description} → Suggestion: {specific fix}
...
```

保存审稿意见 → `{WORK_DIR}/02_review_r1.md`

### 2.2 用户确认

将审稿意见展示给用户，AskUserQuestion：

```
📋 第1轮审稿意见（共 N 条）：

1. [Para X] {issue} → {suggestion}
2. [Para X] {issue} → {suggestion}
...

请选择要执行的意见：
- 接受：输入编号（如 "1,3,5" 或 "all"）
- 拒绝：输入 "reject 2,4"
- 修改某条：输入 "3: 改为..."
```

用户确认后，生成确认清单。保存 → `{WORK_DIR}/02_confirmed_r1.md`

### 2.3 生成具体修改方案

基于用户确认的意见和偏好，主 agent 生成**具体修改方案**——逐条列出"把哪句话改成什么"：

```
📝 修改方案（共 M 条）：

1. [对应意见#1]
   原文: "originated from descriptive social network analysis"
   改为: "has its roots in descriptive social network analysis, which..."

2. [对应意见#3]
   原文: "Despite these advances, a gap remains between the two streams"
   改为: "Despite these advances, a gap remains between project-level SAOM studies and industry-level cross-sectional analyses"

...
```

AskUserQuestion：确认修改方案，或调整某条的具体措辞。

### 2.4 执行修改

用户确认方案后，主 agent 直接使用 Edit 工具逐条执行修改（不调用 sci-writer agent）。修改时严格遵守：
- **只改方案中列出的内容**，不做额外改动
- **不动任何 citation key 和引用形式**
- 保留所有数据、数字和事实性表述

保存修改版 → `{WORK_DIR}/03_revision_r1.md`

## 步骤 3：第2轮审稿（可选）

### 3.1 询问用户

AskUserQuestion：
```
第1轮修改完成。是否进行第2轮审稿？
(1) 进行第2轮
(2) 跳过，直接进入语言润色
```

用户选 (2) → 直接进入步骤 4。

### 3.2 第2轮审稿-确认-修改

如果用户选 (1)：

**3.2a strict-reviewer 审稿**：同步骤 2.1 逻辑，待审文本改为 `{WORK_DIR}/03_revision_r1.md`，标注"第2轮"。保存 → `{WORK_DIR}/04_review_r2.md`

**3.2b 用户确认**：同步骤 2.2。保存 → `{WORK_DIR}/04_confirmed_r2.md`

**3.2c 生成修改方案 + 用户确认**：同步骤 2.3，基于用户确认的第2轮意见生成具体修改方案，用户确认后执行。

**3.2d 执行修改**：同步骤 2.4，主 agent 直接修改 `03_revision_r1.md` 的内容。保存 → `{WORK_DIR}/05_revision_r2.md`

## 步骤 4：language-polisher 最终润色

调用 language-polisher（`subagent_type: "language-polisher"`），prompt 要素：

```
Read `drafts/writing_brief.md` for journal conventions and style guidance. Refer to the Journal Profile section for the journal's tone and style preferences.

## Section: {SECTION_TITLE}
## Mode: Language polish (final step after review cycles)

## Text to Polish
Read `{WORK_DIR}/{最新版本}`
（如果跑了第2轮 → 05_revision_r2.md；否则 → 03_revision_r1.md）

## Instructions
- Improve grammar, coherence, sentence flow, and naturalness
- Preserve all academic content, arguments, and structure
- Do NOT restructure paragraphs or change argument order

## Citation Protection (CRITICAL)
- Do NOT add, remove, or change any citation key in \citet{} or \citep{} commands
- Do NOT change citation form (\citet → \citep or vice versa)
- Preserve all `(ref)` markers and existing citations exactly as they are

## Constraints
- Word target: {ORIGINAL_WORD_COUNT} ± 10%
- Do NOT use \textbf{}
- Record all changes in a Change Summary at the end

## Output
1. Complete polished LaTeX content in a ```latex``` code block
2. Change Summary: list of language improvements made
3. Actual word count
```

保存润色版 → `{WORK_DIR}/06_polished.md`

## 步骤 5：生成输出文件

### 文件 1：`{WORK_DIR}/final.md`

从 `06_polished.md` 提取 ` ```latex``` ` code block，包裹为：

```markdown
# {Section Title} — Polished Version

> Ready to copy · Replaces original text in manuscript.tex

```latex
{LaTeX content}
```

**Target location**: manuscript.tex, {section position}
**Word count**: {original} → {final}
**Review rounds**: {1 或 2}
```

### 文件 2：`_latest_final.md`（便捷入口）

`drafts/{SECTION_NAME}_latest_final.md`，复制 `final.md` 内容，已存在则覆盖。

## 步骤 6：完成提示

显示：
- ✅ 完成状态
- 📂 工作目录路径 / 便捷入口路径
- 字数变化：{original} → {final}
- 审稿轮数：{1 或 2}
- Checkpoint 文件清单
- 💡 提醒手动替换 manuscript.tex 中的对应文本
- 💡 所有章节 polish 完成后，运行 `/finalize` 完成 Conclusion → Abstract → Cover Letter
