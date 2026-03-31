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

- 确认主文件存在（Glob `manuscript.tex` 或 `main.tex`）。不存在 → 停止，提示用户
- 确认当前目录是 git 仓库（`git status`）。不是 → 停止，提示用户初始化

### 0b. 冷启动检测（遗留项目适配）

读取项目 CLAUDE.md → 检查是否包含关键字段（期刊名、模板类型、bib 文件名）。

**如果 CLAUDE.md 不存在或缺少关键字段** → 进入冷启动模式：

```
📋 检测到项目尚未完整配置。请确认以下信息：

1. 主文件: [自动检测结果，如 manuscript.tex]
2. Bib 文件: [自动检测结果]
3. 目标期刊: ?
4. 出版社: [Elsevier / ASCE / Emerald / SAGE / IEEE / Wiley / 其他]
5. 编译方式: [从 latexmkrc 或文件头检测，如 pdflatex / xelatex]
6. 补充材料: [自动检测 supplemental-materials.tex / supplementary-materials.tex]
7. 作者信息（用于 Cover Letter 署名）: ?
```

用户确认后，生成或更新 CLAUDE.md 的 `## 项目信息` 和 `## 核心配置` 部分。不生成 `structure/` 目录——遗留项目不需要写作阶段的脚手架。

### 0c. 轮次检测

自动推断当前修改轮次 `{ROUND}`：

```
检测逻辑（按优先级）：
1. CLAUDE.md 的 ## 项目阶段 字段中有 revision-R{N} → ROUND = N（状态表示"当前在第 N 轮"）
2. 统计已有的 revision-R*/ 归档目录 → ROUND = 最大编号 + 1
3. 存在 manuscript-original.tex（旧格式）且无 revision-R*/ 归档 → ROUND = 1（遗留项目首次使用新系统）
4. 以上都没有 → ROUND = 1（全新项目）
```

展示检测结果并 AskUserQuestion 确认：

```
🔍 检测到当前应为第 {ROUND} 轮修改（R{ROUND}）。

确认？或输入正确的轮次编号。
```

### 0d. Git Checkpoint — 归档前快照

在任何文件移动或覆盖之前，先保存当前状态：

```bash
git add -A && git commit -m "R${ROUND} pre-init: snapshot before archiving R$((ROUND-1)) files" --allow-empty
```

> 这是安全网。如果后续归档或初始化出错，可以 `git reset --hard HEAD~1` 回到此状态。

### 0e. 已有文件处理（基于轮次）

**检查 `revision-R{ROUND}/` 是否已存在**（可能是上次 rev-init 中断留下的）：
- 已存在 → AskUserQuestion：「`revision-R{ROUND}/` 目录已存在：**1** = 删除后重新初始化 / **2** = 停止」
- 不存在 → 继续

**如果 `revision/` 存在**（遗留项目的旧格式目录）：
- `ROUND == 1` → `mv revision revision-R0`（归档为 R0）
- `ROUND >= 2` → 警告用户存在旧格式目录，建议手动处理

**如果 `response-letter.tex` 已存在**：
- `ROUND >= 2` → 归档：`mv response-letter.tex response-letter-R$((ROUND-1)).tex`
- `ROUND == 1` 且已有实质内容 → AskUserQuestion：覆盖 / 保留

**遗留兼容**：如果存在 `manuscript-original.tex`（旧格式）且 `ROUND == 1`：
- 不重复冻结，直接复用为 R0 基准
- 创建 `.revision-baseline` 指向它

---

## Step 1: 冻结基准

冻结当前 `manuscript.tex` 为本轮的 diff 基准：

```bash
# 基准文件名：manuscript-R{ROUND-1}.tex
BASELINE="manuscript-R$((ROUND-1)).tex"

# 遗留兼容：如果已有 manuscript-original.tex 且 ROUND=1，复用它
if [ "$ROUND" = "1" ] && [ -f "manuscript-original.tex" ]; then
    BASELINE="manuscript-original.tex"
else
    cp manuscript.tex "$BASELINE"
fi

# 写入 .revision-baseline 供 make-diff.sh 读取
echo "$BASELINE" > .revision-baseline

git add "$BASELINE" .revision-baseline && git commit -m "R${ROUND}: Freeze baseline ($BASELINE) for latexdiff"
```

