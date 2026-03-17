---
description: "从章节大纲自动读取素材，生成论文初稿（2-Agent Pipeline：journal-scout → sci-writer）"
---

# Draft Workflow — 从 structure/ 素材生成初稿

自动读取 `structure/` 下的章节 md、citation pool 和 idea.md，调用 sci-writer 生成初稿。后续审稿润色由 `/polish` 完成。

**执行模式**：Form 1（单节）直接运行；Form 2（有子节的 section）自动拆分，逐个子节运行。

**输入** `$ARGUMENTS`：`section=XXX`（必须），可选 `words=500`。`words` 支持全局（`words=500`）、按节（`words=Measures:300,Model:500`）、自然语言（`Measures 300字`）。

## 步骤 0：前置准备

### 0.1 解析 `$ARGUMENTS`

- 提取 `section` 和 `words` 参数
- `words` 解析：纯数字→`{"_global": N}`，键值对/自然语言→`{"SectionName": N, ...}`，未指定→`{}`。键名匹配忽略大小写和下划线/空格差异
- 无 `section` → AskUserQuestion 询问要写哪个 section

### 0.2 获取项目文件路径

- 从 CLAUDE.md 获取主文件和 bib 文件路径
- Fallback：Glob("*.tex") 查找含 `\documentclass` 的文件（排除 supplementary/appendix/*.cls）
- 读取主文件了解论文结构

### 0.3 构建 Section Tree `{SECTION_TREE}`

- 正则 `\\(section|subsection|subsubsection)\{([^}]+)\}` 提取所有 section 命令（忽略 `*` 变体）
- 记录级别、标题、行号，构建父子关系树，记录 parent/children/siblings/preceding/following

### 0.4 Section 匹配与 Form 判定

将 `section=XXX` 在 `{SECTION_TREE}` 中匹配：

- **匹配规则**：先精确匹配，后模糊匹配（忽略大小写、"and"/"&"互换、冠词省略）
- **有子 section** → `{INPUT_FORM}` = "multi"，`{SPLIT_SEGMENTS}` = 子 section 列表
- **无子 section** → `{INPUT_FORM}` = "single"
- **匹配失败** → 列出 `{SECTION_TREE}` 中所有可用 section，AskUserQuestion 让用户选择

### 0.5 构建层级路径

**`normalize(title)`**：空格→下划线，Capitalized_Words 风格，> 40 字符在最后完整单词边界截断。示例："Research methods" → `Research_methods`

**Form 1**：`{SECTION_NAME}` = normalize(标题)。`{HIERARCHY_PREFIX}` = 祖先标题 normalize 后 "/" 连接（顶级为空，二级=parent，三级=grandparent/parent）

**Form 2**：`{HIERARCHY_PREFIX}` 同 Form 1 规则。`{PARENT_HIERARCHY}` = `{HIERARCHY_PREFIX}/{normalize(parent)}`（parent 为顶级时 = normalize(parent)）

### 0.6 自动解析源文件 `{SOURCE_FILES}`

从匹配到的 section 自动定位需要读取的素材文件：

**a. 定位章节 md 文件**：

1. 找到匹配 section 的**顶层父 section**（如 "Platform economics..." → 父 "Literature review"）
2. 扫描 `structure/` 子目录，用关键词匹配目录名：

```
section 关键词        → 目录
introduction         → structure/1_introduction/introduction.md
literature           → structure/2_literature/literature.md
model/method/formul  → structure/3_methodology/methodology.md
equilibrium/result/analysis → structure/4_results/results.md
simulation/numerical → Glob("structure/*simulation*/simulation.md") 动态匹配
discussion           → Glob("structure/*discussion*/discussion.md") 动态匹配
conclusion           → 无对应 md，停止并提示用户
```

3. 记录 `{CHAPTER_MD_PATH}`

**b. 定位 citation pool 文件**：

1. 读取 `{CHAPTER_MD_PATH}`
2. 查找底部 `## 引用池` 区块（或 `## Citation Pool`）
3. 解析该区块中列出的 citation pool 文件路径（格式如 `→ 见 \`2_literature/citation_pool/LR.md\``）
4. 构建完整路径列表 → `{CITATION_POOL_PATHS}`
5. 如无引用池区块 → `{CITATION_POOL_PATHS}` = 空列表，不报错

