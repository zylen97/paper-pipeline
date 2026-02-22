---
description: "从大纲/要点撰写论文段落（4-Agent Pipeline：journal-scout → sci-writer → strict-reviewer → language-polisher）"
---

# Draft Workflow — 从大纲/要点撰写

用户通过选中文本或直接输入提供大纲、要点或需要重写的文本段落，本工作流调用四个 agent 完成从期刊识别到润色的全流程。

支持两种执行模式：
- **Form 1（单节）**：输入对应单个 section → 直接运行完整流水线
- **Form 2（多节）**：输入包含多个需独立处理的 section → 按 section 拆分，依次运行流水线

## 输入说明

用户输入 `$ARGUMENTS`，格式为：
- 直接传入大纲/要点文本
- 可选参数用 `|` 分隔：`大纲文本 | section=Introduction | words=500`
- 字数参数支持多种格式（由 Claude 智能解析，无需严格语法）：
  - **全局字数**：`words=500`（所有 section 共享）
  - **按节指定（结构化）**：`words=Measures:300,Model_settings:500`
  - **按节指定（自然语言）**：`Measures 300字，Model settings 500字` 或 `measures大概300字 model settings控制在500字`
- 如果用户在 VS Code 中选中了文本，选中内容会作为 `$ARGUMENTS` 传入

## 步骤 0：解析输入与前置检查

1. **解析 `$ARGUMENTS`**：
   - 提取主体内容（大纲/要点文本）
   - 提取可选参数：`section`（section 名称，用于输出文件命名）、`words`（目标字数）
   - **`words` 参数解析**（支持结构化和自然语言输入）：
     - 纯数字（如 `words=500`）→ `{WORD_BUDGETS}` = `{"_global": 500}`
     - 键值对（如 `words=Measures:300,Model_settings:500`）→ `{WORD_BUDGETS}` = `{"Measures": 300, "Model_settings": 500}`
     - 自然语言（如 `Measures 300字，Model settings 500字`）→ 智能提取 section 名称和字数，结果同键值对格式
     - 键名匹配规则：与 section 标题匹配时忽略大小写和下划线/空格差异（即 `Measures` 匹配 `measures`、`MEASURES`）
     - 未指定 `words` → `{WORD_BUDGETS}` = `{}`（空）
   - 如果 `$ARGUMENTS` 为空或过短（少于 20 个字符），停止并提示用户："请提供大纲/要点文本后重新调用 /draft。Draft 工作流需要大纲内容作为输入。"
   - 如果没有指定 section，从内容中推断或询问用户

2. **获取项目文件路径**：
   - 从 CLAUDE.md 获取主文件路径（`主文件` 字段）和参考文献文件路径
   - 如果 CLAUDE.md 未声明主文件，fallback：使用 Glob("*.tex") 查找包含 `\documentclass` 的文件，排除 supplementary*.tex、appendix*.tex 和 *.cls
   - 读取主文件，了解当前论文结构和上下文

