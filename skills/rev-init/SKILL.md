---
description: "一次性初始化修改工作流（冻结基准 → 解析决定信 → 交互式聚类 → 搭骨架 → 概括性回复）"
---

# Rev-Init — 修改工作流初始化

一次性初始化论文修改项目：冻结基准稿件、解析审稿决定信、交互式分类与聚类、生成追踪文件骨架、构建回复信骨架、生成概括性回复。

**核心原则**：所有分类和聚类决策必须经用户确认后才执行。AI 提方案，用户拍板。

## 输入说明

`$ARGUMENTS` 可选，通常为空。如提供，视为附加指令（如 `审稿人编号从 #2 开始`）。

---

## Step 0: 前置检查

### 0a. 项目环境

- 确认 `manuscript.tex` 存在（Glob `manuscript.tex`）。不存在 → 停止，提示用户
- 确认当前目录是 git 仓库（`git status`）。不是 → 停止，提示用户初始化
- 读取项目 CLAUDE.md，提取：期刊名、模板类型、bib 文件名、编译命令

### 0b. 已有文件检查

- 检查 `revision/` 是否已存在
  - 存在 → AskUserQuestion：「`revision/` 目录已存在，是否归档到 `revision-archived/` 后重新初始化？」
  - 用户确认归档 → `mv revision revision-archived`
- 检查 `manuscript-original.tex` 是否已存在
  - 存在 → 跳过 Step 1（冻结步骤）
- 检查 `response-letter.tex` 是否已存在
  - 存在 → AskUserQuestion：「`response-letter.tex` 已存在，是否覆盖？」

---

## Step 1: 冻结基准

（仅在 `manuscript-original.tex` 不存在时执行）

```bash
cp manuscript.tex manuscript-original.tex
git add manuscript-original.tex && git commit -m "Freeze baseline for latexdiff"
```

告知用户：`manuscript-original.tex` 已冻结，此后**永远不得修改**。

---

## Step 2: 创建目录 + 复制工具

```bash
mkdir -p tools revision/drafts
```

从 `~/.claude/skills/rev-init/` 读取以下文件并写入项目：
- `make-diff.sh` → `tools/make-diff.sh`（`chmod +x`）
- `latexdiff-preamble.tex` → `tools/latexdiff-preamble.tex`

---

## Step 3: 获取决定信

AskUserQuestion：

```
请提供审稿决定信的来源：
  [1] 已粘贴到 revision/comment-letter.md
  [2] 直接在此处粘贴原文
  [3] 从文件路径读取
```

- 选 1 → 读取 `revision/comment-letter.md`，确认非空
- 选 2 → 用户粘贴内容 → 写入 `revision/comment-letter.md`
- 选 3 → 用户提供路径 → 读取 → 写入 `revision/comment-letter.md`

---

## Step 4: 解析决定信

### 4a. 识别结构

读取 `revision/comment-letter.md`，自动检测：

**角色边界**：
- **Editor**：检测 "Decision"、"Editor's comments" 等关键词
- **Associate Editor**：检测 "Associate Editor"、"AE" 等关键词
- **Reviewer #N**：检测 "Reviewer #1"、"Reviewer 2" 等模式

**意见结构**（每位 Reviewer）：
- 是否已分 Major/Minor
- 是否已编号
- 是否为连续段落（无编号）

**Q&A 区域**：
- 检测标准化问答（ASCE EM、Elsevier EES 的 Q&A 表格）
- 包含实质性回答 → 提取为独立 Comment，标注 "(from Q&A)"

### 4b. 编号处理

- 保留审稿人原始编号（#2, #3, #5 不重编为 #1, #2, #3）
- 已分 Major/Minor → `RN-K` / `RN-mK`
- 未分 Major/Minor → 连续编号 `RN-1, RN-2, ...`
- 一条评论含多个独立问题 → 拆分为独立 Comments

### 4c. 清理

- 删除邮件头、系统页脚、日历附件说明
- 保留所有实质性内容（包括审稿人原始措辞和拼写错误）

### 4d. 生成输出

读取 `~/.claude/skills/rev-init/comment-letter-clean.md.tmpl`，按模板格式生成 `revision/comment-letter-clean.md`。

### 4e. 展示并确认

展示统计摘要：
- 识别到 N 位审稿人
- 每位审稿人 N 条 Major / M 条 Minor
- 是否有 Q&A 提取
- 审稿人编号是否连续

AskUserQuestion：

```
解析结果如上。请检查：
- 审稿人数量和编号是否正确？
- 意见拆分是否合理？
- 有无遗漏的实质性意见？

确认无误请回复 "ok"，或说明需要调整的地方。
```

用户要求调整 → 修改后重新展示 → 再次确认。反复迭代直到用户说 ok。

---

## Step 5: 交互式分类

读取 `~/.claude/skills/rev-init/reference.md` 获取分类规则。

AI 对每条 Comment 提出分类建议：
- **类型**：Modify / Explain / Supplement
- **优先级**：Highest / High / Medium / Low

展示完整分类表：

```
| ID | 核心问题（5-8词） | 类型 | 优先级 | 备注 |
|----|-------------------|------|--------|------|
| R1-1 | 核心概念定义模糊 | Modify | Highest | R2-1 也提到 |
| R1-2 | 方程符号不一致 | Modify | Highest | R3-4 类似 |
| ...  | ... | ... | ... | ... |
```

