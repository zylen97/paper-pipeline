---
description: "交互式逐条审稿回复闭环（策略对齐 → 内容起草 → 执行），每步用户确认后推进"
---

# Rev-Respond — 交互式逐条审稿回复

对单条审稿意见执行完整的交互式闭环：策略对齐 → 内容起草 → 执行。每一步都需要用户确认后才推进到下一步。

**核心原则**：AI 只提方案，用户拍板。确认前不写文件、不改稿件、不填回复。

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

### 0b. 前置环境检查

检查 `/rev-init` 是否已执行：
- 确认 `revision/comment-letter-clean.md` 存在
- 确认 `revision/revision-guide.md` 存在
- 确认 `response-letter.tex` 存在

任一文件缺失 → **停止**，提示用户："请先运行 `/rev-init` 初始化修改工作流。"

### 0c. 读取项目上下文

依次读取以下文件：
1. `revision/comment-letter-clean.md` → 定位该 Comment 的完整评论文本
2. `revision/revision-guide.md` → 找到所属 Cluster、核心问题、修改计划、锚点信息
3. `manuscript.tex` → 全文（重点关注与该 Comment 相关的 section）
4. 项目 `.bib` 文件 → 可用引用（从 CLAUDE.md 或 `manuscript.tex` 的 `\bibliography{}` 确认文件名）
5. `response-letter.tex` → 定位该 Comment 的填写位置，同时检查哪些 Comment 的 `[TO BE FILLED]` 已被替换（= 已完成）
6. 如 `supplemental-materials.tex` 存在 → 读取（该 Comment 可能涉及补充材料修改）

### 0d. 检查同 Cluster 上下文

扫描 `revision/drafts/` 目录：
- 查找同 Cluster 的 `Proposal_*.md` 和 `Comment_*.md`
- 如有 → 读取已确认的策略和回复，保持一致性
- 判断交叉引用类型：
  - **同审稿人**（如 R1-4 和 R1-1 同属 C1）→ 回复中可直接引用（"As discussed in our response to Comment #1-1 above..."）
  - **跨审稿人**（如 R2-1 和 R1-1 同属 C1）→ **必须自含式回复**，不可引用其他 Reviewer 的 Comment

### 0e. 防护检查

- `revision/drafts/Proposal_{Comment_ID}.md` 或 `Comment_{Comment_ID}.md` 已存在 → AskUserQuestion："该 Comment 已有草稿文件，是否覆盖重做？"
- `response-letter.tex` 中该 Comment 的 `\response{[TO BE FILLED]}` 已被替换（即已有实质回复内容）→ 警告用户，AskUserQuestion："该 Comment 已有回复内容，是否覆盖重做？"
- 该 Cluster 依赖的其他 Cluster 尚未完成（检查方法：revision-guide.md 中依赖 Cluster 的 Comments 在 response-letter.tex 中仍有 `[TO BE FILLED]`）→ 警告（非阻断）："⚠️ C2 依赖 C1，但 C1 尚未完成。建议先处理 C1。"

---

## Round 1: 策略对齐

### 1a. 生成策略提案

在对话中展示策略提案（**不写文件**）：

```
## 策略提案 — {Comment ID}

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

回复 "ok" 确认策略，或提出调整意见。
```

用户说调整 → 根据反馈修改策略，重新展示 → 再次 AskUserQuestion。**反复迭代直到用户说 ok**。

### 1c. 保存确认的策略

写入 `revision/drafts/Proposal_{Comment_ID}.md`：

```markdown
# 策略提案 — {Comment ID}

> **审稿人**: Reviewer #{X}
> **所属集群**: C{N} — {Cluster 名称}
> **角色**: {Anchor/Satellite}
> **确认日期**: {当前日期}

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
- 行号写入当前值或 `[TBD]`，不回头更新旧的 lineref
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
- 检查 `revision/drafts/` 中已有回复，确保不重复

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

### 2b. 用户交互

展示 Part A 和 Part B 给用户。

AskUserQuestion：

```
以上是 {Comment ID} 的完整草稿。请审阅：

【回复信文本】措辞、论证逻辑、承诺程度
【修改方案】范围、具体措辞

回复 "ok" 确认，或提出具体修改意见。
```

用户说调整 → 修改后重新展示 → 再次 AskUserQuestion。**反复迭代直到用户说 ok**。

### 2c. 保存确认的草稿

写入 `revision/drafts/Comment_{Comment_ID}.md`：

```markdown
# Comment {Comment_ID} 回复

> **审稿人**: Reviewer #{X}
> **意见编号**: {Comment ID} — {简短标题}
> **所属集群**: C{N} — {Cluster 名称}
> **角色**: {Anchor/Satellite}
> **确认日期**: {当前日期}

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

## Round 3: 执行

### 3a. 应用稿件修改

使用 Edit 工具逐条应用确认的修改（manuscript.tex 和/或 supplemental-materials.tex）。

**铁律**：仅改确认内容，不做额外修改。

### 3b. 填写回复信

在 `response-letter.tex` 中定位该 Comment 的 `\response{[TO BE FILLED]}`，替换为确认的回复文本。

如果该 Comment 的 `\response{[TO BE FILLED]}` 找不到（可能已被提前填写），告知用户并跳过。

### 3c. 编译验证

编译由 PostToolUse hook 自动触发（`/rev-init` Step 2 配置）：
- Edit/Write `.tex` 文件后自动编译
- 修改 `manuscript.tex` 时额外生成 track changes PDF

**主 Agent 无需手动执行编译命令。** 如果 hook 报告编译失败，告知用户错误信息，不自动修复。

### 3d. Commit 决策

AskUserQuestion：

```
{Comment ID} 已完成：
  ✅ manuscript.tex 已修改（{N} 处）
  ✅ response-letter.tex 已填写
  ✅ 编译 {通过/失败}

是否提交 Git commit？
  [yes] 提交
  [no] 暂不提交
```

如 yes：
```bash
git add manuscript.tex response-letter.tex \
       revision/drafts/
# 仅在修改了补充材料时才 add
git add supplemental-materials.tex 2>/dev/null || true
git commit -m "C{N} {Comment_ID}: {brief description}"
```

### 3e. 下一步提示

展示：
- 当前 Cluster 剩余情况（从 revision-guide.md 获取 Cluster 成员列表，grep response-letter.tex 中对应 Comment 的 `[TO BE FILLED]` 计数）
- 推荐下一条 Comment（Cluster 内：锚点优先；Cluster 间：按 revision-guide.md 执行顺序）
- 依赖警告（如有）

---

## 科技写作纪律（适用于所有生成文本）

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

## 质量检查清单

每条回复完成前自检：

- [ ] 感谢措辞不与已有回复重复
- [ ] 每个论证点有具体支撑（文献/推导/逻辑）
- [ ] `\response{}`、`\manuscriptquote{}`、`\lineref{}` 格式正确且不嵌套
- [ ] 回复直接回应审稿人核心关切（不答非所问）
- [ ] Part A 和 Part B 内容一致
- [ ] 行号准确（或已标注 [TBD]）
- [ ] 未过度承诺（用 "We addressed" 而非 "We have completely resolved"）
- [ ] 与同 Cluster 其他回复一致
- [ ] 跨审稿人回复为自含式（无 "see Comment #X-Y" 跨审稿人引用）
- [ ] 科技写作纪律通过（短句、主动语态、无冗余修饰）
- [ ] 回复体现对目标期刊读者群的关注（从 CLAUDE.md 或 revision-guide.md 确认期刊和读者群特征）
- [ ] 回复中使用了论文的核心术语（从 revision-guide.md 或 manuscript.tex 摘要提取）