3. **引用格式预处理**（仅当输入包含全角括号年份模式时执行）：

   此步骤将 `$ARGUMENTS` 中的中文格式引用预处理为 LaTeX 可识别格式，确保后续 pipeline 的引用保护机制能正确工作。**此步骤为通用逻辑，bib 文件路径从步骤 0.2 动态获取，不依赖特定文件名。**

   **核心规则**：只转换**英文姓氏（拉丁字母）**作者的引用为 `\citet{}`/`\citep{}`；**中文姓氏（汉字）**作者的引用统一替换为 `(ref)` 占位符。

   **跳过条件**：如果 `$ARGUMENTS` 中不包含「全角括号内含4位数字」的模式（即无 `（...YYYY...）`），跳过此步骤。

   **a. 解析 bib 文件构建查找表 `{BIB_LOOKUP}`**：
   - 读取 bib 文件（路径在步骤 0.2 已动态确定，可能是任意名称的 .bib 文件）
   - 对每个条目，从 `author = {...}` 字段提取第一作者姓氏（小写），从 `year = {...}` 字段提取年份
     - **必须从条目字段解析，不可从 key 名推断**（例：bib key 中的年份可能与 year 字段不一致）
     - 带连字符的姓名保留连字符（如 Martinez-Noya → `martinez-noya`）
     - 缺少 `year` 字段的条目不加入查找表
   - 构建查找表：`(姓氏_lower, 年份)` → `bib_key`

   **b. 识别作者姓氏类型并分流**：

   扫描 `$ARGUMENTS` 中所有含全角括号年份的引用，判断作者姓氏是否为拉丁字母：
   - **判定规则**：作者姓氏的第一个字符为 `[A-Za-z]` → 英文姓氏；为 `[\u4e00-\u9fff]` → 中文姓氏
   - 中文姓氏引用 → 直接替换为 `(ref)`，不做 bib 匹配

   **c. 转换英文姓氏引用**：

   **优先处理 Pattern B（括注式 → `\citep{}`）**，整个引用在全角括号内，先处理避免被 Pattern A 部分匹配：
   - 匹配全角括号内容 `（([^（）]+)）`，检查是否包含英文作者+年份
   - 单引用：`（English_Author info, YYYY）` → `\citep{key}`
   - 多引用（`;`/`；` 分隔）：逐个检查每个子引用的作者类型
     - 全部英文 → `\citep{key1, key2}`
     - 全部中文 → `(ref)`
     - 混合 → 英文部分转为 `\citep{key}`，中文部分转为 `(ref)`，按原顺序拼接
       - 示例：`（Wang, 2024；孙忠娟等，2025；Sirmon et al., 2011）` → `\citep{wang2024Does} (ref) \citep{sirmon2011Resource}`（英文引用各自独立转为 `\citep{}`，中文部分合并为单个 `(ref)`）

   **然后处理 Pattern A（行内式 → `\citet{}`）**，英文作者名在括号外、年份在全角括号内：
   - `Author（YYYY）` / `Author et al.（YYYY）` / `Author and Author（YYYY）` / `Author-Name et al.（YYYY）`

   **英文引用的 bib 匹配逻辑**：
   1. 提取第一作者英文姓氏和年份
   2. 在 `{BIB_LOOKUP}` 查找 `(姓氏_lower, 年份)`
      - 匹配成功 → 使用 bib key
      - 匹配失败 → 生成临时 key `AuthorYear`（首字母大写，如 `Barney1991`）
      - 歧义（同姓同年多条目）→ 生成临时 key，标注 AMBIGUOUS

   **d. 生成转换结果并存储**：
   - 生成转换结果表内容 `{CITATION_MAP_CONTENT}`（markdown 格式），包含：
     ```markdown
     # Citation Map — {Section}
     ## Date: {current date}
     ## Mode: Draft
     ## Bib file: {bib 文件路径}

     | # | 原文 | 类型 | → 转换 | Bib 匹配 |
     |---|------|------|--------|---------|
     | 1 | Wang（2024） | citet | \citet{wang2024Does} | ✓ bib |
     | 2 | （孙忠娟等，2025） | — | (ref) | — 汉字作者 |
     | ... |

     ## Summary
     - 英文引用: {M} 个（{K} 匹配 bib，{J} 生成临时 key）
     - 中文引用: {C} 个 → (ref)
     - 临时 key 列表: {列表，如有}
     ```
   - 在对话中显示转换结果表（简化版），自动继续不阻塞
   - `{CITATION_MAP_CONTENT}` 暂存在内存中，在步骤 2 创建 checkpoint 文件时保存到 `{WORK_DIR}/00_citation_map.md`

   **e. 应用转换**：
   - 将转换应用到 `$ARGUMENTS` 的**工作副本** `{CONVERTED_ARGUMENTS}`
   - 后续所有步骤使用 `{CONVERTED_ARGUMENTS}` 作为用户输入内容
   - **唯一例外**：步骤 2 保存 `00_user_outline.md` 时使用**原始** `$ARGUMENTS`

4. **构建 Manuscript Section Tree**：
   - 读取主文件全文，用正则提取所有 `\section{}`、`\subsection{}`、`\subsubsection{}` 命令（忽略 `\section*{}` 等非编号 section）
   - 正则模式：`\\(section|subsection|subsubsection)\{([^}]+)\}`
   - 为每个命令记录：级别（section=1, subsection=2, subsubsection=3）、标题文本、行号
   - 根据级别和出现顺序构建父子关系树，记为 `{SECTION_TREE}`
   - 为每个节点记录：parent、children、siblings（同级邻居）、preceding（前一个同级）、following（后一个同级）

