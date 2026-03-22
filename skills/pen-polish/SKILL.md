---
description: "交互式打磨已有论文段落（Pipeline：journal-scout → strict-reviewer → 用户确认 → sci-writer → language-polisher）"
---

# Polish Workflow — 交互式打磨已有文本

调用 agent 对已有文本进行质量提升。与 Draft 不同，Polish 保持原文逻辑结构，不从零撰写。

**核心特征**：
- **不拆分 subsection**：无论输入包含多少 `\subsection`，都作为一个整体交给 reviewer
- **交互式审稿**：reviewer 给出编号意见 → **用户逐条确认** → sci-writer 只执行用户确认的意见
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

### 0.3 构建 Section Tree `{SECTION_TREE}`

- 正则 `\\(section|subsection|subsubsection)\{([^}]+)\}` 提取所有 section 命令（忽略 `*` 变体）
- 记录级别、标题、行号，构建父子关系树

### 0.4 Section 检测

扫描输入文本中的 section 命令，在 `{SECTION_TREE}` 中定位：

- **无 section 命令**：用户指定 `section=XXX` 则使用，否则与 `{SECTION_TREE}` 对比推断或询问
- **有 section 命令**：提取最高级别 section 标题，在 `{SECTION_TREE}` 中查找（先精确后模糊），确定 `{ANCESTOR_PATH}`

**不拆分**：无论输入包含多少 `\subsection`，都作为一个整体处理。记录 `{SECTION_TITLE}` 和 `{ANCESTOR_PATH}`。

### 0.5 字数基准

- 原文字数 → `{ORIGINAL_WORD_COUNT}`
- 目标字数 = 原文字数 ± 10%

### 0.6 创建工作目录

**`normalize(title)`**：空格→下划线，Capitalized_Words 风格，> 40 字符在最后完整单词边界截断。

`{WORK_DIR}` = `drafts/{HIERARCHY_PREFIX}/{SECTION_NAME}_{序号:03d}/`（HIERARCHY_PREFIX = 祖先标题 normalize 后 "/" 连接，顶级为空）

## 步骤 1：生成 Writing Brief

1. **复用检查**：读取 `drafts/writing_brief.md`，检查 `## Metadata` 中的 `Generated` 时间戳（> 24h→重新生成）和 `Manuscript word count`（变化 > 20%→重新生成）。两项通过→复用
2. **Web 搜索**（主 agent 执行）：从 `\journal{}` 提取期刊名，依次尝试 `mcp__web-search-prime__webSearchPrime`→`mcp__MiniMax__web_search`→"Knowledge base only"
3. **调用 journal-scout**（`subagent_type: "journal-scout"`）：prompt 含 manuscript 分析 + web 搜索结果
4. **保存**：提取 `---BEGIN/END WRITING BRIEF---` 之间内容→`drafts/writing_brief.md`
5. **展示**：期刊名称、研究情境、期刊画像摘要

## 步骤 2：提取要点

从已有文本提取要点。关注**现有文本的逻辑骨架**和**不可变更的事实性内容**，防止多轮修改中破坏逻辑或篡改数据。

**提取内容**：
- 核心论点（每段主要观点）
- 论证链条（前提→推理→结论）
- 硬性事实与数据细节（样本、时间、数据库、方法、阈值等，绝不可修改/省略/近似化）
- 已有引用（原样保留，记录每个 `\citet{}` 和 `\citep{}` 的位置和 key）

**格式**：编号列表，每个锚点标明所在段落和逻辑角色。如：`[Para 1] Core argument: ... | Logical role: ...`

**输出**：
1. 对话中显示
2. 保存要点 → `{WORK_DIR}/00_key_points.md`
3. 保存原始文本 → `{WORK_DIR}/01_original_text.md`

生成 Structural Context：

```
### Structural Context
- Paper structure position: {完整路径}
- Parent section: {parent title 或 "Top level (no parent)"}
- Sibling sections: {同级列表}
- Preceding/Following section: {前/后同级或 "None"}
- Role in paper: {基于位置推断的角色}
```

## 步骤 3：第1轮审稿

### 3.1 strict-reviewer 审稿

调用 strict-reviewer（`subagent_type: "strict-reviewer"`），prompt 要素：

```
Read `drafts/writing_brief.md` for journal conventions and style guidance. Pay special attention to the **Journal Profile** section for the journal's aesthetic preferences, methodology expectations, and research topic hotspots.

## Section: {SECTION_TITLE}
## Mode: Polish (refine existing text, preserve logic)
## Round: 1

## Structural Context
{STRUCTURAL_CONTEXT}

## Key Points (logic anchors — suggestions must NOT break these)
Read `{WORK_DIR}/00_key_points.md`

## Text to Review
Read `{WORK_DIR}/01_original_text.md`

## Review Instructions
- Output a NUMBERED list of specific, actionable review comments
- Each comment must reference the specific paragraph/sentence it applies to
- Focus on: language clarity, argument flow, sentence structure, academic tone
- Do NOT suggest adding/removing/changing citations
- Do NOT suggest restructuring the overall argument logic
- Word count target: {ORIGINAL_WORD_COUNT} ± 10%

## Output Format
1. [Para X, Line Y] Comment: {specific issue} → Suggestion: {specific fix}
2. [Para X, Line Y] Comment: ... → Suggestion: ...
...
N. [Overall] Comment: ... → Suggestion: ...
```

保存审稿意见 → `{WORK_DIR}/02_review_r1.md`

### 3.2 用户确认

将审稿意见展示给用户，AskUserQuestion：

