---
description: "交互式研究idea与方法设计审稿迭代（idea-reviewer审稿 → 用户确认 → 修改idea.md → 循环至满意）"
---

# Idea Refine — 交互式 idea + 方法设计审稿迭代

调用 idea-reviewer agent 对 `idea.md` 进行多轮审稿，迭代优化研究 idea 和方法设计，直到用户满意。

**核心特征**：
- **idea + 方法同步审**：idea 和方法设计是耦合的，审稿人同时评估两者
- **交互式迭代**：reviewer 给出编号意见 → **用户逐条确认** → 主 agent 修改 idea.md → 可选下一轮
- **自动检测调用情境**：区分 idea 定稿前（Context a）和技术开发中（Context b）
- **版本管理**：每轮自动快照，保留完整审稿轨迹

**输入** `$ARGUMENTS`：无参数，直接运行 `/idea-refine`。

---

## 全局约束

### ⛔ Fail-Fast 规则
- `idea.md` 不存在或内容 < 100 字符 → 立即停止，提示用户先创建 idea
- idea-reviewer agent 调用失败 → 报告错误，等待用户指示

### 输出语言
**所有描述性文本使用中文**。idea.md 中的英文学术术语、期刊名、方法名保持原文。

---

## 步骤 0：前置准备

### 0.1 读取项目信息

- 读取 `CLAUDE.md` → 提取项目编号、目标期刊、方法类型（METHOD_TYPE）
- 缺失则警告，但不停止

### 0.2 读取 idea.md

- 读取 `structure/0_global/idea.md`
- 不存在 → **停止**，提示："idea.md 未找到。请先通过 `/idea-mine` 生成或手动创建 idea。"
- 内容 < 100 字符 → **停止**，提示："idea.md 内容过少，请先完善基本内容。"
- 提取版本号（`版本: vX.Y`），缺失则默认 `v0.0`

### 0.3 自动检测调用情境

Glob 检查以下文件：
- `structure/3_methodology/*_dev.md`
- `structure/4_results/*_dev.md`
- `structure/5_simulation/*_dev.md`（如存在）

**判定规则**：
- 任一 `_dev.md` 文件内容 > 500 字符 → **Context (b)：技术开发中的重新评估**
- 否则 → **Context (a)：idea 定稿前的主要成熟化**

向用户展示：
```
📍 调用情境：Context (a) — idea 定稿前的主要成熟化
   （未检测到实质性 _dev.md 内容）
```
或
```
📍 调用情境：Context (b) — 技术开发中的重新评估
   （检测到 _dev.md：methodology_dev.md, results_dev.md）
```

### 0.4 扫描可用材料

Glob 检查每项，记录存在/不存在：

| 材料 | 路径 | 用途 |
|------|------|------|
| 源论文精读 | `structure/0_global/idea-context/paper_note.md` | reviewer 理解迁移基础 |
| 期刊适配版本 | `structure/0_global/idea-context/adaptations/*.md` | reviewer 了解期刊定制 |
| idea-mine 审稿 | `structure/0_global/idea-context/reviews/*.md` | reviewer 参考前序评审 |
| 方法论综述 | `structure/2_literature/method_landscape.md` | reviewer 对标方法论现状 |
| 方法引用池 | `structure/2_literature/citation_pool/METHOD.md` | reviewer 了解方法先例 |
| 文献总报告 | `structure/2_literature/master_report.md` | reviewer 交叉验证 Gap |
| 方向报告 | `structure/2_literature/direction*_report.md` | reviewer 了解文献覆盖 |
| 技术开发文件 | `structure/3_methodology/*_dev.md` 等 | Context (b) 一致性检查 |

向用户展示材料可用性摘要：
```
📦 可用材料：
  ✅ idea.md (v0.1)
  ✅ paper_note.md
  ✅ method_landscape.md
  ✅ citation_pool/METHOD.md (32篇)
  ❌ idea-context/reviews/ — 未找到
  ❌ master_report.md — 未找到
  ...
```

如果可用材料极少（只有 idea.md），额外提示：
```
⚠️ 可用上下文材料有限，审稿质量受限。建议先完成 /lit-pool 后再运行 /idea-refine。
```

### 0.5 创建/复用工作目录

- 目录：`structure/0_global/idea-refine/`
- 已存在则复用（支持跨 session 多轮）

### 0.6 确定轮次编号

- Glob `structure/0_global/idea-refine/review_r*.md`
- M = 最大已有轮次 + 1（无则 M = 1）

### 0.7 版本快照

- 复制当前 `idea.md` → `structure/0_global/idea-refine/idea_v{X.Y}_before_r{M}.md`

---

## 步骤 1：idea-reviewer 审稿

### 1.1 调用 idea-reviewer

调用 idea-reviewer（`subagent_type: "idea-reviewer"`），prompt 要素：