5. **Section 检测与输入分类**：

   > 注意：以下所有扫描和拆分操作均基于 `{CONVERTED_ARGUMENTS}`（如步骤 0.3 已执行）或原始 `$ARGUMENTS`（如步骤 0.3 被跳过）。

   - 扫描 `{CONVERTED_ARGUMENTS}`（如存在，否则 `$ARGUMENTS`）主体内容中的所有 `\section{}`、`\subsection{}`、`\subsubsection{}` 命令
   - 记录出现的 section 级别集合 `{LEVELS_FOUND}`

   **情况 A — 无 section 命令**：
   - 如果用户指定了 `section=XXX`，使用该名称
   - 否则，将内容与 `{SECTION_TREE}` 对比，推断所属 section
   - 如果无法推断，询问用户
   - 在 `{SECTION_TREE}` 中查找该 section 节点，确定其祖先路径 `{ANCESTOR_PATH}`（从根到该节点的所有祖先标题列表，不含自身）
   - 如果该 section 名称不在 `{SECTION_TREE}` 中（可能是新 section），将 `{ANCESTOR_PATH}` 设为空列表，并在 Structural Context 的 Role in paper 中标注 "New section — not yet in manuscript structure"
   - 设置 `{INPUT_FORM}` = "single"

   **情况 B — 只有一个级别的 section 命令**：
   统计该级别的 section 命令数量。

   **B1 — 只有 1 个命令**（Form 1 — 单节）：
   - 提取该 section 的标题
   - 在 `{SECTION_TREE}` 中查找匹配节点（先精确匹配，失败则忽略大小写和冠词做模糊匹配）
   - 如果找不到匹配，警告用户并询问确认
   - 确定该节点的祖先路径 `{ANCESTOR_PATH}`（从根到该节点的所有祖先标题列表，不含自身）
   - 设置 `{INPUT_FORM}` = "single"

   **B2 — 有多个命令**（Form 2 — 同级多节）：
   - 提取所有 section 命令的标题列表
   - 在 `{SECTION_TREE}` 中查找每个节点
   - **推断共同 parent**：
     - 如果所有节点在 Section Tree 中共享同一个 parent → 使用该 parent
     - 如果部分节点不在 Section Tree 中（新 section）→ 使用已匹配节点的 parent，假设未匹配节点为同级兄弟
     - 如果所有节点都不在 Section Tree 中 → 询问用户指定 parent section
     - 如果匹配到的节点分属不同 parent → 警告用户"选中的 section 分属不同父节点"，询问用户确认或缩小选择范围
   - 确定推断 parent 节点的祖先路径 `{ANCESTOR_PATH}`
   - 设置 `{INPUT_FORM}` = "multi"
   - **拆分内容**：按 section 命令位置拆分（逻辑同情况 C）
     - 每个片段 = section 标题 + 该 section 直到下一个同级 section 之前的所有内容
     - **Inter-section text**（选中文本开头到第一个 section 命令之间的文本）：如果去除空白后超过 50 字符，作为独立片段处理，命名为 `{InferredParent}_preamble`
   - 将拆分结果记为 `{SPLIT_SEGMENTS}` = [{title, content, base_dir}, ...]，其中每个片段的 `base_dir` = `{PARENT_HIERARCHY}`

   **情况 C — 两个级别的 section 命令**（Form 2 — 多节拆分）：
   - 识别较高级别为 parent，较低级别为 children
   - 在 `{SECTION_TREE}` 中查找 parent 节点
   - 提取所有 child section 的标题列表 `{CHILD_SECTIONS}`（按出现顺序）
   - 确定 parent 节点的祖先路径 `{ANCESTOR_PATH}`
   - 设置 `{INPUT_FORM}` = "multi"
   - **拆分内容**：按 child section 命令位置将主体内容拆分为多个片段
     - 每个片段 = child section 标题 + 该 child section 直到下一个同级 section 之前的所有内容
     - **Inter-section text**（parent 标题到第一个 child 标题之间的文本）：
       如果去除空白后超过 50 字符，作为独立片段处理，命名为 `{Parent}_preamble`，在第一个 child section 之前处理；
       如果不超过 50 字符，忽略
   - 将拆分结果记为 `{SPLIT_SEGMENTS}` = [{title, content, base_dir}, ...]，其中每个片段的 `base_dir` = `{PARENT_HIERARCHY}`

   **情况 D — 三个或更多级别的 section 命令**：
   - 以最高级别为 top parent，按情况 C 的方式确定 `{ANCESTOR_PATH}`、`{PARENT_HIERARCHY}`
   - 以**最低级别**为拆分单元（split unit），中间级别提供层级上下文
   - 按最低级别 section 命令位置拆分内容（拆分逻辑同情况 C）
   - Inter-section text 规则同情况 C（> 50 字符则作为独立片段）。每个中间级别标题到其第一个子 section 之间的文本也适用此规则
   - 每个片段记录其所属中间级别 parent 的标题（用于计算 `base_dir`）
   - `{SPLIT_SEGMENTS}` 中每个片段的 `base_dir` = `{PARENT_HIERARCHY}/{normalize(中间级别 parent 标题)}`
   - 向用户提示："检测到 {N} 个层级的 section 命令，将按最低级别（{level_name}）拆分为 {M} 个片段分别处理。"
   - 设置 `{INPUT_FORM}` = "multi"