告知用户：`{BASELINE}` 已冻结，此后**永远不得修改**。

---

## Step 2: 创建目录 + 复制工具 + 配置 Hook

```bash
mkdir -p tools revision-R${ROUND}/drafts .claude/hooks
```

从 `~/.claude/skills/rev-init/` 读取以下文件并写入项目：
- `make-diff.sh` → `tools/make-diff.sh`（`chmod +x`）
- `latexdiff-preamble.tex` → `tools/latexdiff-preamble.tex`

### Hook 配置

#### 编译 Hook（升级为 diff 版本）

用 `~/.claude/skills/rev-init/latex-compile.sh` **覆盖** `.claude/hooks/latex-compile.sh`（`chmod +x`）。

paper-init 创建的原版只做纯编译。rev-init 的升级版增加：
- 如果修改的是 `manuscript.tex`，额外运行 `tools/make-diff.sh` 生成 track changes PDF
- 编译 + diff 均在后台运行，不阻塞工作流

#### Unicode Guard（确保存在）

检查 `.claude/hooks/unicode-guard.sh` 是否存在：
- 存在（paper-init 已创建）→ 跳过
- 不存在（旧项目）→ 从 `~/.claude/skills/paper-init/unicode-guard.sh.tmpl` 复制（`chmod +x`）

#### settings.local.json Hook 配置

确保 `.claude/settings.local.json` 同时包含两个 hook（保留已有的 permissions）：

```json
"hooks": {
  "PreToolUse": [
    {
      "matcher": "Edit|Write",
      "hooks": [
        {
          "type": "command",
          "command": "\"$CLAUDE_PROJECT_DIR/.claude/hooks/unicode-guard.sh\""
        }
      ]
    }
  ],
  "PostToolUse": [
    {
      "matcher": "Edit|Write",
      "hooks": [
        {
          "type": "command",
          "command": "\"$CLAUDE_PROJECT_DIR/.claude/hooks/latex-compile.sh\"",
          "timeout": 120
        }
      ]
    }
  ]
}
```

> hook command 统一使用 `$CLAUDE_PROJECT_DIR` 绝对路径，与 paper-init 模板一致。

---

## Step 3: 获取决定信

AskUserQuestion：

```
请提供审稿决定信的来源：
  [1] 已粘贴到 revision-R${ROUND}/comment-letter.md
  [2] 直接在此处粘贴原文
  [3] 从文件路径读取
```

- 选 1 → 读取 `revision-R${ROUND}/comment-letter.md`，确认非空
- 选 2 → 用户粘贴内容 → 写入 `revision-R${ROUND}/comment-letter.md`
- 选 3 → 用户提供路径 → 读取 → 写入 `revision-R${ROUND}/comment-letter.md`

---

## Step 4: 解析决定信（主 Agent）

### 4a. 通读原始决定信

主 Agent 读取 `revision-R${ROUND}/comment-letter.md` 全文，理解整体结构。不同期刊/投稿系统的格式差异极大，需要 LLM 的语义理解能力来正确识别结构，不可使用硬编码脚本。

### 4b. 结构识别

识别并分离以下角色：
- **Editor / Handling Editor**：决定信正文、编辑要求
- **Associate Editor**（如有）：AE 综合评价
- **Reviewer #N**：每位审稿人的意见

注意：
- 审稿人编号保留原始编号（如 #2, #3, #4，不重编为 #1, #2, #3）
- 识别 Q&A 区域（如 ASCE EM 的标准化问答表），提取含实质性反馈的回答

### 4c. 编号处理

对每位 Reviewer 的意见进行编号：
- 审稿人已分 Major/Minor → `RN-K` / `RN-mK`
- 审稿人未分 Major/Minor → 连续编号 `RN-1, RN-2, ...`（不强行分类）
- 保留原始编号；一个独立关切 = 一条 Comment
- 同一段落内多个独立问题 → 拆分为独立 Comment
- 保留完整原始英文文本，不改写不缩减

### 4d. 生成 comment-letter-clean.md

