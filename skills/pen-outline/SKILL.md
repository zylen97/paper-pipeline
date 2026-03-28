---
description: "交互式构建叙述型章节的要点（论点 + citations），为 /pen-draft 提供高质量输入"
---

# Outline Workflow — 交互式构建章节要点

为叙述型章节（Introduction, Literature Review, Discussion）逐子节构建要点（核心论点 + citation key），经用户确认后写入章节 md 文件。技术型章节不适用本技能。

**三个章节的流程差异**：
- **Introduction / Discussion**：子节骨架由必备元素固定（RQ数量确定 → 子节确定），跳过步骤 1-2，直接进入要点填充
- **Literature Review**：子节骨架（N个方向）不确定，需先交互确定方向（步骤 1）和写作蓝图（步骤 2），再填充要点

**输入** `$ARGUMENTS`：`section=XXX`（必须）。

## 步骤 0：前置准备

### 0.1 解析 `$ARGUMENTS`

- 提取 `section` 参数
- 无 `section` → AskUserQuestion 询问要为哪个 section 构建要点

### 0.2 获取项目文件路径

- 从 CLAUDE.md 获取主文件和 bib 文件路径
- Fallback：Glob("*.tex") 查找含 `\documentclass` 的文件（排除 supplementary/appendix/*.cls）
- 读取主文件了解论文结构

### 0.3 构建 Section Tree `{SECTION_TREE}`（Python 脚本）

**由 Python 脚本自动完成**，替代主 Agent 手动正则解析。

```bash
python3 ~/.claude/skills/shared/tex_section.py section-tree --tex {主文件路径}
```

输出 `_section_tree.json`。VERIFY 必须为 PASS。

### 0.4 Section 匹配与 Form 判定（Python 脚本 + 主 Agent 判定）

**匹配由 Python 脚本完成**：

```bash
python3 ~/.claude/skills/shared/tex_section.py match-section \
  --tree _section_tree.json --query "{section参数}"
```

输出 `_section_match.json`。主 Agent 从中读取：
- `has_children` = true → `{INPUT_FORM}` = "multi"，`{SPLIT_SEGMENTS}` = children 列表
- `has_children` = false → `{INPUT_FORM}` = "single"
- **匹配失败**（VERIFY: FAIL）→ AskUserQuestion 让用户从列出的 section 中选择

### 0.5 叙述型章节检查 + 章节类型判定

判断匹配到的 section 所属顶层 section 是否为叙述型：

```
叙述型: Introduction, Literature review, Discussion
```

判断规则：匹配 section 所属的顶层 section 是否在叙述型列表中。不在列表中 → 视为技术型。

- **非叙述型** → 显示警告并退出：
  ```
  ⚠️ "{section title}" 不属于叙述型章节。
  /outline 仅适用于叙述型章节（Introduction, Literature Review, Discussion）。
  技术型章节应通过 /method-end 从 X_dev.md（过程文件）凝练到 X.md（成稿）。
  ```
- **Conclusion** → 显示提示并退出：Conclusion 无对应 md 文件，不适用 /outline。

**设置章节类型 `{SECTION_TYPE}`**：

根据匹配到的顶层 section 名称设置：
- Introduction → `{SECTION_TYPE}` = `"intro"`
- Literature review → `{SECTION_TYPE}` = `"litrev"`
- Discussion → `{SECTION_TYPE}` = `"discussion"`

### 0.6 定位源文件

- **章节 md 文件**：找到匹配 section 的顶层父 section，扫描 `structure/` 子目录用关键词匹配目录名：

```
section 关键词        → 目录
introduction         → structure/1_introduction/introduction.md
literature           → structure/2_literature/literature.md
discussion           → Glob("structure/*discussion*/discussion.md") 动态匹配
```

记录 `{CHAPTER_MD_PATH}`

- **citation pool 文件**（Python 脚本）：
```bash
python3 ~/.claude/skills/shared/tex_section.py citation-paths --chapter-md {CHAPTER_MD_PATH}
```
从 `_citation_paths.json` 读取 `citation_pool_paths` → `{CITATION_POOL_PATHS}`。如无引用池区块 → 空列表，不报错
- **全局上下文**：固定读取 `structure/0_global/idea.md` → `{IDEA_PATH}`
- **其他章节 md 扫描**（交叉参考）：扫描 `structure/` 下所有章节 md 文件（排除当前章节），检查有实质内容的 → `{OTHER_MD_PATHS}` 列表。读取时仅提取标题和要点摘要
- **LR 额外源文件**（仅 `{SECTION_TYPE}` == `"litrev"` 时）：
  - Glob `structure/2_literature/direction*report*.md` → `{DIRECTION_REPORT_PATHS}`
  - Glob `structure/2_literature/*search_plan*.md` → `{SEARCH_PLAN_PATH}`
  - Glob `structure/2_literature/master_report.md` → `{MASTER_REPORT_PATH}`
  - 任一 Glob 无匹配结果 → 对应变量设为空，不报错

**路由判定**：

```
IF {SECTION_TYPE} == "litrev" → 执行步骤 1-2，然后步骤 3
ELSE → 跳过步骤 1-2，直接进入步骤 3
```

## 步骤 1：LR 方向确定（仅 litrev）

> Introduction 和 Discussion 跳过此步骤。

### 1.1 读取 LR 专用素材

读取以下文件（摘要级别，避免上下文过长）：
1. `{DIRECTION_REPORT_PATHS}` 中所有方向报告 → `{DIRECTION_REPORTS_CONTEXT}`（每篇提取标题、关键发现、筛选后文献列表）
2. `{SEARCH_PLAN_PATH}` → `{SEARCH_PLAN_CONTEXT}`（了解方向设计逻辑）
3. `{MASTER_REPORT_PATH}` → `{MASTER_REPORT_CONTEXT}`（跨方向总结）
4. `{IDEA_PATH}` → `{IDEA_CONTEXT}`（Gap/RQ 定义）
5. `{CITATION_POOL_PATHS}` 中所有文件 → `{CITATION_POOL_CONTENT}`（可用文献和标签分布）
6. `{OTHER_MD_PATHS}` 中已完成的 Introduction md（如有）→ 提取 Gap 段落的覆盖领域

显示已读取的文件列表（空变量显示"（未找到）"）：
```
📂 LR 方向确定——上下文已加载：
- 纲领: structure/0_global/idea.md
- 方向报告: {逐行列出 direction report 文件名，或"（未找到）"}
- 检索方案: {search_plan 文件名，或"（未找到）"}
- 总报告: {master_report 文件名，或"（未找到）"}
- 引用池: {逐行列出 citation pool 文件名}
- 交叉参考: {有内容的其他章节 md 列表}
```

> 如无方向报告/检索方案/总报告，方向提议将主要基于 idea.md 和引用池。

### 1.2 自动提议方向

基于所有素材，提议 N 个 LR 方向（subsection）。

**方向生成规则**（用户写作风格）：

1. **第一个方向 = 研究主题本身**（最大主题/"因变量"）。识别方法：idea.md 标题中的核心研究对象，通常也是 RQ1 讨论的对象
2. **后续方向 = 围绕主题的子议题**，按**文献发展逻辑**而非机械 RQ 映射来组织。每个方向应能对应一个或多个 direction report 的内容。子议题的组织原则：
   - 从宏观到微观（如：网络演化 → 合作驱动因素 → 合作后果）
   - 或从共识到争议（如：已有共识 → 本文挑战的假设）
3. **可选末尾方向 = 理论视角**（仅当论文有明确的、独立于各方向的理论框架时才单设。如果理论线索已融入各方向讨论，则不需要单独子节）
4. **每个方向标注对应的 Gap 编号**（G1/G2/G3...），确保所有 Gap 都被覆盖
5. **方向数量**：通常 3-5 个，取决于 Gap 数量和文献覆盖面

**输出格式**：

```
📚 Literature Review 方向提议

基于 idea.md（{N} 个 Gap/RQ）、{M} 个检索方向报告和 Introduction 的 Gap 段落，提议以下 LR 结构：

| # | 方向标题（英文） | 核心内容 | 对应 Gap | 主要依据 |
|:-:|:---------------|:--------|:---------|:--------|
| 1 | {title} | {1句话概括} | G{x} | {来自哪些 direction reports} |
| 2 | {title} | {1句话概括} | G{y} | {来自哪些 direction reports} |
| ... | ... | ... | ... | ... |
| + | 定位表 | 本文 vs 最相关文献的多维对比 | 全局 | — |

**方向设计理由**：
- 方向1为什么放第一个：{理由}
- 方向2与方向1的递进关系：{理由}
- ...

**Gap 覆盖检查**：G1 → 方向{N}, G2 → 方向{N}, G3 → 方向{N}（全覆盖 ✓/✗）

你觉得这个方向划分合适吗？可以：
(1) 确认这个方案
(2) 调整方向数量/顺序/内容
(3) 讨论某个方向的设置理由
```

AskUserQuestion 等待用户确认。

**循环**：用户不满意 → 修改方向 → 再次展示 → 直到用户确认。确认后记录 `{LR_DIRECTIONS}` = 用户确认的方向列表（含标题、核心内容、对应 Gap）。

## 步骤 2：LR 写作蓝图构建（仅 litrev）

> Introduction 和 Discussion 跳过此步骤。

### 2.1 为每个方向构建写作蓝图

LR 方向的内部结构分为两部分，比重固定：

| 部分 | 比重 | 说明 |
|:-----|:----:|:-----|
| 综述主体 | ~85% | 按子主题展开，是每个方向的核心内容 |
| 指出不足 + 连接Gap | ~15% | 末段，约50词指出不足 + 一句话连接Gap |

**引用风格**（综述主体中交替使用）：
- **形式A（主题驱动）**: 以研究领域/主题为主语，文献做括号引用 `\citep{}`——用于概括性综述、覆盖多篇文献
- **形式B（作者驱动）**: 以作者为主语 `\citet{}`——用于 highlight 关键文献的具体发现

**落脚规则**：
- 如果该方向综述的是**跨行业的一般文献**，综述主体的**末尾子主题必须回溯到本文的研究情境**（从一般→本文研究的具体行业/领域），然后再接"指出不足"
- 如果该方向**本身就聚焦于本文的研究情境**（如直接综述建筑业文献），则不需要额外落脚
- **落脚比重**：落脚子主题不能只是一句话带过，应包含**至少3-4个要点**，充分综述本文研究情境中的已有证据。落脚的作用是为"指出不足"建立扎实的铺垫——只有先展示"这个领域已经做了什么"，才能有说服力地指出"还没做什么"

对每个已确认的方向，构建写作蓝图——列出子主题、为每个子主题从 citation pool 中分配具体 citation keys 并标注引用形式。bib 文件验证所有 citation key 存在性。

**输出格式**：

```
📐 各方向写作蓝图

### 方向1: {title} → G{x}
**比重**: 综述主体 ~85% | 指出不足+连接Gap ~15%

**综述主体展开**:
- 子主题A: {描述}（形式A）
  → \citep{key1, key2, key3}
- 子主题B: {描述}（形式B，逐篇 highlight）
  → \citet{key4}: {该文献的具体发现/贡献}
  → \citet{key5}: {该文献的具体发现/贡献}
- 子主题C: {描述}（形式A）
  → \citep{key6, key7}
- [落脚] 子主题D: 回溯到本文研究情境（形式A/B）
  → \citep{key8} 或 \citet{key9}: {...}

**指出不足**（~50词）: {基于前面综述自然引出的不足}
**连接Gap**: → G{x}

### 方向2: {title} → G{y}
...

确认后将记录到 literature.md 的必备元素中。
```

AskUserQuestion 等待用户确认。用户可以：
- 调整子主题的顺序、增删子主题
- 更换某个子主题的 citation 分配
- 修改引用形式（形式A↔形式B）
- 调整"指出不足"的措辞

**循环**：用户不满意 → 修改写作蓝图 → 再次展示 → 直到用户确认。

### 2.2 记录写入内容

记录需要更新到 `{CHAPTER_MD_PATH}`（literature.md）的内容（实际写入延迟到步骤 7 统一执行）：

1. `## 必备元素` 更新内容：方向列表 + 写作蓝图定义 + 定位表说明
2. `## 大纲` 中需要创建的 `###` heading 列表

### 2.3 生成子节列表

将 `{LR_DIRECTIONS}` + "定位表" 转换为 `{SPLIT_SEGMENTS}` 格式，设 `{INPUT_FORM}` = `"multi"`。

**关键**：对 LR，`{SPLIT_SEGMENTS}` 来自步骤 1 的用户确认结果，**而非** manuscript.tex 的 section tree 解析（因为 tex 中 LR 可能还没有 subsection）。步骤 0.4 中对 LR 的 Form 判定结果在此被覆盖。

## 步骤 3：读取并组装上下文

**动作**：

1. 读取 `{IDEA_PATH}` → `{IDEA_CONTEXT}`（idea.md 全文）
2. 读取 `{CHAPTER_MD_PATH}` → `{CHAPTER_MD_CONTENT}`（当前章节 md 全文）
3. 读取 `{CITATION_POOL_PATHS}` 中所有文件 → `{CITATION_POOL_CONTENT}`
4. 读取 `{OTHER_MD_PATHS}` 中的文件（仅标题和要点摘要）→ `{CROSS_REF_CONTEXT}`
5. 读取 bib 文件用于验证 citation key 存在性

**LR 额外读取**（仅 `{SECTION_TYPE}` == `"litrev"` 时）：

步骤 1.1 已读取方向报告等素材用于方向确定。此处复用已加载的上下文变量（`{DIRECTION_REPORTS_CONTEXT}` 等），不重复读取。

显示已读取的文件列表：
```
📂 上下文已加载：
- 纲领: structure/0_global/idea.md
- 当前章节: {CHAPTER_MD_PATH}
- 引用池: {逐行列出}
- 交叉参考: {有内容的其他章节 md 列表}
[仅 litrev]:
- 方向报告: {逐行列出}
- 检索方案: {文件名}
- 总报告: {文件名}
```

## 步骤 4：调度确认

`{INPUT_FORM}` = "single" → 跳过，直接对整个 section 执行步骤 5。

**4.1 确认**（AskUserQuestion）：
- Parent section 名称
- 子节列表（编号）
- 将读取的源文件列表
- 预计交互：每个子节 2 轮确认（intent + 要点）

**LR 特殊说明**（仅 `{SECTION_TYPE}` == `"litrev"`）：
- `{SPLIT_SEGMENTS}` 来自步骤 2.3（而非 manuscript.tex 解析）
- 子节列表末尾含"定位表"（特殊子节，走独立流程）
- 预计交互说明中注明：各方向子节 2 轮（intent + 要点），定位表 1 轮（文献选择 + 维度确认）

等待用户确认后开始循环。

**4.2 循环处理**：
```
FOR i, child IN enumerate({SPLIT_SEGMENTS}):
  a. 设置 {CURRENT_TITLE} = child.title
  b. 从 {CHAPTER_MD_CONTENT} 按 heading 提取该子节已有内容：
     匹配规则：忽略编号前缀（如 "### 2.1 "），对标题部分做模糊匹配
  c. 显示 "▶ [{i+1}/{total}]: {CURRENT_TITLE}"
  d. 执行步骤 5（单子节交互流程）
  e. 显示 "✓ [{i+1}/{total}] done"
END FOR
```

## 步骤 5：单子节交互流程

Form 1（single）执行一次，Form 2（multi）每个子节重复。

### 5.1 检查已有要点

从 `{CHAPTER_MD_CONTENT}` 中提取当前子节对应 heading 下的内容：

- **已有要点**（以 `- ` 开头的条目，且包含实质内容而非 TODO）→ 显示已有要点，AskUserQuestion：
  ```
  📋 该子节已有以下要点：
  {列出已有要点}

  选择操作：
  (1) 保留现有要点，跳过此子节
  (2) 在现有基础上补充/调整
  (3) 重新构建（覆盖）
  ```
  用户选 (1) → 跳过此子节，进入下一个
  用户选 (2) → 将已有要点作为起点，进入 5.2
  用户选 (3) → 忽略已有要点，进入 5.2

- **无要点或仅 TODO** → 直接进入 5.2

### 5.2 Intent 确认

基于以下信息生成该子节的一句话意图（概括这个子节要达成的论证目的）：

- idea.md 中的相关信息
- 章节 md 的 `## 必备元素` 中对应要求
- 章节 md 大纲中该子节的现有提示
- Section Tree 中的位置（前后关系）
- 其他章节 md 中的交叉参考信息

**LR 方向子节的 intent 格式**（仅 `{SECTION_TYPE}` == `"litrev"` 且非定位表）：

intent 展示完整写作蓝图摘要（来自步骤 2.1 的确认结果）：

```
💡 子节 intent：
> {one-line intent}
> 比重: 综述主体 ~85% | 指出不足+连接Gap ~15%
> 子主题: A({形式}) → B({形式}) → ... → [落脚]({形式}) → 不足 → Gap
```

**其他章节的 intent 格式**（Introduction / Discussion）：

```
💡 子节 intent：
> {one-line intent}
```

AskUserQuestion：确认 intent 或提出修改意见。

**循环**：用户不满意 → 修改 intent → 再次展示 → 直到用户确认。

### 5.3 要点构建

**分支判定**：如果 `{SECTION_TYPE}` == `"litrev"` 且当前子节为"定位表" → 执行 5.3 的定位表专用流程（见下方）。否则执行以下通用流程。

基于已确认的 intent，结合所有上下文，生成要点列表：

**生成依据**：
- 已确认的 intent 作为目标导向
- idea.md 中的相关论点
- 章节 md 大纲中的现有提示（如有）
- citation pool 中的可用文献
- 交叉参考上下文（确保一致性）
- bib 文件验证 citation key 存在性

**要点写作规范**：
- 中文表述，citation key/专用术语/公式符号用英文原文
- 每个要点包含核心论点 + 对应的 `\citep{}` 或 `\citet{}`
- **引用密度**：尽可能每个要点都带引用，宁多勿少（用户后期可删，但补加成本高）
- 每个要点引用不超过 2 个（硬性上限 3 个）
- 需要引用但 citation pool 中找不到合适文献 → 标记 `(ref)`
- **引用偏好**：遵循 citation pool 的分级说明（如 BG 优先近3年高质量期刊，GAP 优先近年进展而非经典文献）
- 如用户选了 (2) 补充模式，在已有要点基础上调整

**LR 方向子节的要点组织**（仅 `{SECTION_TYPE}` == `"litrev"` 且非定位表）：

要点按写作蓝图的**子主题**分组组织，citations 使用步骤 2.1 预分配的文献。在交互输出中用子主题标记辅助用户审阅（写入 md 时去掉标记）：

```
### {subsection title}
> {confirmed intent}

**综述主体** (~85%):
- [A] 要点1：{子主题A内容}（形式A）\citep{key1, key2}
- [A] 要点2：{子主题A内容}（形式A）\citep{key3}
- [B] 要点3：{子主题B内容}（形式B）\citet{key4} 的具体发现
- [B] 要点4：{子主题B内容}（形式B）\citet{key5} 的具体发现
- [C] 要点5：{子主题C内容}（形式A）\citep{key6, key7}
- [落脚] 要点6：{回溯到研究情境——已有证据1}（形式A/B）\citep{key8, key9}
- [落脚] 要点7：{回溯到研究情境——已有证据2}（形式B）\citet{key10}
- [落脚] 要点8：{回溯到研究情境——已有证据3}（形式A）\citep{key11}
- [落脚] 要点9：{回溯到研究情境——但未触及的核心问题}（形式A）\citep{key12}

**指出不足** (~50词):
- [不足] 要点10：{不足} \citep{key13}

**连接Gap**:
- [Gap] 要点11：→ G{x}

| # | Citation | 引用理由 |
|:-:|:---------|:---------|
| 1 | key1 | 为什么选这篇 |
| ... | ... | ... |
```

**与 Introduction/Discussion 的差异**：LR 要点的 citations 已在步骤 2.1 预分配，步骤 5.3 主要任务是**围绕预分配的 citations 撰写要点文本**。用户仍可在此阶段增删改 citations。

**通用输出格式**（Introduction / Discussion）：

```
### {subsection title}
> {confirmed intent}

- 要点1：论点内容 \citep{key1, key2}
- 要点2：论点内容 \citet{key3}
- 要点3：论点内容 (ref)
- ...

| # | Citation | 引用理由 |
|:-:|:---------|:---------|
| 1 | key1 | 为什么选这篇文献支撑该要点 |
| 2 | key2 | 为什么选这篇文献支撑该要点 |
| 3 | key3 | 为什么选这篇文献支撑该要点 |
```

AskUserQuestion：确认要点或提出修改意见（可以要求增删改某个要点、换引用、调整顺序等）。

**循环**：用户不满意 → 修改要点和引用理由表 → 再次展示 → 直到用户确认。

**定位表专用流程**（仅 `{SECTION_TYPE}` == `"litrev"` 且当前子节为"定位表"时）：

定位表不走正常的 intent → 要点流程，而是：

**a. 筛选候选文献**：从 citation pool、direction reports 中筛选 5-8 篇与本文最具可比性的文献（标准：研究主题相似、方法可对比、发现可对照）。如果 manuscript.tex 中已有文献对比表（如 `Tab:lit_comparison`），以该表为基础进行调整，而非从零开始。

**b. 确定对比维度**：默认维度（可根据具体论文调整）：研究方法（Method）、数据情境（Context/Industry）、网络层级（Level）、节点类型（Node type）、关键变量（Key variables）、主要发现（Key findings）

**c. 展示候选方案**：

```
📊 定位表（Literature Positioning Table）

**候选文献**（按相关度排序）：
| # | Citation | 为什么入选 |
|:-:|:---------|:---------|
| 1 | \citet{key1} | {与本文的可比性} |
| 2 | \citet{key2} | {与本文的可比性} |
| ... | ... | ... |

**对比维度**：{列出维度}

确认文献选择和对比维度？可以增删文献或调整维度。
```

AskUserQuestion 等待用户确认。**循环**：用户不满意 → 修改文献/维度 → 再次展示 → 直到用户确认。

**d. 生成定位表骨架**：用户确认后，生成完整的 markdown 定位表暂存（含每篇文献在各维度的填充内容）。bib 文件验证所有 citation key。

### 5.4 记录确认结果

将用户确认的要点（不含引用理由表、不含子主题标记 `[A][B][落脚][不足][Gap]` 等）暂存，等待步骤 6 字数分配。

定位表以完整表格形式暂存。

## 步骤 6：字数分配表

所有子节的要点确认完毕后，生成字数分配表供用户确认。

**6.1 确定总字数**：

从 `{CHAPTER_MD_PATH}` 头部读取 `> 目标字数: {N} words` 中的数值。

- **读到数值** → 使用该值（由 /method-audit step 5.8 基于 benchmark 写入）
- **读到 TBD 或无法解析** → AskUserQuestion：
  ```
  ⚠️ {md文件名} 的目标字数尚未确定（仍为 TBD）。
  建议先运行 /method-audit 基于 benchmark 论文确定各 section 字数。

  (1) 手动指定字数（输入数字）
  (2) 退出，先运行 /method-audit
  ```
  用户选 (1) → 使用用户指定值
  用户选 (2) → 退出

用户可在字数分配表确认（step 6.4）中修改总字数。

**6.2 自动分配各子节字数**：
- 基础分配 = 总字数 × (该子节要点数 / 全部要点数)
- 角色调整（按 `{SECTION_TYPE}` 分别处理）：

  **intro**：
  - Gap 段落权重 ×1.2
  - 论文结构固定 50 words
  - RQ 列表固定 100 words

  **litrev**：
  - 定位表标注"表格，不计字数"，不占正文字数配额
  - 总字数仅分配给各方向子节
  - 末方向（通常最接近核心 Gap、承担"指出不足→连接本文"的重任）权重 ×1.2
  - 各子节内部字数按写作蓝图比重自动分配（综述主体 ~85% / 指出不足+连接Gap ~15%），无需额外指定

  **discussion**：
  - 各 RQ discussion 子节按要点数等比分配
  - 无特殊权重调整

- 取整到最近的 50

**6.3 生成默认写作说明**：每个子节一句话风格指导

**6.4 输出字数分配表**（AskUserQuestion 让用户确认/修改）：

```
📊 字数分配方案（总目标: {N} words）

| 子节 | 要点数 | 目标字数 | 写作说明 |
|:-----|:---:|:---:|:------|
| {subsection1} | 4 | 200 | {风格指导} |
| ... | ... | ... | ... |
[仅 litrev]: | 定位表 | — | 表格，不计字数 | 对比表，由 /pen-draft 转为 LaTeX |
| 合计 | — | {N} | — |

你可以修改目标字数和写作说明。确认后写入 md。
```

**循环**：用户不满意 → 修改字数/说明 → 再次展示 → 直到用户确认。

## 步骤 7：写入

所有子节和字数分配确认后，将要点和字数分配表写入 `{CHAPTER_MD_PATH}`。

**写入规则**：

1. 读取 `{CHAPTER_MD_PATH}` 当前内容

2. **LR 额外写入**（仅 `{SECTION_TYPE}` == `"litrev"`）：

   a. 更新 `## 必备元素` 区块——将步骤 1-2 确认的方向列表和写作蓝图写入：
   ```markdown
   ## 必备元素

   1. **{N}个方向**（步骤 1 确认）:
      - 方向1: {title} → G{x}
      - 方向2: {title} → G{y}
      - ...
   2. **每个方向末尾点明 Gap**: Gap 编号与 Introduction 一致
   3. **定位表**: 本文 vs {M} 篇最相关文献的多维对比表（{列出维度}）
   4. **各方向写作蓝图**（步骤 2 确认）: 每个方向内部按子主题展开（综述主体 ~85% + 指出不足+连接Gap ~15%），含 citation 预分配和引用形式标注
   ```

   b. 在 `## 大纲` 中为每个方向创建 `###` heading（如不存在）

   c. **同步更新 manuscript.tex**：在匹配到的 `\section` 下，为每个方向插入 `\subsection{title}`（如不存在）。**定位表不插入 tex**——定位表是表格，不是独立 subsection，遍历时跳过。检查逻辑：读取 tex 中该 `\section` 与下一个 `\section` 之间的内容，如果已有对应 `\subsection` 则跳过，否则在 `\section` 行后按顺序插入。此步骤仅在 `{SECTION_TYPE}` == `"litrev"` 时执行——Introduction 和 Discussion 的 `###` 是隐形结构，不写入 tex。

3. 在 `## 大纲` 区块开头插入字数分配表：
   ```markdown
   ## 大纲

   **目标总字数: {N} words**

   | 子节 | 要点数 | 目标字数 | 写作说明 |
   |:-----|:---:|:---:|:------|
   | ... | ... | ... | ... |
   ```

4. 对每个已确认的子节：
   a. 定位 md 中对应的 heading（模糊匹配，忽略编号前缀）
   b. 替换该 heading 下的内容为：
   ```
   > {intent}

   - 要点1...
   - 要点2...
   ```
   c. 保留 heading 本身不变

5. **LR 定位表写入**（仅 `{SECTION_TYPE}` == `"litrev"`）：
   - 在 `## 大纲` 的最后一个 `###` 下写入完整定位表（markdown table 格式）

6. 保留 `## 引用池` 等非大纲/非必备元素区块不变

7. **同步 bib**：写入 md 后，立即将本章节新增的 citation key 同步到项目 bib：
   1. 从刚写入的所有要点中提取所有 `\citep{}`/`\citet{}` 中的 citation key（正则提取，去重）
   2. 检查每个 key 是否已在项目 bib 中
   3. 不在的 → 从 `master.bib` 中提取对应条目，追加到项目 bib 末尾
   4. master.bib 中也找不到 → 跳过（该 key 可能是手动添加的老文献，已在项目 bib 中，或标记为 `(ref)` 的待补文献）
   5. 显示同步结果：`📚 Bib 同步：{N} 个 key，新增 {M} 条到项目 bib`（M=0 时不显示）

**写入确认**：写入前 AskUserQuestion 展示即将写入的内容摘要：
```
📝 即将写入 {CHAPTER_MD_PATH}：

[仅 litrev]: **必备元素更新**: {N} 个方向 + 写作蓝图定义
[仅 litrev]: **manuscript.tex 更新**: 插入 {N} 个 \subsection{}
**字数分配表**: {N} words 分配到 {M} 个子节

### {subsection1}
> {intent1}
- {N1} 个要点，目标 {W1} words

### {subsection2}
> {intent2}
- {N2} 个要点，目标 {W2} words

[仅 litrev]: ### 定位表
- {M} 篇文献 × {K} 个维度

确认写入？
```

用户确认 → 执行写入。用户拒绝 → 结束，不写入。

## 步骤 8：完成提示

显示：
- ✅ 完成状态
- 📂 读取的源文件列表
- 📊 各子节要点数量 + 字数分配汇总
- ⚠️ 标记 `(ref)` 的数量（提醒用户后续补充文献）
- 💡 提示：要点就绪后可运行 `/pen-draft section=XXX` 生成初稿