6. **构建层级路径**：
   - **Section 名称标准化规则** `normalize(title)`：
     - 替换空格为下划线
     - 保持 Capitalized_Words 风格（每个单词首字母大写，除了介词/冠词等短词保持原样）
     - **截断规则**：标准化后超过 40 字符，在最后一个完整单词（下划线）边界处截断
     - 示例："Research methods" → `Research_methods`（15字符，不截断）
     - 示例："Theoretical foundation and hypotheses development" → `Theoretical_foundation_and_hypotheses`（37字符，截断去掉 `_development`）
     - 示例："The impact of digital investment on digital competitive advantage" → `The_impact_of_digital_investment_on`（35字符，截断）

   - **Form 1 (single)**：
     - `{SECTION_NAME}` = normalize(当前 section 标题)
     - `{HIERARCHY_PREFIX}` = 将 `{ANCESTOR_PATH}` 中每个祖先标题 normalize 后用 "/" 连接
       - 顶级 section（无祖先）: `{HIERARCHY_PREFIX}` 为空
       - 二级 section: `{HIERARCHY_PREFIX}` = normalize(parent_title)
       - 三级 section: `{HIERARCHY_PREFIX}` = normalize(grandparent_title)/normalize(parent_title)

   - **Form 2 (multi)**：
     - `{HIERARCHY_PREFIX}` = 按 Form 1 相同规则，用 parent 节点的 `{ANCESTOR_PATH}` 构建
     - `{PARENT_HIERARCHY}` = `{HIERARCHY_PREFIX}` + "/" + normalize(parent 自身标题)
       - 如果 parent 是顶级 section（`{HIERARCHY_PREFIX}` 为空）: `{PARENT_HIERARCHY}` = normalize(parent 标题)
     - 每个 child section 的工作目录将在 `drafts/{PARENT_HIERARCHY}/` 下创建

7. **创建工作目录**：

   - **Form 1 (single)**：
     - 确定完整父目录路径：
       如果 `{HIERARCHY_PREFIX}` 为空: 父目录 = `drafts/`
       否则: 父目录 = `drafts/{HIERARCHY_PREFIX}/`
     - 如果父目录不存在，递归创建
     - 在父目录下查找匹配 `{SECTION_NAME}_*` 的文件夹，提取最大序号
     - 创建 `{SECTION_NAME}_{序号+1:03d}`（如果无已有文件夹则为 `_001`）
     - `{WORK_DIR}` = `{父目录}/{SECTION_NAME}_{序号}/`

   - **Form 2 (multi)**：
     - 确定基础目录 `{MULTI_BASE_DIR}` = `drafts/{PARENT_HIERARCHY}/`
     - 如果不存在，递归创建
     - 不在此步创建子工作目录——在步骤 1.5 的调度循环中为每个 child section 分别创建

8. **生成 Structural Context**：
   - 根据 `{SECTION_TREE}` 和当前 section 节点，生成结构上下文描述（传递给 agents）：
   ```
   ### Structural Context
   - Paper structure position: {完整路径，如 "Section 3 (Research methods) > Subsection 3.2 (Measures)"}
   - Parent section: {parent title，如无则写 "Top level (no parent)"}
   - Sibling sections: {同级 section 标题列表}
   - Preceding section: {前一个同级 section 标题，如无则写 "None (first in group)"}
   - Following section: {后一个同级 section 标题，如无则写 "None (last in group)"}
   - Role in paper: {基于 section 位置推断的角色描述，如 "变量测度与操作化定义" "理论假设推导" 等}
   ```
   - 对于 Form 1，此处直接生成并记为 `{STRUCTURAL_CONTEXT}`
   - 对于 Form 2，在调度循环中为每个 child section 分别生成

## 步骤 1：生成 Writing Brief

1. **检查现有 Brief 是否可复用**：
   - 读取 `drafts/writing_brief.md`
   - 如果文件不存在或为空 → 执行下方第 3 步（调用 journal-scout）
   - 从 `## Metadata` 提取 `Generated` 时间戳和 `Manuscript word count`
   - 如果 Metadata 缺失（旧格式 Brief） → 执行下方第 3 步
   - **时间检查**：计算当前时间与 `Generated` 的差值。如果 > 24 小时 → 执行下方第 3 步，提示 "Writing Brief 已超过 24 小时，自动重新生成..."
   - **字数检查**：读取当前 manuscript 主文件，估算正文字数。计算 `|当前字数 - Brief记录字数| / Brief记录字数`。如果 > 20% → 执行下方第 3 步，提示 "Manuscript 字数变化超过 20%（Brief 记录 {X}，当前 {Y}），自动重新生成..."
   - 如果两项检查均通过 → **复用现有 Brief**，提示 "使用现有 Writing Brief（期刊：{名称}，生成于 {时间}）"，跳过下方第 2-5 步