AskUserQuestion：

```
以上是 AI 建议的分类结果。请逐条确认或修改：
- 修改某条：如 "R1-3: 优先级改为 High"
- 全部接受：回复 "ok"
```

反复迭代直到用户确认。

---

## Step 6: 交互式聚类（核心交互点）

读取 `~/.claude/skills/rev-init/reference.md` 获取聚类决策树和主题类别。

基于分类结果提出 Cluster 方案：

```
## 聚类方案

### C1: [名称] (Highest)
- 涉及: R1-1, R2-1, R3-1
- 锚点: R1-1（最详细，3个具体要求）
- 核心问题: [一句话提炼]
- 理由: [为什么这些意见归为一组]

### C2: [名称] (Highest)
- 涉及: R1-2, R3-4
- 锚点: R1-2
- 理由: [...]

...

### 依赖关系
C2 → C1（C1 需要 C2 的符号统一结果）

### 推荐执行顺序
1. C2（全局影响，无依赖）
2. C1（依赖 C2）
3. ...
```

AskUserQuestion：

```
以上是 AI 建议的聚类方案。请审阅并调整：
- 合并：如 "合并 C3 和 C5"
- 拆分：如 "C2 拆为 C2a 和 C2b"
- 调整归属：如 "R2-3 从 C1 移到 C4"
- 调整锚点：如 "C1 锚点改为 R2-1"
- 修改方向：如 "C3 重点改 Methods 而非 Introduction"
- 全部接受：回复 "ok"
```

**反复迭代直到用户确认**——这是整个初始化最关键的交互点。

### 特殊情况

**矛盾意见**：两位审稿人要求互相矛盾 → 放入同一 Cluster，标注 "⚠️ 矛盾"，要求用户做取舍决策。

**AI 使用披露**：审稿人质疑 AI 使用 → Highest 优先级合规问题。此条回复策略**必须由用户亲自确认**，AI 不得自行起草 AI 使用声明。

---

## Step 7: 生成追踪文件

基于用户确认的聚类方案，读取模板并生成：

1. **`revision/revision-guide.md`**：读取 `revision-guide.md.tmpl`，填充全部 9 个 Section
   - Section 3 行号表：用 `grep -n "\\section\|\\subsection" manuscript.tex` 获取
   - Section 4 意见清单：从 comment-letter-clean.md 导入，回填 Cluster 列
   - Section 5 Cluster 分析：从确认的聚类方案填充

2. **`revision/cluster-progress.md`**：读取 `cluster-progress.md.tmpl`，从 revision-guide.md 派生。所有状态 ⬜。

3. **`revision/response-progress.md`**：读取 `response-progress.md.tmpl`，从 revision-guide.md 派生。包含 Proposal 文件列和 Comment 文件列。

---

## Step 8: 构建 response-letter.tex 骨架

读取 `~/.claude/skills/rev-init/response-letter.tex.tmpl`，填入：

1. 标题 `[MANUSCRIPT-ID]` → 实际稿件编号
2. 开篇段落 `[N]` → 审稿人数量（two/three）；无 AE 删除 "the Associate Editor, and"
3. 目录 → 按实际审稿人编号生成
4. Editor → 粘贴意见原文
5. AE（如有）→ 粘贴意见原文
6. 每位 Reviewer：
   - General Assessment 原文
   - 每条 Comment → `\reviewercomment{}` + 原文 + `\responseheader` + `\response{[TO BE FILLED]}` + `\bigskip`

写入 `response-letter.tex`。

验证：`grep -c "TO BE FILLED" response-letter.tex` = 需填写的总条目数。

---

## Step 9: 生成 General Responses

### 9a. 生成规则

对 Editor、AE（如有）、R1-0、R2-0、...、RN-0 生成概括性回复：
- 每个回复 3-6 句话（80-150 words）
- 使用 `\response{}` 包裹，不用 `\manuscriptquote{}` 和 `\lineref{}`
- **每个对象的感谢措辞必须不同**（限一个描述性形容词）
- 引用格式：纯文本 `(Author et al., Year)`，不用 natbib
- 科技写作纪律：短句（≤25词）、主动语态、克制修饰、无中式英语

### 9b. 回复要点

- **Editor**：感谢安排审稿 + 概述修改方向 + 针对编辑特别要求的概括性回应
- **AE**：感谢协调和综合评价 + 简要说明已做对应改进
- **Reviewer #X-0**：感谢时间和专业评审 + 对总体评价回应 + 引导到逐条回复

### 9c. 展示 + 确认

一次性展示所有 general responses → AskUserQuestion 确认。

确认后 → 填入 `response-letter.tex` + 保存草稿到 `revision/drafts/Response_*.md` + 更新 `response-progress.md`。

---

## Step 10: 更新 CLAUDE.md

AskUserQuestion：是否自动追加修改工作流配置到项目 CLAUDE.md？

如用户选是，追加：修改工作流节（上下文文件、skills、闭环步骤）+ Response Letter 格式规范。

---

## Step 11: 编译 + 提交 + 摘要

1. 编译验证：`latexmk -pvc- -pv- response-letter.tex` + `latexmk manuscript.tex`
2. Git 提交所有新文件
3. 展示摘要：文件树 + Cluster 总览 + 推荐执行顺序 + 下一步指引（`/rev-respond {first anchor ID}`）
