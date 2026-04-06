---
description: "从章节大纲自动读取素材，生成论文初稿（Pipeline：journal-scout → 并行 sci-writer）"
---

# Draft Workflow — 从 structure/ 素材生成初稿

自动读取 `structure/` 下的章节 md、citation pool 和 idea.md，调用 sci-writer 生成初稿。后续审稿润色由 `/pen-polish` 完成。

**架构**：

- **Form 1**（原子写作单元）：写单个 section / subsection / 隐形段落。被 Form 2 和 Form 3 调用，也可独立运行。
- **Form 2**（调度器-真实 subsection）：tex 中有 `\subsection` → 从 md 读字数 → **并行**调 Form 1 → 输出带 `\subsection{}` 标题
- **Form 3**（调度器-隐形结构）：tex 中无 `\subsection`，md 中有 `###` 隐形段落 → 从 md 读字数 → **并行**调 Form 1 → 拼接为连续文本

**输入** `$ARGUMENTS`：`section=XXX`（必须）。

## 步骤 0：前置准备

### 0.1 解析 `$ARGUMENTS`

- 提取 `section` 参数
- 无 `section` → AskUserQuestion 询问要写哪个 section

### 0.2 获取项目文件路径

- 从 CLAUDE.md 获取主文件和 bib 文件路径
- Fallback：Glob("*.tex") 查找含 `\documentclass` 的文件（排除 supplementary/appendix/*.cls）
- 读取主文件了解论文结构

### 0.3 构建 Section Tree `{SECTION_TREE}`（Python 脚本）

**由 Python 脚本自动完成**，替代主 Agent 手动正则解析。

```bash
python3 ~/.claude/skills/shared/tex_section.py section-tree --tex {主文件路径}
```

脚本解析所有 `\section{}`/`\subsection{}`/`\subsubsection{}` 命令（忽略 `*` 变体），构建含父子/兄弟/前后关系的树，输出 `_section_tree.json`。VERIFY 必须为 PASS。

### 0.4 匹配 section + 判定 Form（Python 脚本 + 主 Agent 判定 Form）

**匹配由 Python 脚本完成**：

```bash
python3 ~/.claude/skills/shared/tex_section.py match-section \
  --tree _section_tree.json --query "{section参数}"
```

脚本输出 `_section_match.json`，含匹配结果、子节点列表、父子关系。VERIFY 为 PASS 表示匹配成功，FAIL 表示未找到（列出所有可用 section 供用户选择）。

**主 Agent 基于匹配结果判定 Form**：
- `has_children` = true → `{INPUT_FORM}` = "multi"（Form 2），`{SPLIT_SEGMENTS}` = children 列表
- `has_children` = false → 进一步检查章节 md：
  - md 的 `## 大纲` 下有 `### ` 子标题且有字数分配表 → `{INPUT_FORM}` = "implicit-multi"（Form 3）
  - 否则 → `{INPUT_FORM}` = "single"（Form 1）
- **匹配失败** → AskUserQuestion 让用户从脚本列出的 section 中选择

### 0.5 方法论审计检查（仅技术章节）

当目标 section 匹配以下关键词时触发检查：`model/method/formul/equilibrium/result/analysis/simulation/numerical`

- 检查 `drafts/method_audit_report.md` 是否存在
- **不存在** → 警告用户：
  ```
  ⚠️ 检测到你正在 draft 技术章节（{section name}），但尚未运行 /method-audit。
  建议先运行 /method-audit 完成方法论审计，再生成初稿。
  - 继续 draft（跳过审计）→ 输入 "continue"
  - 先去审计 → 输入 "stop"
  ```
- **存在但有未修复的 🔴 MUST-FIX** → 警告用户：
  ```
  ⚠️ method_audit_report.md 中仍有 {N} 条 🔴 MUST-FIX 未处理。
  建议先处理完再 draft，否则 draft 后可能需要大幅修改。
  - 继续 draft → 输入 "continue"
  - 先去处理 → 输入 "stop"
  ```
- **存在且无红色项** → 静默通过

**成稿 md 填充检查**（紧接审计检查之后）：

读取该 section 对应的成稿 md 文件，检查 `## 正文要点` 下是否仍有大量 `TODO` 占位符：
- **全部或大部分 subsection 仍为 TODO** → 警告用户：
  ```
  ⚠️ {md文件名} 的正文要点大部分仍为 TODO，尚未被 /method-end 填充。
  /pen-draft 需要完整的成稿 md 作为输入，直接 draft 可能产出空洞内容。
  - 先运行 /method-end 填充成稿 md → 输入 "stop"
  - 仍然继续 draft → 输入 "continue"
  ```
- **已有实质内容** → 静默通过
- **叙述型章节** → 跳过此检查（叙述型通过 /pen-outline 填充大纲）

### 0.6 定位源文件

- **章节 md 文件**：找到匹配 section 的顶层父 section，扫描 `structure/` 子目录用关键词匹配目录名：

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

记录 `{CHAPTER_MD_PATH}`

- **citation pool 文件**（Python 脚本）：
```bash
python3 ~/.claude/skills/shared/tex_section.py citation-paths --chapter-md {CHAPTER_MD_PATH}
```
从 `_citation_paths.json` 读取 `citation_pool_paths` → `{CITATION_POOL_PATHS}`。如无引用池区块 → 空列表，不报错
- **全局上下文**：固定读取 `structure/0_global/idea.md` → `{IDEA_PATH}`

### 0.7 创建工作目录

**`normalize(title)`**：空格→下划线，Capitalized_Words 风格，> 40 字符在最后完整单词边界截断。

- **Form 1**：`drafts/{HIERARCHY_PREFIX}/{SECTION_NAME}_{序号:03d}/`（HIERARCHY_PREFIX = 祖先标题 normalize 后 "/" 连接，顶级为空）
- **Form 2/3**：`{MULTI_BASE_DIR}` = `drafts/{PARENT_HIERARCHY}/`，子工作目录在步骤 2 并行调用中创建

## 步骤 1：生成 Writing Brief

1. **复用检查**：读取 `drafts/writing_brief.md`，检查 `## Metadata` 中的 `Generated` 时间戳（> 24h→重新生成）和 `Manuscript word count`（变化 > 20%→重新生成）。两项通过→复用
2. **Web 搜索**（主 agent 执行）：从 `\journal{}` 提取期刊名，使用 `WebSearch` 工具搜索期刊投稿指南。如需深入获取页面内容，加载 web-access skill 通过 CDP 访问
3. **调用 journal-scout**（`subagent_type: "journal-scout"`）：prompt 含 manuscript 分析 + web 搜索结果
4. **保存**：提取 `---BEGIN/END WRITING BRIEF---` 之间内容→`drafts/writing_brief.md`
5. **展示**：期刊名称、研究情境、信息来源

## 步骤 2：调度

根据 `{INPUT_FORM}` 分派。**三个子步骤互斥，只走一个**。

### 2.1 Form 1（单节）

直接进入步骤 3，传入：
- `{CHAPTER_MD_CONTENT}` = 章节 md 中对应区块（顶级 section 读全文，子 section 按 heading 提取）
- `{WORD_TARGET}` = null（由 sci-writer 根据大纲密度自行判断）

### 2.2 Form 2（真实 subsection）

**2.2a 解析段落列表**：

- `{SPLIT_SEGMENTS}` = tex 中的 `\subsection` 列表（步骤 0.4 已解析）
- 对每个 subsection：从 `{CHAPTER_MD_PATH}` 按 heading 匹配提取内容。
  - **叙述型章节**：从 `## 大纲` 区块提取（intent + 要点）
  - **技术型章节**：从 `## 正文要点` 区块提取（凝练后的正文要点）
  - 匹配规则：忽略编号前缀（如 "### 2.1 "），对标题部分做模糊匹配（忽略大小写）。匹配失败 → 使用章节 md 全文并警告
- 从 md 的字数分配表匹配每个 subsection 的目标字数 → `{WORD_TARGETS}`

**2.2b 判定写作模式**：

根据章节类型判定调度策略：

- **叙述型章节**（Introduction, Literature Review, Discussion）→ `{WRITE_MODE}` = "parallel"
- **技术型章节**（Methodology, Results, Simulation 等）→ `{WRITE_MODE}` = "sequential"

**判定依据**：技术型章节的 subsection 有强顺序依赖（前面的 subsection 定义符号/假设/模型，后面的 subsection 引用和扩展），并行写作会导致术语和符号不一致。叙述型章节的 subsection 相对独立，并行写作效率更高。

**2.2c 确认**（AskUserQuestion）：

- Parent section 名称
- Subsection 列表 + 各自目标字数
- 写作模式：并行 / 串行
- 源文件列表：`{CHAPTER_MD_PATH}` + `{CITATION_POOL_PATHS}`
- 预计 agent 调用次数：N 次 sci-writer（{并行/串行}）

等待用户确认。

**2.2d 写作执行**：

根据 `{WRITE_MODE}` 分派：

**并行模式**（叙述型章节）：

读取 `{IDEA_PATH}`、`{CITATION_POOL_PATHS}` 等共享上下文后，按**槽位制**调用 N 个 sci-writer agent（同时不超过 8 个，完成一个补一个）：

```
FOR EACH subsection IN {SPLIT_SEGMENTS} (PARALLEL):
  a. 创建工作目录 {WORK_DIR} = {MULTI_BASE_DIR}/{normalize(subsection.title)}_{序号:03d}/
  b. 执行步骤 3（传入：subsection 内容 + 字数 + 位置信息）
END FOR
```

**串行模式**（技术型章节）：

读取共享上下文后，按 subsection 顺序**逐个**调用 sci-writer agent。每个 agent 额外接收前序 subsection 的已完成输出作为上下文：

```
SET {PRIOR_OUTPUTS} = ""

FOR EACH subsection IN {SPLIT_SEGMENTS} (SEQUENTIAL):
  a. 创建工作目录 {WORK_DIR} = {MULTI_BASE_DIR}/{normalize(subsection.title)}_{序号:03d}/
  b. 执行步骤 3（传入：subsection 内容 + 字数 + 位置信息 + {PRIOR_OUTPUTS}）
  c. 读取输出 → 追加到 {PRIOR_OUTPUTS}：
     {PRIOR_OUTPUTS} += "\n\n## Previously written: {subsection.title}\n{该 subsection 的 LaTeX 输出}"
  d. 显示进度："✓ [{i}/{N}] {subsection.title} — {word_count} words"
END FOR
```

> **串行模式的 sci-writer prompt 额外指令**：在步骤 3.2 的 prompt 中追加：
> ```
> ## Previously Written Subsections (for consistency)
> {PRIOR_OUTPUTS}
>
> IMPORTANT: Maintain exact consistency with the notation, terminology, and
> definitions established in the previously written subsections above.
> Do not redefine symbols or introduce alternative notation.
> ```

### 2.3 Form 3（隐形结构 — 并行调度）

**2.3a 解析段落列表**：

从 `{CHAPTER_MD_PATH}` 的 `## 大纲` 区块中提取：
- 字数分配表（目标总字数、各子节目标字数、写作说明）
- 各 `### ` 子标题及其下的 intent 和要点
- `{SPLIT_SEGMENTS}` = md 中 `### ` 子标题列表

**2.3b 确认**（AskUserQuestion）：

- Section 名称
- 隐形段落列表 + 各自目标字数 + 写作说明
- 源文件列表
- 预计 agent 调用次数：N 次并行 sci-writer

等待用户确认。

**2.3c 并行写作**：

读取 `{IDEA_PATH}`、`{CITATION_POOL_PATHS}` 等共享上下文后，按**槽位制**调用 N 个 sci-writer agent（同时不超过 8 个，完成一个补一个）：

```
FOR EACH implicit_segment IN {SPLIT_SEGMENTS} (PARALLEL):
  a. 创建工作目录 {WORK_DIR} = {MULTI_BASE_DIR}/{normalize(segment.title)}_{序号:03d}/
  b. 执行步骤 3（传入：段落内容 + 字数 + 位置信息："你正在写 {section title} 的第 {i}/{N} 个逻辑段落，前面是 {prev}，后面是 {next}"）
END FOR
```

## 步骤 3：原子写作单元（Form 1 核心）

被步骤 2.1 / 2.2c / 2.3c 调用。

### 3.1 读取并组装源材料

1. 读取 `{IDEA_PATH}` → `{IDEA_CONTEXT}`（idea.md 全文）
2. 读取传入的章节 md 内容 → `{CHAPTER_MD_CONTENT}`（由步骤 2 提取好的对应区块）
3. 读取 `{CITATION_POOL_PATHS}` 中所有文件 → `{CITATION_POOL_CONTENT}`
4. 生成 Structural Context：

```
### Structural Context
- Paper structure position: {完整路径}
- Parent section: {parent title 或 "Top level (no parent)"}
- Sibling sections: {同级列表}
- Preceding/Following section: {前/后同级或 "None"}
- Role in paper: {基于位置推断的角色}
```

5. 保存 `{WORK_DIR}/00_source_context.md`

### 3.2 调用 sci-writer 撰写初稿

调用 sci-writer（`subagent_type: "sci-writer"`），prompt 要素：

```
You are writing **{Section Title}** for this manuscript.

## Mode: Draft (first draft from outline)

## Structural Context
{STRUCTURAL_CONTEXT}

## Instructions
- Read `drafts/writing_brief.md` for journal conventions and style guidance
- Read the bib file for available citations
- Do NOT read the manuscript file. All necessary context (structure, notation, prior subsection outputs) is provided in this prompt. Reading the manuscript risks being influenced by existing content that is being replaced.

## Research Context (from idea.md)
{IDEA_CONTEXT}

## Outline and Key Points (from {CHAPTER_MD_PATH 的文件名})
{CHAPTER_MD_CONTENT}

This outline contains ALL the content points, arguments, and citation keys you need.
Every point in this outline must appear in the draft. Treat them as non-negotiable
key points — do not omit, weaken, or reinterpret any point.

## Available Citations
{CITATION_POOL_CONTENT}

Use these citation keys following the outline's citation markers:
- `\citet{key}` = author as subject: "Smith (2020) found that..." — use when highlighting a specific study's findings
- `\citep{key}` = parenthetical: "...recent findings (Smith, 2020)" — use for general claims supported by multiple sources
- `\citep{key1, key2}` = multiple parenthetical: "...observed across industries (Smith, 2020; Jones, 2021)"
If the outline specifies `\citet{}` for a point, the author MUST appear as subject in the sentence.
If the outline specifies `\citep{}`, use parenthetical citation.
Only use keys that appear in the outline above or in this citation pool.
Where a citation is clearly needed but no key is available, mark with (ref).

## Constraints
- Word target: {WORD_TARGET}±10% (if unspecified, judge based on outline density and note actual count)
- Do NOT use \textbf{}
- Do NOT invent citations — only use keys from the outline or citation pool
- Ensure every outline point is covered; do not add arguments not in the outline or idea.md

## Citation Density Requirement
- Every factual claim or literature-based argument MUST have at least one citation
- Maximum 2 citations per claim (hard limit 3), prefer 1-2
- Only transition sentences and the author's own arguments may be uncited
- When in doubt, ADD a citation — the author will remove excess ones

## Output
1. Complete LaTeX content in a ```latex``` code block
2. Actual word count
3. Key Point Verification table confirming every outline point is covered
```

### 3.3 保存输出

从 sci-writer 返回中提取 ` ```latex``` ` code block，包裹为：

```markdown
# {Section Title} — First Draft

> Ready to copy · Run `/pen-polish` to review and refine

```latex
{LaTeX content from sci-writer}
```

**Target location**: manuscript.tex, {section position info from STRUCTURAL_CONTEXT}
**Word count**: {N}
**Key point coverage**: {X}/{Y} points covered
```

保存到 `{WORK_DIR}/final.md`。

**便捷入口** `_latest_final.md`：
- Form 1: `drafts/{HIERARCHY_PREFIX}/{SECTION_NAME}_latest_final.md`
- Form 2: `drafts/{PARENT_HIERARCHY}/{normalize(subsection.title)}_latest_final.md`
- Form 3: `drafts/{HIERARCHY_PREFIX}/{SECTION_NAME}_latest_final.md`（指向拼接后的完整文件）
- 复制 `final.md` 内容，已存在则覆盖

## 步骤 4：后处理

### 4.1 拼接（仅 Form 3）

收集 N 个 agent 的输出后，按顺序拼接，保存到 `{MULTI_BASE_DIR}/final.md`。拼接时不加 `\subsection{}` 标题（隐形结构→连续文本）。

Form 2 不拼接——每个 subsection 的 `final.md` 保持独立。

### 4.2 Bib 验证（仅检查，不同步）

> **Bib 同步已前移**：citation key 到项目 bib 的同步由 `/method-end`（步骤 2.6）和 `/pen-outline`（步骤 7）在确认要点时完成。`/pen-draft` 不再负责 bib 同步，仅做验证。

适用于所有 Form。扫描 draft 文件中的 citation key，验证是否全部存在于项目 bib 中：

1. 从 draft 文件提取所有 `\citep{}`/`\citet{}` 中的 citation key
2. 检查每个 key 是否在项目 bib 中存在
3. 如有缺失 key → 尝试从 master.bib 补充（兜底，正常流程不应触发）→ 显示警告提醒用户
4. 质量检测：key 中的年份与 bib 条目 year 字段是否一致

**draft 文件选择规则**：
- Form 1：`{WORK_DIR}/final.md`
- Form 2：所有子节的 `final.md`
- Form 3：拼接后的 `{MULTI_BASE_DIR}/final.md`

## 步骤 5：完成提示

### Form 1
显示：
- ✅ 完成状态
- 📂 读取的源文件列表
- 工作目录路径 / 便捷入口路径
- 字数统计
- Key point coverage
- Bib 验证：N 个 key 全部存在 / M 个缺失已兜底补充（列出补充的 key）
- 💡 提示：运行 `/pen-polish` 进行审稿和润色

### Form 2
显示：
- ✅ 全部 {N} 个 subsection 完成
- 基础目录 `{MULTI_BASE_DIR}`
- 汇总表：Subsection / 工作目录 / 便捷入口 / 字数 / Key point coverage
- Bib 验证：N 个 key 全部存在 / M 个缺失已兜底补充（列出补充的 key）
- 💡 提示：逐个或整体运行 `/pen-polish` 进行审稿和润色
- ⚠️ 提醒手动合并到 manuscript.tex

### Form 3
显示：
- ✅ 全部 {N} 个隐形段落完成并拼接
- 工作目录 `{MULTI_BASE_DIR}`
- 便捷入口路径
- 汇总表：段落名称 / 字数
- 总字数
- Bib 验证：N 个 key 全部存在 / M 个缺失已兜底补充（列出补充的 key）
- 💡 提示：运行 `/pen-polish` 进行审稿和润色
- ⚠️ 提醒手动合并到 manuscript.tex