2. **主 agent 执行 Web 搜索**（此步骤由主 agent 执行，不是调用 agent）：
   - 提取期刊名称：从 manuscript.tex 的 `\journal{}` 获取
   - 使用 `mcp__web-search-prime__webSearchPrime` 搜索：
     ```
     search_query: "{期刊名} author guidelines"
     location: "us"
     content_size: "medium"
     ```
   - 如果成功，记录搜索结果和来源："Web (mcp__web-search-prime__webSearchPrime)"
   - 如果失败，尝试 `mcp__MiniMax__web_search`
   - 如果成功，记录来源为 "Web (mcp__MiniMax__web_search)"
   - 如果都失败，记录来源为 "Knowledge base only"

3. **调用 journal-scout agent**：
   使用 Task 工具调用 journal-scout agent（`subagent_type: "journal-scout"`），**传递搜索结果**：

   **传递给 journal-scout 的 prompt**：
   ```
   Analyze the manuscript in this project and generate a Writing Brief.

   ## Web Search Results (from main agent):
   {搜索结果内容或"无结果，使用训练知识"}

   ## Journal Info Source: {Web (mcp__web-search-prime__webSearchPrime) | Web (mcp__MiniMax__web_search) | Knowledge base only}

   Output the complete Writing Brief in the conversation.
   ```

4. **保存 Writing Brief**：
   将 journal-scout 输出的 Writing Brief（从 `---BEGIN WRITING BRIEF---` 到 `---END WRITING BRIEF---`）保存到 `drafts/writing_brief.md`（如果 drafts/ 目录不存在，先创建）

5. **向用户展示关键信息**：
   显示 Brief 中的期刊名称、研究情境、信息来源（Web / Knowledge base only）。

## 步骤 1.5：Form 2 调度控制（仅在 `{INPUT_FORM}` = "multi" 时执行）

如果 `{INPUT_FORM}` = "single"，**跳过此步骤**，直接执行步骤 2-8。

如果 `{INPUT_FORM}` = "multi"：

### 1.5a. 向用户确认拆分结果

使用 AskUserQuestion 显示拆分结果并等待确认：

```
检测到多节输入（Form 2），将拆分为以下子 section 依次处理：

Parent: {parent title}
Hierarchy: drafts/{PARENT_HIERARCHY}/
Children (按 manuscript 顺序):
1. {child_1 title} → {child_1_normalized}_{序号}/ ({content preview, first 50 chars}...) [字数: {budget or "未指定"}]
2. {child_2 title} → {child_2_normalized}_{序号}/ ({content preview, first 50 chars}...) [字数: {budget or "未指定"}]
3. ...

Writing Brief: 已生成/复用，所有子 section 共享
预计 agent 调用: 约 {6 × N} 次（N={子section数}）

是否开始处理？
```

用户确认后进入循环；如果用户调整拆分方案，按调整后的 `{SPLIT_SEGMENTS}` 执行。

### 1.5b. 依次处理每个子 section

```
FOR i, segment IN enumerate({SPLIT_SEGMENTS}):

  a. 设置当前 section 变量：
     - {CURRENT_SECTION_NAME} = normalize(segment.title)
     - {CURRENT_SECTION_TITLE} = segment.title
     - {CURRENT_CONTENT} = segment.content
     - {CURRENT_WORD_TARGET} = 解析字数目标（优先级：按节指定 > 全局 > 未指定）：
       先查找 {WORD_BUDGETS}[normalize(segment.title)]，如果有则使用；
       否则查找 {WORD_BUDGETS}["_global"]，如果有则使用；
       否则为 null（未指定字数）

  b. 创建工作目录：
     - {CURRENT_BASE_DIR} = drafts/{segment.base_dir}/
     - 如果 {CURRENT_BASE_DIR} 不存在，递归创建
     - 在 {CURRENT_BASE_DIR} 下检查 {CURRENT_SECTION_NAME}_* 文件夹
     - 确定序号并创建
     - {WORK_DIR} = {CURRENT_BASE_DIR}/{CURRENT_SECTION_NAME}_{序号:03d}/

  c. 生成该子 section 的 Structural Context（使用步骤 0.8 的逻辑）

  d. 显示进度提示：
     "▶ 开始处理子 section [{i+1}/{total}]: {segment.title}"

  e. 执行步骤 2-7（完整的单 section 流水线）：
     - 使用 {CURRENT_CONTENT} 作为输入
     - 使用 {CURRENT_SECTION_TITLE} 作为 section 名称
     - 使用当前的 {WORK_DIR}
     - 使用当前子 section 的 {STRUCTURAL_CONTEXT}
     - 字数目标为 {CURRENT_WORD_TARGET}（在 agent prompt 的字数约束中使用此值替代全局 {words}）
     - Writing Brief 不重新生成（复用步骤 1 的结果）

  f. 显示子 section 完成状态：
     "✓ 子 section [{i+1}/{total}] 完成: {WORK_DIR}"

END FOR
```