读取 `comment-letter-clean.md.tmpl` 模板格式，生成 `revision-R${ROUND}/comment-letter-clean.md`，包含：
- 头部元信息（决定类型、日期、截止日期、编辑姓名）
- Editor / AE / 每位 Reviewer 各有独立标题
- 每条意见有 ID 前缀（`**R1-1.**`、`**R1-m1.**`）
- Q&A 区域提取（如有实质性反馈）
- 末尾的初步分类工作区表格（供 Step 5 填写）

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

**1** = 确认无误，或直接输入需要调整的地方。
```

用户输入调整意见 → 修改后重新展示 → 再次 AskUserQuestion。**迭代直到用户输入 1**。

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
- 全部接受：**1**
```

**迭代直到用户输入 1**。

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
- 全部接受：**1**
```

**迭代直到用户输入 1**——这是整个初始化最关键的交互点。

### Git Checkpoint — 分类聚类确认后

分类和聚类方案用户确认后立即保存（这是最昂贵的交互产物）：

```bash
git add revision-R${ROUND}/comment-letter.md revision-R${ROUND}/comment-letter-clean.md && \
git commit -m "R${ROUND} rev-init: parsed comments + confirmed classification & clustering"
```

### 特殊情况

**矛盾意见**：两位审稿人要求互相矛盾 → 放入同一 Cluster，标注 "⚠️ 矛盾"，要求用户做取舍决策。

**AI 使用披露**：审稿人质疑 AI 使用 → Highest 优先级合规问题。此条回复策略**必须由用户亲自确认**，AI 不得自行起草 AI 使用声明。

---

## Step 7: 生成追踪文件

基于用户确认的聚类方案，读取模板并生成：

1. **`revision-R${ROUND}/revision-guide.md`**：读取 `revision-guide.md.tmpl`，填充全部 9 个 Section
   - Section 3 行号表：用 `grep -n "\\section\|\\subsection" manuscript.tex` 获取
   - Section 4 意见清单：从 comment-letter-clean.md 导入，回填 Cluster 列
   - Section 5 Cluster 分析：从确认的聚类方案填充

**进度追踪说明**：不单独生成进度文件。回复完成状态直接通过 `response-letter.tex` 中的 `[TO BE FILLED]` 占位符判断——有占位符 = 未完成，无占位符 = 已完成。

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
   - 每条 Comment → `\reviewercomment{Comment \#N-K.}` + 换行 + 审稿人原文（不加粗） + `\responseheader` + `\response{[TO BE FILLED]}` + `\bigskip`
     - `\reviewercomment{}` 内**只放编号**（如 `Comment \#2-1.`），不要自编标题
     - 如果审稿人原文自带标题/编号（如 "Major Comment 1: ..."），则将其原样作为 `\reviewercomment{}` 的内容
     - 审稿人意见正文作为普通文本（不加粗）另起一行

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

确认后 → 填入 `response-letter.tex` + 保存草稿到 `revision-R${ROUND}/drafts/Response_*.md`。

---

## Step 10: 更新 CLAUDE.md

### 10a. 追加/更新修改工作流配置

AskUserQuestion：是否自动追加修改工作流配置到项目 CLAUDE.md？

如用户选是，追加：修改工作流节（上下文文件、skills、闭环步骤）+ Response Letter 格式规范。

### 10b. 更新项目阶段字段

在 CLAUDE.md 中查找 `## 项目阶段` 部分：
- 已存在 → 更新 `状态` 和 `更新时间`
- 不存在 → 在文件末尾追加

```markdown
## 项目阶段
- 状态: revision-R{ROUND}
- 更新时间: {TODAY}
- 基准文件: {BASELINE}
- 轮次历史:
  - R{ROUND}: {TODAY}（{DECISION_TYPE}）
```

如果是 R2+，保留之前的轮次历史记录，追加新行。

---

## Step 11: 编译 + Git Checkpoint（最终）+ 摘要

1. 编译验证：`latexmk -pvc- -pv- response-letter.tex` + `latexmk manuscript.tex`
2. Git 提交所有初始化产物：
   ```bash
   git add -A && git commit -m "R${ROUND} rev-init: complete initialization (guide + response skeleton + general responses)"
   ```
3. 展示摘要：文件树 + 当前轮次 R{ROUND} + Cluster 总览 + 推荐执行顺序 + 下一步指引（`/rev-respond {first anchor ID}`）