**c. 全局上下文**：

- 固定读取 `structure/0_global/idea.md` → `{IDEA_PATH}`

### 0.7 创建工作目录

**Form 1**：父目录 = `drafts/{HIERARCHY_PREFIX}/`（空则 `drafts/`），查找 `{SECTION_NAME}_*` 最大序号，创建 `{SECTION_NAME}_{序号+1:03d}`

**Form 2**：`{MULTI_BASE_DIR}` = `drafts/{PARENT_HIERARCHY}/`，递归创建。子工作目录在步骤 1.5 循环中创建

### 0.8 生成 Structural Context

```
### Structural Context
- Paper structure position: {完整路径}
- Parent section: {parent title 或 "Top level (no parent)"}
- Sibling sections: {同级列表}
- Preceding/Following section: {前/后同级或 "None"}
- Role in paper: {基于位置推断的角色}
```
Form 1 直接生成 `{STRUCTURAL_CONTEXT}`；Form 2 在循环中为每个 child 分别生成。

## 步骤 1：生成 Writing Brief

**1. 复用检查**：读取 `drafts/writing_brief.md`，检查 `## Metadata` 中的 `Generated` 时间戳（> 24h→重新生成）和 `Manuscript word count`（变化 > 20%→重新生成）。两项通过→复用，跳到步骤 1.5/2

**2. Web 搜索**（主 agent 执行）：从 `\journal{}` 提取期刊名，依次尝试 `mcp__web-search-prime__webSearchPrime`→`mcp__MiniMax__web_search`→"Knowledge base only"

**3. 调用 journal-scout**（`subagent_type: "journal-scout"`）：
- prompt: `Analyze the manuscript and generate a Writing Brief. ## Web Search Results: {结果} ## Journal Info Source: {来源}. Output the complete Writing Brief.`

**4. 保存**：提取 `---BEGIN/END WRITING BRIEF---` 之间内容→`drafts/writing_brief.md`

**5. 展示**：期刊名称、研究情境、信息来源

## 步骤 1.5：Form 2 调度控制

`{INPUT_FORM}` = "single" → 跳过，直接执行步骤 2-4。

**1.5a 确认**：AskUserQuestion 显示：
- Parent section / Hierarchy
- Children 列表
- 将读取的 md 文件：`{CHAPTER_MD_PATH}`
- 将读取的 citation pool 文件：`{CITATION_POOL_PATHS}`
- 预计 agent 调用次数：N 次（每个子 section 1 次 sci-writer）
- 字数预算（如有）

等待用户确认。

**1.5b 循环处理**：
```
FOR i, child IN enumerate({SPLIT_SEGMENTS}):
  a. 设置变量：{CURRENT_SECTION_NAME} = normalize(child.title)，{CURRENT_TITLE} = child.title
     解析 {CURRENT_WORD_TARGET}（按节>全局>null）
  b. 从 {CHAPTER_MD_PATH} 按 heading 提取该子 section 内容：
     匹配规则：忽略编号前缀（如 "2.1 "），对标题部分做模糊匹配（忽略大小写）
     即 `### 2.1 Platform economics...` 可匹配 section tree 中的 "Platform economics..."
     匹配失败 → 使用章节 md 全文并警告
  c. 创建工作目录 {WORK_DIR} = {MULTI_BASE_DIR}/{CURRENT_SECTION_NAME}_{序号:03d}/
  d. 生成该子 section 的 Structural Context
  e. 显示 "▶ [{i+1}/{total}]: {CURRENT_TITLE}"
  f. 执行步骤 2-3（单 section 流水线，复用 Writing Brief）
  g. 显示 "✓ [{i+1}/{total}] done: {WORK_DIR}"