处理完所有子 section 后，跳转到**步骤 8（完成提示）**的 Form 2 汇总版本。

## 步骤 2：提取 Anchor Points

> 此步骤及后续步骤 3-7 构成**单 section 流水线**，在 Form 1 中直接执行一次，在 Form 2 中对每个子 section 重复执行。

从 `{CONVERTED_ARGUMENTS}`（如存在，否则 `$ARGUMENTS`）中提取**所有**核心要点锚点（Anchor Points）。**数量不设硬性限制**，完全由用户输入的信息密度决定——简洁大纲可能只有 3 个，密集要点可能有 12 个以上。

**核心原则：宁多不漏，确保逻辑完备。**

**提取规则**：
1. **原子性**：每个锚点只包含一个不可再分的逻辑单元。如果一句话包含两个独立论点（如 "X 导致 Y，且 Z 调节该关系"），必须拆成两个锚点
2. **完备性**：提取完成后自检——"仅凭这些锚点，能否重建用户大纲的**全部**核心逻辑？" 如果不能，补充遗漏的锚点
3. **忠实性**：锚点反映用户的**原始意图**，不添加你的推断或延伸
4. **不合并**：两个相关但独立的论点不得合并为一个锚点，即使它们属于同一主题

**需要捕捉的逻辑单元类型**：
- 核心论断（X leads to Y）
- 因果机制（through mechanism Z）
- 理论框架的选用与应用方式
- 变量间关系（中介、调节、边界条件）
- 关键定义或构念界定
- 数据与方法细节（样本来源、时间范围、样本量、筛选标准、数据库名称、分析方法、软件工具、阈值设定等）
- 已有文献引用（用户大纲中出现的 `\citep{}`、`\citet{}` 等引用命令及其位置，必须原样保留在最终输出中）
- 论证的逻辑顺序（如果顺序本身承载意义）

**格式**：编号列表，每个锚点一句话概括。

**示例**：
```
Anchor Points:
1. Social use (rather than purely instrumental use) of digital communication tools is the key driver of meta-knowledge development
2. Meta-knowledge mediates the relationship between DCT usage and improvisational capability
3. Distributed Cognition Theory explains the tool → cognition → capability transmission mechanism
4. The relationship is moderated by team size — larger teams benefit more from social use
5. Instrumental use alone does not significantly predict meta-knowledge improvement
```

**输出与保存**：
1. 在对话中显示提取的 anchor points
2. 将用户**原始** `$ARGUMENTS`（未经引用转换的版本）保存到 `{WORK_DIR}/00_user_outline.md`
3. 将 anchor points 保存到 `{WORK_DIR}/00_anchor_points.md`，格式：
   ```markdown
   # Anchor Points — {Section}
   ## Mode: Draft
   ## Date: {current date}

   1. {anchor point 1}
   2. {anchor point 2}
   3. ...
   ```
4. 如果 `{CITATION_MAP_CONTENT}` 存在（即步骤 0.3 执行了引用转换），将其保存到 `{WORK_DIR}/00_citation_map.md`
5. 自动继续步骤 3，无需用户确认。

## 步骤 3：调用 sci-writer 撰写初稿

使用 Task 工具调用 sci-writer agent（`subagent_type: "sci-writer"`）。

**传递给 sci-writer 的 prompt 必须包含**：

```
## 任务：撰写初稿

### 写作环境
请先读取 `drafts/writing_brief.md` 获取期刊要求、领域情境和项目文件路径。

### 上下文
- Section: {section名称}
- 工作模式：Draft（从大纲/要点撰写）

### Structural Context
{STRUCTURAL_CONTEXT}

此 section 的写作应当与其在论文中的位置角色一致。确保内容与前后 section 的衔接自然。

### Anchor Points（不可偏离）
请读取 `{WORK_DIR}/00_anchor_points.md` 获取完整 anchor points。

### 用户提供的大纲/要点
请读取 `{WORK_DIR}/00_user_outline.md` 获取用户原始大纲。

### 编排约束（必须遵守）
1. **字数控制**：{如果用户指定了字数} 目标字数 {words} 字（允许 ±10%，即 {words*0.9}-{words*1.1} 字）。当内容完整性与字数约束冲突时，优先满足字数要求。
   {如果用户未指定字数} 用户未指定字数，按内容需要自行把控，但需在输出开头标注实际字数。
2. **加粗格式**：默认不添加 \textbf{} 加粗。让用户自己决定强调重点。
3. **引用处理**：禁止添加新的 \citep{}/\citet{} 等引用命令。输入文本中已有的 \citep{}/\citet{} 引用命令原样保留。需要新引用的地方标记 (ref)。

### 输出要求
按照你的 Output Protocol 输出。在输出末尾标注实际字数，并包含 Anchor Point Verification 表格。
```