```
Read `structure/0_global/idea.md` as the primary review target.

## Available Context Materials
{逐条列出 Step 0.4 中标记为 ✅ 的文件的完整绝对路径}

## Invocation Context
{Context (a) 或 (b) 的描述}

{仅 Context (b) 时追加以下内容：}
## Additional Focus for Mid-Development Review
Also read the following technical development files:
{列出所有 _dev.md 文件的完整绝对路径}

Check for consistency between technical development content and idea.md claims:
- Flag cases where the modeling work has evolved beyond what idea.md describes
- Flag opportunities discovered during technical development that idea.md should capture
- Flag assumptions in idea.md that technical findings have invalidated or refined

## Review Instructions
- Output a NUMBERED list of specific, actionable improvement suggestions
- Each suggestion must reference the idea.md section it applies to (§1-§5)
- Do NOT suggest changing the fundamental method type
- Do NOT suggest specific literature to add
- Focus on idea architecture and method design, not prose quality
```

保存审稿意见 → `structure/0_global/idea-refine/review_r{M}.md`

### 1.2 用户确认

将审稿意见展示给用户，AskUserQuestion：

```
📋 第{M}轮 idea 审稿意见（共 N 条）：

1. [§X] {issue} → {suggestion}
2. [§X] {issue} → {suggestion}
...

请选择要执行的意见：
- 接受：输入编号（如 "1,3,5" 或 "all"）
- 拒绝：输入 "reject 2,4"
- 修改某条：输入 "3: 改为..."
- 终止：输入 "done"（不做修改，结束流程）
```

- 用户选 "done" → 跳到步骤 3（收尾）
- 用户选择后，生成确认清单 → 保存到 `structure/0_global/idea-refine/confirmed_r{M}.md`

---

## 步骤 2：执行修改

### 2.1 生成修改方案

基于用户确认的意见，主 agent 生成**具体修改方案**——逐条列出对 idea.md 的修改：

```
📝 修改方案（共 K 条）：

1. [对应意见#1, §2 Gap]
   当前内容: "G1: 现有研究缺乏对XX的系统分析"
   改为: "G1: 现有研究虽从A和B角度探讨了XX，但未考虑C机制在D情境下的调节作用"

2. [对应意见#3, §3 方法论]
   当前内容: "采用博弈论建模分析三方决策"
   改为: "采用三阶段Stackelberg博弈分析三方序贯决策，引入信息不对称假设以反映..."

...
```

AskUserQuestion：确认修改方案，或调整某条的具体内容。

### 2.2 执行修改

用户确认方案后，主 agent 直接使用 Edit 工具逐条修改 `structure/0_global/idea.md`。修改时严格遵守：
- **只改方案中列出的内容**，不做额外改动
- 保留 idea.md 的整体结构和格式
- 更新 frontmatter 中的版本号（v0.1 → v0.2，递增末位；如版本字段缺失则新增 `> **版本**: v0.1`）
- 更新 frontmatter 中的日期

保存修改后快照 → `structure/0_global/idea-refine/idea_v{NEW}_after_r{M}.md`

### 边界处理：idea.md 被外部修改

如果 Edit 工具因找不到 `old_string` 而失败（说明用户在审稿和修改之间手动编辑了 idea.md）：
1. 重新读取当前 idea.md
2. 向用户说明检测到外部修改
3. 基于当前内容重新生成修改方案
4. 重新确认后执行

---

## 步骤 2.5：下一轮决定

AskUserQuestion：
```
第{M}轮修改完成。
(1) 进行下一轮审稿
(2) 结束，idea.md 已满意
```

- 用户选 (1) → M += 1，回到步骤 0.7（新版本快照）→ 步骤 1
- 用户选 (2) → 进入步骤 3

---

## 步骤 3：收尾

### 3.1 Git Checkpoint

```bash
git add structure/0_global/idea.md structure/0_global/idea-refine/
git commit -m "Checkpoint: idea-refine round {M} complete (v{FINAL_VERSION})"
```

### 3.2 完成展示

```
✅ idea-refine 完成

📊 审稿轨迹：
  - 总轮数：{M}
  - 版本变化：v{START} → v{FINAL}
  - 采纳意见：{总采纳数}/{总意见数}

📂 工作目录：structure/0_global/idea-refine/
  {列出所有文件}

{Context (a) 时：}
💡 下一步：开始技术章节开发（步骤④）。开发过程中随时可再次 /idea-refine 重新评估。

{Context (b) 时：}
💡 idea.md 已更新，请继续技术章节开发。注意检查 _dev.md 中是否有内容需要同步调整。
```

---

## 边界条件处理

| 情况 | 处理 |
|:-----|:-----|
| idea.md 不存在或近空 | 停止，提示先创建 |
| idea.md 无版本号字段 | 默认 v0.0，首次修改时新增字段 |
| 无 idea-context/ 目录 | 正常运行，reviewer 上下文更少 |
| method_landscape.md 不存在 | 正常运行，reviewer 跳过此文件 |
| 用户立即选 "done" | 不创建 confirmed/修改文件，只保留快照和 review，进入收尾 |
| lit-pool 之前调用（极早期） | 正常运行，展示 "⚠️ 可用上下文材料有限" 提示 |
| idea-reviewer agent 失败 | 报告错误信息，等待用户指示（不自动重试） |
| Edit 因外部修改失败 | 重新读取、重新生成方案、重新确认 |
| 跨 session 续用 | 工作目录和轮次编号自动续接（基于已有文件 Glob） |