```
📋 第1轮审稿意见（共 N 条）：

1. [Para X, Line Y] {comment} → {suggestion}
2. [Para X, Line Y] {comment} → {suggestion}
...

请对每条意见选择操作：
- 输入接受的编号（如 "1,3,5" 或 "all"）
- 输入拒绝的编号（如 "reject 2,4"）
- 可以对某条意见提出修改（如 "3: 改为..."）
```

用户确认后，生成 `{CONFIRMED_CHANGES}` = 用户接受的意见列表。保存 → `{WORK_DIR}/02_confirmed_r1.md`

### 3.3 sci-writer 执行修改

调用 sci-writer（`subagent_type: "sci-writer"`），prompt 要素：

```
Read `drafts/writing_brief.md` for journal conventions and style guidance. Pay special attention to the **Journal Profile** section for the journal's aesthetic preferences.

## Section: {SECTION_TITLE}
## Mode: Polish — Execute confirmed review comments only

## Key Points (logic anchors — MUST be preserved exactly)
Read `{WORK_DIR}/00_key_points.md`

## Current Version
Read `{WORK_DIR}/01_original_text.md`

## Confirmed Changes to Execute
Read `{WORK_DIR}/02_confirmed_r1.md`

ONLY execute the changes listed above. Do NOT make additional changes.
If a confirmed change conflicts with the key points, preserve the key points and skip that change.

## Citation Protection (CRITICAL)
- Do NOT add, remove, or change any citation key in \citet{} or \citep{} commands
- Do NOT change citation form (\citet → \citep or vice versa)
- Do NOT reorder, merge, or split citation groups
- If a confirmed change involves citations, IGNORE that part and only change the surrounding prose
- The ONLY allowed changes are to the surrounding prose text, not the citations themselves

## Constraints
- Word target: {ORIGINAL_WORD_COUNT} ± 10%
- Do NOT use \textbf{}
- Preserve all data, numbers, and factual claims exactly as in the original

## Output
1. Complete revised LaTeX content in a ```latex``` code block
2. Change log: for each confirmed change, state what was done
3. Actual word count
4. Key Point Verification table confirming all key points are preserved
```

保存修改版 → `{WORK_DIR}/03_revision_r1.md`

## 步骤 4：第2轮审稿（可选）

### 4.1 询问用户

AskUserQuestion：
```
第1轮修改完成。是否进行第2轮审稿？
(1) 进行第2轮
(2) 跳过，直接进入语言润色
```

用户选 (2) → 直接进入步骤 5。

### 4.2 第2轮审稿-确认-修改

如果用户选 (1)：

**4.2a strict-reviewer 审稿**：同步骤 3.1 的逻辑，但待审文本改为 `{WORK_DIR}/03_revision_r1.md`，标注"第2轮"。保存 → `{WORK_DIR}/04_review_r2.md`

**4.2b 用户确认**：同步骤 3.2。保存 → `{WORK_DIR}/04_confirmed_r2.md`

**4.2c sci-writer 修改**：同步骤 3.3，当前版本改为 `03_revision_r1.md`，确认清单改为 `04_confirmed_r2.md`。保存 → `{WORK_DIR}/05_revision_r2.md`

## 步骤 5：language-polisher 最终润色

调用 language-polisher（`subagent_type: "language-polisher"`），prompt 要素：

```
Read `drafts/writing_brief.md` for journal conventions and style guidance. Refer to the **Journal Profile** section for the journal's tone and style preferences.

## Section: {SECTION_TITLE}
## Mode: Language polish (final step after review cycles)

## Structural Context
{STRUCTURAL_CONTEXT}

## Key Points (meaning, strength, and scope MUST NOT change)
Read `{WORK_DIR}/00_key_points.md`

## Text to Polish
Read `{WORK_DIR}/{最新版本文件}`
（如果跑了第2轮 → 05_revision_r2.md；否则 → 03_revision_r1.md）

## Instructions
- Improve grammar, coherence, sentence flow, and naturalness
- Preserve all academic content, arguments, and structure
- Do NOT restructure paragraphs or change argument order

## Citation Protection (CRITICAL)
- Do NOT add, remove, or change any citation key in \citet{} or \citep{} commands
- Do NOT change citation form (\citet → \citep or vice versa)
- Do NOT reorder, merge, or split citation groups
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

## 步骤 6：生成输出文件

### 文件 1：`{WORK_DIR}/changelog.md`

含 Section、Date、Mode: Polish、Work Directory、Structural Context、Key Points 摘要、Original → Final word count、各轮审稿意见摘要（含用户接受/拒绝决策）、Language Polish 摘要、逻辑完整性确认

### 文件 2：`{WORK_DIR}/final.md`

从 `06_polished.md` 提取 ` ```latex``` ` code block，包裹为：

```markdown
# {Section Title} — Polished Version

> Ready to copy · Replaces original text in manuscript.tex

```latex
{LaTeX content from 06_polished.md}
```

**Target location**: manuscript.tex, {section position info}
**Word count**: {original} → {final}
**Review rounds**: {1 或 2}
**Key point integrity**: {X}/{Y} preserved
```

### 文件 3：`_latest_final.md`（便捷入口）

`drafts/{HIERARCHY_PREFIX}/{SECTION_NAME}_latest_final.md`，复制 `final.md` 内容，已存在则覆盖。

## 步骤 7：完成提示

显示：
- ✅ 完成状态
- 📂 工作目录路径 / 便捷入口路径
- 字数变化：{original} → {final}
- 审稿轮数：{1 或 2}
- 要点完整性：{X}/{Y} preserved
- Checkpoint 文件清单（00_key_points → ... → 06_polished → final）
- 💡 提醒手动替换 manuscript.tex 中的对应文本