**Checkpoint**：将 sci-writer 输出保存到 `{WORK_DIR}/01_draft_v1.md`。

## 步骤 4：第 1 轮审稿-修改循环

### 4a. 调用 strict-reviewer 审稿

使用 Task 工具调用 strict-reviewer agent（`subagent_type: "strict-reviewer"`）。

**传递给 strict-reviewer 的 prompt**：

```
## 任务：审稿（第 1 轮）

### 审稿环境
请先读取 `drafts/writing_brief.md` 获取期刊标准和领域审查要点。

### 上下文
- Section: {section名称}
- 工作模式：Draft（从大纲/要点撰写）
- 这是初稿的第 1 轮审稿

### Structural Context
{STRUCTURAL_CONTEXT}

### Anchor Points（审稿时参照）
请读取 `{WORK_DIR}/00_anchor_points.md` 获取完整 anchor points。

### 待审文本
请读取 `{WORK_DIR}/01_draft_v1.md` 获取待审文本。

### 编排约束
1. **字数约束**：{如果有字数要求} 用户指定目标字数 {words} 字（±10%）。不得要求增加内容导致超出此范围。如发现超标，应建议精简而非扩充。
   {如果无字数要求} 用户未指定字数，按合理长度审查。
2. **Drift Check**：重点检查文本是否偏离 anchor points。请在审稿报告中包含 Anchor Point Verification 表格。

### 输出要求
按照你的 Review Output Format 输出。
```

**Checkpoint**：将 strict-reviewer 输出保存到 `{WORK_DIR}/02_review_r1.md`。

### 4b. 调用 sci-writer 根据审稿意见修改

使用 Task 工具调用 sci-writer agent（`subagent_type: "sci-writer"`）。

**传递给 sci-writer 的 prompt**：

```
## 任务：根据审稿意见修改（第 1 轮）

### 写作环境
请先读取 `drafts/writing_brief.md` 获取期刊要求、领域情境和项目文件路径。

### 上下文
- Section: {section名称}
- 工作模式：Draft

### Structural Context
{STRUCTURAL_CONTEXT}

### Anchor Points（不可偏离）
请读取 `{WORK_DIR}/00_anchor_points.md` 获取完整 anchor points。

### 你的当前版本
请读取 `{WORK_DIR}/01_draft_v1.md` 获取你之前的初稿。

### 审稿意见
请读取 `{WORK_DIR}/02_review_r1.md` 获取审稿报告。

### 编排约束
1. **字数控制**：{同步骤3的字数约束}
2. **加粗格式**：默认不添加 \textbf{} 加粗。
3. **引用处理**：禁止添加新的引用命令，需要引用的地方用 (ref) 标记。已有的 \citep{}/\citet{} 引用命令原样保留。
4. **Anchor Points 优先**：如审稿意见与 anchor point 冲突，保留 anchor point，在修改说明中解释原因。
5. **如审稿建议会大幅超出字数限制，拒绝该建议并说明"用户指定字数限制"。**

### 输出要求
按照你的 Output Protocol 输出修改后的完整文本。标注：(a) 针对每条审稿意见的处理方式，(b) 实际字数。在输出末尾包含 Anchor Point Verification 表格。
```

**Checkpoint**：将 sci-writer 输出保存到 `{WORK_DIR}/03_revision_r1.md`。

## 步骤 5：第 2 轮审稿-修改循环

重复步骤 4 的结构，但标注为"第 2 轮"。

### 5a. strict-reviewer 第 2 轮审稿
- prompt 结构同 4a，但标注"第 2 轮"
- 包含 `### Structural Context` 块（同上）
- 待审文本改为：`请读取 {WORK_DIR}/03_revision_r1.md`
- **Checkpoint**：输出保存到 `{WORK_DIR}/04_review_r2.md`

### 5b. sci-writer 第 2 轮修改
- prompt 结构同 4b，但标注"第 2 轮"
- 包含 `### Structural Context` 块（同上）
- "### 你的当前版本" 改为：`请读取 {WORK_DIR}/03_revision_r1.md` 获取第 1 轮修改后的文本
- "### 审稿意见" 改为：`请读取 {WORK_DIR}/04_review_r2.md` 获取第 2 轮审稿报告
- **Checkpoint**：输出保存到 `{WORK_DIR}/05_revision_r2.md`

## 步骤 6：调用 language-polisher 润色

使用 Task 工具调用 language-polisher agent（`subagent_type: "language-polisher"`）。

**传递给 language-polisher 的 prompt**：