END FOR
```
完成后跳转步骤 4 汇总。

## 步骤 2：读取并组装源材料

> 步骤 2-3 = 单 section 流水线（Form 1 执行一次，Form 2 每个子 section 重复）

**动作**：

1. 读取 `{IDEA_PATH}` → `{IDEA_CONTEXT}`（idea.md 全文）
2. 读取章节 md → `{CHAPTER_MD_CONTENT}`：
   - Form 1 且顶级 section：读取 md 全文
   - Form 1 且子 section：按 heading 提取对应区块
   - Form 2：在步骤 1.5b 中已提取
3. 读取 `{CITATION_POOL_PATHS}` 中所有文件 → `{CITATION_POOL_CONTENT}`
4. 保存 `{WORK_DIR}/00_source_context.md`：

```markdown
# Source Context — {Section Title}
Generated: {date}

## Files Read
- **Global**: structure/0_global/idea.md
- **Chapter md**: {CHAPTER_MD_PATH} (全文 / subsection "{title}")
- **Citation pools**: {逐行列出文件路径}

## Chapter MD Content
{CHAPTER_MD_CONTENT}

## Citation Pool Content
{CITATION_POOL_CONTENT}
```

5. 自动继续步骤 3

## 步骤 3：调用 sci-writer 撰写初稿

调用 sci-writer（`subagent_type: "sci-writer"`），prompt 要素：

```
You are writing **{Section Title}** for this manuscript.

## Mode: Draft (first draft from outline)

## Structural Context
{STRUCTURAL_CONTEXT}

## Instructions
- Read `drafts/writing_brief.md` for journal conventions and style guidance
- Read the manuscript file for overall structure awareness
- Read the bib file for available citations

## Research Context (from idea.md)
{IDEA_CONTEXT}

## Outline and Key Points (from {CHAPTER_MD_PATH 的文件名})
{CHAPTER_MD_CONTENT}

This outline contains ALL the content points, arguments, and citation keys you need.
Every point in this outline must appear in the draft. Treat them as non-negotiable
key points — do not omit, weaken, or reinterpret any point.

## Available Citations
{CITATION_POOL_CONTENT}

Use these citation keys with \citet{} or \citep{} as appropriate.
Only use keys that appear in the outline above or in this citation pool.
Where a citation is clearly needed but no key is available, mark with (ref).

## Constraints
- Word target: {words}±10% (if unspecified, judge based on outline density and note actual count)
- Do NOT use \textbf{}
- Do NOT invent citations — only use keys from the outline or citation pool
- Ensure every outline point is covered; do not add arguments not in the outline or idea.md

## Output
1. Complete LaTeX content in a ```latex``` code block
2. Actual word count
3. Key Point Verification table confirming every outline point is covered
```

**输出**：`{WORK_DIR}/final.md`

从 sci-writer 返回中提取 ```latex``` code block，包裹为：

```markdown
# {Section Title} — First Draft

> Ready to copy · Run `/polish` to review and refine

```latex
{LaTeX content from sci-writer}
```

**Target location**: manuscript.tex, {section position info from STRUCTURAL_CONTEXT}
**Word count**: {N}
**Key point coverage**: {X}/{Y} points covered
```

**便捷入口** `_latest_final.md`：
- Form 1: `drafts/{HIERARCHY_PREFIX}/{SECTION_NAME}_latest_final.md`（顶级 section 省略 prefix）
- Form 2: `drafts/{PARENT_HIERARCHY}/{CURRENT_SECTION_NAME}_latest_final.md`
- 复制 `final.md` 内容，已存在则覆盖

## 步骤 4：完成提示

### Form 1
显示：
- 完成状态
- 读取的源文件列表
- 工作目录路径 / 便捷入口路径
- 字数统计
- Key point coverage
- 提示：运行 `/polish` 进行审稿和润色

### Form 2
显示：
- 全部 {N} 个子 section 完成
- 基础目录 `{MULTI_BASE_DIR}`
- 汇总表：子 Section / 工作目录 / 便捷入口 / 字数 / Key point coverage
- 提示：逐个或整体运行 `/polish` 进行审稿和润色
- 提醒手动合并到 manuscript.tex
