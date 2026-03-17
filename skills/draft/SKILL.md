---
description: "从大纲/要点撰写论文段落（4-Agent Pipeline：journal-scout → sci-writer → strict-reviewer → language-polisher）"
---

# Draft Workflow — 从大纲/要点撰写

调用四个 agent 完成从期刊识别到润色的全流程。

**执行模式**：Form 1（单节）直接运行流水线；Form 2（多节）按 section 拆分依次运行。

**输入** `$ARGUMENTS`：大纲/要点文本，可选 `| section=XXX | words=500`。`words` 支持全局（`words=500`）、按节（`words=Measures:300,Model:500`）、自然语言（`Measures 300字`）。选中文本自动作为输入。

## 步骤 0：解析输入与前置检查

### 0.1 解析 `$ARGUMENTS`
- 提取主体内容、`section`、`words` 参数
- `words` 解析：纯数字→`{"_global": N}`，键值对/自然语言→`{"SectionName": N, ...}`，未指定→`{}`。键名匹配忽略大小写和下划线/空格差异
- 空或 < 20 字符 → 停止提示用户提供大纲
- 未指定 section → 从内容推断或询问用户

### 0.2 获取项目文件路径
- 从 CLAUDE.md 获取主文件和 bib 文件路径
- Fallback：Glob("*.tex") 查找含 `\documentclass` 的文件（排除 supplementary/appendix/*.cls）
- 读取主文件了解论文结构

### 0.3 引用格式预处理

**跳过条件**：`$ARGUMENTS` 不含全角括号年份模式（`（...YYYY...）`）则跳过。

**核心规则**：英文姓氏（拉丁字母首字符）→ `\citet{}`/`\citep{}`；中文姓氏（汉字首字符）→ `(ref)`。

**a. 解析 bib 构建 `{BIB_LOOKUP}`**：
- 读取 bib 文件，从每个条目的 `author`/`year` 字段（非 key 名）提取第一作者姓氏(小写)和年份
- 带连字符姓名保留连字符
- 构建查找表：`(姓氏_lower, 年份)` → `bib_key`

**b. 分流**：扫描全角括号年份引用，首字符 `[A-Za-z]` → 英文；`[\u4e00-\u9fff]` → 中文→直接替换 `(ref)`

**c. 转换英文引用**：

**先 Pattern B（括注式→`\citep{}`）**：匹配 `（([^（）]+)）` 中含英文作者+年份的内容
- 单引用→`\citep{key}`，多引用（`;`/`；`分隔）→全英文合并为 `\citep{k1, k2}`，全中文→`(ref)`，混合→各自处理按原序拼接

**后 Pattern A（行内式→`\citet{}`）**：`Author（YYYY）`/`Author et al.（YYYY）` 等

**Bib 匹配**：`(姓氏_lower, 年份)` 查 `{BIB_LOOKUP}`→匹配成功用 bib key，失败→临时 key `AuthorYear`，歧义→标注 AMBIGUOUS

**d. 生成 `{CITATION_MAP_CONTENT}`**：markdown 表格含原文、类型、转换结果、匹配状态、Summary 统计。对话中显示简化版，自动继续。暂存内存，步骤 2 保存到 `{WORK_DIR}/00_citation_map.md`

**e. 应用转换**：工作副本 `{CONVERTED_ARGUMENTS}` 用于后续步骤。**例外**：`00_user_outline.md` 保存原始 `$ARGUMENTS`

### 0.4 构建 Section Tree `{SECTION_TREE}`
- 正则 `\\(section|subsection|subsubsection)\{([^}]+)\}` 提取所有 section 命令（忽略 `*` 变体）
- 记录级别、标题、行号，构建父子关系树，记录 parent/children/siblings/preceding/following

### 0.5 Section 检测与输入分类

> 以下操作基于 `{CONVERTED_ARGUMENTS}`（如存在）或 `$ARGUMENTS`。

扫描所有 section 命令，记录 `{LEVELS_FOUND}`。

**情况 A — 无 section 命令**：用户指定 `section=XXX` 则使用，否则与 `{SECTION_TREE}` 对比推断或询问。查找祖先路径 `{ANCESTOR_PATH}`。新 section 则 `{ANCESTOR_PATH}` = 空，标注 "New section"。`{INPUT_FORM}` = "single"

**B1 — 单个命令**（Form 1）：提取标题，在 `{SECTION_TREE}` 查找（先精确后模糊），确定 `{ANCESTOR_PATH}`。`{INPUT_FORM}` = "single"

**B2/C/D — 多命令**（Form 2）：`{INPUT_FORM}` = "multi"

B2（同级多节）、C（两个级别）、D（三个+级别）的共同逻辑：
- **Parent 推断**：B2 从 `{SECTION_TREE}` 推断共同 parent（全部共享→用之；部分新→用已匹配的 parent；全新→询问；分属不同→警告）。C 取较高级别为 parent。D 取最高级别为 top parent
- **拆分单元**：B2/C 按各自 section 命令位置拆分。D 按最低级别拆分，中间级别提供上下文
- **拆分规则**：每片段 = section 标题 + 到下一同级 section 前的内容
- **Inter-section text**：开头/parent标题到第一个 child 之间的文本，> 50 字符→独立片段命名 `{Parent}_preamble`；≤ 50→忽略。D 中每个中间级别标题到其首个子 section 也适用此规则
- **结果**：`{SPLIT_SEGMENTS}` = [{title, content, base_dir}, ...]。B2/C 的 `base_dir` = `{PARENT_HIERARCHY}`；D 的 `base_dir` = `{PARENT_HIERARCHY}/{normalize(中间 parent)}`
- D 情况提示用户检测到 N 个层级

### 0.6 构建层级路径

**`normalize(title)`**：空格→下划线，Capitalized_Words 风格，> 40 字符在最后完整单词边界截断。示例："Research methods" → `Research_methods`

**Form 1**：`{SECTION_NAME}` = normalize(标题)。`{HIERARCHY_PREFIX}` = 祖先标题 normalize 后 "/" 连接（顶级为空，二级=parent，三级=grandparent/parent）

**Form 2**：`{HIERARCHY_PREFIX}` 同 Form 1 规则。`{PARENT_HIERARCHY}` = `{HIERARCHY_PREFIX}/{normalize(parent)}`（parent 为顶级时 = normalize(parent)）

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

`{INPUT_FORM}` = "single" → 跳过，直接执行步骤 2-8。

**1.5a 确认**：AskUserQuestion 显示 Parent/Hierarchy/Children 列表（含内容预览、字数预算）、预计 agent 调用次数（约 6×N），等待确认

**1.5b 循环处理**：
```
FOR i, segment IN enumerate({SPLIT_SEGMENTS}):
  a. 设置变量：{CURRENT_SECTION_NAME/TITLE/CONTENT}，解析 {CURRENT_WORD_TARGET}（按节>全局>null）
  b. 创建工作目录 {WORK_DIR} = {CURRENT_BASE_DIR}/{NAME}_{序号:03d}/
  c. 生成该子 section 的 Structural Context
  d. 显示 "▶ [{i+1}/{total}]: {title}"
  e. 执行步骤 2-7（完整单 section 流水线，复用 Writing Brief）
  f. 显示 "✓ [{i+1}/{total}] 完成: {WORK_DIR}"
END FOR
```
完成后跳转步骤 8 Form 2 汇总。

## 步骤 2：提取 Anchor Points

> 步骤 2-7 = 单 section 流水线（Form 1 执行一次，Form 2 每个子 section 重复）

从 `{CONVERTED_ARGUMENTS}`（或 `$ARGUMENTS`）提取所有核心锚点。数量由信息密度决定，**宁多不漏**。

**规则**：原子性（一锚点一逻辑单元）、完备性（自检能否重建全部核心逻辑）、忠实性（不添加推断）、不合并。
**捕捉类型**：核心论断、因果机制、理论框架、变量关系、关键定义、数据方法细节、已有引用（原样保留）、逻辑顺序。

**输出**：
1. 对话中显示
2. 保存原始 `$ARGUMENTS` → `{WORK_DIR}/00_user_outline.md`
3. 保存 anchor points → `{WORK_DIR}/00_anchor_points.md`（含 Section、Mode: Draft、Date）
4. 如有 `{CITATION_MAP_CONTENT}` → 保存到 `{WORK_DIR}/00_citation_map.md`
5. 自动继续步骤 3

## 步骤 3：调用 sci-writer 撰写初稿

调用 sci-writer（`subagent_type: "sci-writer"`），prompt 要素：
- 读取 `drafts/writing_brief.md`
- Section 名称、Mode: Draft
- `{STRUCTURAL_CONTEXT}`，确保与前后 section 衔接
- 读取 `{WORK_DIR}/00_anchor_points.md` 和 `{WORK_DIR}/00_user_outline.md`
- **约束**：字数 {words}±10%（未指定则自行把控并标注）；禁止 `\textbf{}`；禁止新引用，已有引用原样保留，需引用处标 `(ref)`
- 按 Output Protocol 输出，含实际字数和 Anchor Point Verification 表格

**Checkpoint**：`{WORK_DIR}/01_draft_v1.md`

## 步骤 4：第 1 轮审稿-修改

### 4a. strict-reviewer 审稿
调用 strict-reviewer（`subagent_type: "strict-reviewer"`），prompt 要素：
- 读取 `drafts/writing_brief.md`
- Section、Mode: Draft、第 1 轮
- `{STRUCTURAL_CONTEXT}`
- 读取 `{WORK_DIR}/00_anchor_points.md`
- 待审：`{WORK_DIR}/01_draft_v1.md`
- **约束**：字数限制（同步骤 3）；Drift Check 含 Anchor Point Verification 表格
- 按 Review Output Format 输出

**Checkpoint**：`{WORK_DIR}/02_review_r1.md`

### 4b. sci-writer 修改
调用 sci-writer，prompt 要素：
- 读取 `drafts/writing_brief.md`
- Section、Mode: Draft
- `{STRUCTURAL_CONTEXT}`
- 读取 `{WORK_DIR}/00_anchor_points.md`
- 当前版本：`{WORK_DIR}/01_draft_v1.md`
- 审稿意见：`{WORK_DIR}/02_review_r1.md`
- **约束**：字数同步骤 3；禁止 `\textbf{}`；禁止新引用用 `(ref)`；Anchor Points 优先（冲突时保留 anchor point 并说明）；超字数限制则拒绝建议
- 按 Output Protocol 输出，含处理方式说明、实际字数、Anchor Point Verification 表格

**Checkpoint**：`{WORK_DIR}/03_revision_r1.md`

## 步骤 5：第 2 轮审稿-修改

结构同步骤 4，标注"第 2 轮"：
- **5a reviewer**：待审→`{WORK_DIR}/03_revision_r1.md` → **Checkpoint** `{WORK_DIR}/04_review_r2.md`
- **5b writer**：当前版本→`03_revision_r1.md`，审稿→`04_review_r2.md` → **Checkpoint** `{WORK_DIR}/05_revision_r2.md`

## 步骤 6：调用 language-polisher 润色

调用 language-polisher（`subagent_type: "language-polisher"`），prompt 要素：
- 读取 `drafts/writing_brief.md`
- Section、经过 2 轮审稿修改
- `{STRUCTURAL_CONTEXT}`
- 读取 `{WORK_DIR}/00_anchor_points.md`（不得改变含义、强度和范围）
- 待润色：`{WORK_DIR}/05_revision_r2.md`
- **约束**：不改变逻辑结构；不用 `\textbf{}`；`(ref)` 和已有引用保持不变；修改记录在 Change Summary
- 按 Output Protocol 输出

**Checkpoint**：`{WORK_DIR}/06_polished.md`

## 步骤 7：生成输出文件

### 文件 1：`{WORK_DIR}/changelog.md`
含 Section、Date、Mode: Draft、Work Directory、Structural Context、Anchor Points、R1 Review/Revision、R2 Review/Revision、Language Polish 摘要、Final Word Count、Drift Check

### 文件 2：`{WORK_DIR}/final.md`
从 `06_polished.md` 提取 ```latex``` code block（不含 Change Summary），包裹为：标题 `{Section} — Final Draft`，`> Ready to copy`，LaTeX block，Target location，Final word count

### 文件 3：`_latest_final.md`（便捷入口）
- Form 1: `drafts/{HIERARCHY_PREFIX}/{SECTION_NAME}_latest_final.md`（顶级 section 省略 prefix）
- Form 2: `drafts/{segment.base_dir}/{CURRENT_SECTION_NAME}_latest_final.md`
- 复制 `final.md` 内容，已存在则覆盖

## 步骤 8：完成提示

### Form 1
显示：完成状态、Structural Context 概要、工作目录/便捷入口路径、字数统计、Anchor points 完整性、Checkpoint 文件清单、临时 key 提醒（如有 `00_citation_map.md` 含临时 key）、提醒手动合并

### Form 2
显示：全部 {N} 个子 section 完成、基础目录 `{MULTI_BASE_DIR}`、汇总表（子 Section / 工作目录 / 便捷入口 / 字数 / Anchor 状态）、按顺序检查合并建议、临时 key 汇总提醒（如有）、提醒手动合并