```
## 任务：语言润色

### 润色环境
请先读取 `drafts/writing_brief.md` 获取期刊和领域信息。

### 上下文
- Section: {section名称}
- 这是经过 2 轮审稿修改后的最终文本

### Structural Context
{STRUCTURAL_CONTEXT}

### Anchor Points（润色时不得改变其含义、强度和范围）
请读取 `{WORK_DIR}/00_anchor_points.md` 获取 anchor points。润色时可以改善 anchor point 的语言表达，但不得改变其学术含义、论证强度或适用范围。

### 待润色文本
请读取 `{WORK_DIR}/05_revision_r2.md` 获取待润色文本。

### 约束
1. 不改变逻辑结构和论证链条
2. 不使用 \textbf{} 标记修改，输出干净的 LaTeX 文本
3. 所有 (ref) 标记保持不变
4. 所有已有的 \citep{}/\citet{} 引用保持不变
5. 所有修改记录在 Change Summary 中

### 输出要求
按照你的 Output Protocol 输出。
```

**Checkpoint**：将 language-polisher 输出保存到 `{WORK_DIR}/06_polished.md`。

## 步骤 7：生成输出文件

将整个流程的结果写入工作目录：

### 文件 1：`{WORK_DIR}/changelog.md`

```markdown
# {Section} — Draft Changelog

## Date: {current date}
## Mode: Draft (from outline)
## Work Directory: {WORK_DIR}
## Structural Context: {Paper structure position，如 "Section 3 > Subsection 3.2"}

## Anchor Points
{list all anchor points}

## Round 1 — Review
{strict-reviewer Round 1 review summary}

## Round 1 — Revision
{sci-writer Round 1 revision summary}

## Round 2 — Review
{strict-reviewer Round 2 review summary}

## Round 2 — Revision
{sci-writer Round 2 revision summary}

## Language Polish
{language-polisher Change Summary}

## Final Word Count: {final word count}
## Drift Check: {whether all anchor points are intact}
```

### 文件 2：`{WORK_DIR}/final.md`

**LaTeX 提取规则**：从 `06_polished.md` 中提取 ` ```latex ``` ` code block 内的纯 LaTeX 内容（不含 Change Summary 和 Content Notes）。

````markdown
# {Section} — Final Draft

> Ready to copy into the manuscript

```latex
{final LaTeX text from language-polisher}
```

## Target location in manuscript: {section location，如 "Section 3 (Research methods) > Subsection 3.2 (Measures)，Lines 172-178"}
## Final word count: {final word count}
````

### 文件 3（便捷入口）：层级化路径

**路径规则**：`_latest_final.md` 放在与版本化工作目录同级的位置。

- Form 1: `drafts/{HIERARCHY_PREFIX}/{SECTION_NAME}_latest_final.md`
  - 如果 `{HIERARCHY_PREFIX}` 为空（顶级 section）: `drafts/{SECTION_NAME}_latest_final.md`
- Form 2: 每个子 section 各自的 `drafts/{segment.base_dir}/{CURRENT_SECTION_NAME}_latest_final.md`

复制 `{WORK_DIR}/final.md` 的内容到便捷入口文件。此文件始终指向该 section 最新一次运行的结果，方便快速访问。**注意**：如果此文件已存在，直接覆盖（这是设计行为，历史版本保存在带序号的工作目录中）。

## 步骤 8：完成提示

### Form 1（单节模式）

向用户显示：
1. 工作流完成状态
2. Structural Context 概要：该 section 在论文中的位置
3. 工作目录路径：`{WORK_DIR}/`
4. 便捷入口路径
5. 字数统计
6. Anchor points 完整性状态
7. Checkpoint 文件清单（列出工作目录中所有文件）
8. 如果 `00_citation_map.md` 存在且包含临时 key：显示提醒"注意：{N} 个引用使用了临时 key（未在 bib 文件中找到匹配），请手动检查并添加到 bib 文件。临时 key 列表：{列表}"
9. 提醒用户检查 `{WORK_DIR}/final.md`，确认后手动合并到主文件

### Form 2（多节模式）

向用户显示：
1. 工作流完成状态：所有 {N} 个子 section 已处理完毕
2. 基础目录：`{MULTI_BASE_DIR}`
3. 处理结果汇总表：

```
| # | 子 Section | 工作目录 | 便捷入口 | 字数 | Anchor 状态 |
|---|-----------|---------|---------|------|------------|
| 1 | {title}   | {path}  | {path}  | {n}  | {status}   |
| 2 | ...       | ...     | ...     | ...  | ...        |
```

4. 建议按 manuscript 顺序从上到下依次检查和合并
5. 如果任何子 section 的 `00_citation_map.md` 包含临时 key：显示提醒"注意：以下引用使用了临时 key（未在 bib 文件中找到匹配），请手动检查并添加到 bib 文件。临时 key 列表：{汇总列表}"
6. 提醒用户检查每个子 section 的 `final.md`，确认后手动合并到主文件
