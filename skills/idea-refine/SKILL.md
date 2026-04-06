---
description: "交互式研究idea与方法设计审稿迭代（idea-reviewer审稿 → 用户确认 → 修改idea.md + manuscript.tex → 循环至满意）"
---

# Idea Refine — 交互式 idea + 方法设计 + 技术实现审稿迭代

调用 idea-reviewer agent 对 `idea.md` 和技术实现（_dev.md / chapter md / manuscript.tex）进行多轮审稿，迭代优化研究 idea、方法设计和正文表述，直到用户满意。

**核心特征**：
- **idea + 方法 + 技术实现同步审**：idea 和方法设计是耦合的，审稿人同时评估两者及其技术实现
- **交互式迭代**：reviewer 给出结构化评估 + 编号意见 → **用户逐条确认** → 主 agent 修改 idea.md / manuscript.tex → 可选下一轮
- **阶段感知审查**：自动检测项目状态（开发中 / 章节定稿 / 正文完成），选择最权威的技术素材审查
- **正文同步修改**：reviewer 建议指定 target（idea.md / manuscript.tex / both），主 agent 分别执行
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

- 读取 `CLAUDE.md` → 提取项目编号、目标期刊、方法类型、**项目阶段**（`## 项目阶段`）
- 缺失则警告，但不停止

### 0.2 读取 idea.md

- 读取 `structure/0_global/idea.md`
- 不存在 → **停止**，提示："idea.md 未找到。请先通过 `/idea-mine` 生成或手动创建 idea。"
- 内容 < 100 字符 → **停止**，提示："idea.md 内容过少，请先完善基本内容。"
- 提取版本号（`版本: vX.Y`），缺失则默认 `v0.0`

### 0.3 检测项目技术素材状态

按以下顺序 Glob 检查，确定最高可用状态：

| 状态 | 检查 | 解释 |
|------|------|------|
| State A | `structure/{3,4,5}_*/*_dev.md` 内容 > 500 字符 | 开发中，_dev.md 是工作文档 |
| State B | `structure/{3,4,5}_*/*.md`（非 dev）有实质内容 | method-end 完成或进行中 |
| State C | `manuscript.tex` 的 §3/§4/§5 中**至少一个**有实质正文（非 `% TODO`） | 正文已写，drafting/post-finalize |

**路由规则**：
- State C 存在 → 使用 State C（无论 A/B 是否也存在）
- State C 不存在，A + B 共存 → 使用 State A + B
- State C 不存在，仅 B → 使用 State B only
- State C 不存在，仅 A → 使用 State A only
- 全部不存在 → None

如果 State C 检查不通过（所有技术 section 均为 `% TODO`），降级为 State B 或 A 或 None。

**用户展示**使用最高状态名称（C > B > A > None），**prompt 模板**使用完整组合（见步骤 1.1）。

向用户展示：
```
📍 项目状态：State C — 正文已完成（manuscript.tex 为唯一正本）
```
或
```
📍 项目状态：State A — 开发中（检测到 _dev.md：methodology_dev.md, results_dev.md）
```
或
```
📍 项目状态：State B — 章节定稿中（检测到成稿 md）
```
或
```
📍 项目状态：早期（仅 idea.md 可用，技术素材不足）
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
| method-audit 基准 | `structure/3_methodology/benchmark/*.md` | reviewer 对标方法论竞品 |
| 技术开发文件 | `structure/{3,4,5}_*/*_dev.md` | State A/B 一致性检查 |

向用户展示材料可用性摘要：
```
📦 可用材料：
  ✅ idea.md (v2.3)
  ✅ manuscript.tex (State C)
  ✅ citation_pool/METHOD.md
  ✅ benchmark/cross_comparison.md
  ❌ idea-context/reviews/ — 未找到
  ❌ method_landscape.md — 未找到
  ...
```

如果可用材料极少（只有 idea.md，且为 State None），额外提示：
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

## Project Info
- Project: {项目编号}
- Target journal: {目标期刊}
- Method: {方法类型}
- Project phase: {项目阶段字段，如 foundation/drafting/revision-R1}

## Available Context Materials
{逐条列出 Step 0.4 中标记为 ✅ 的文件的完整绝对路径}

## Project Technical Material State: {State A/B/C/None}

{State A 时：}
## Technical Development Files
Read the following _dev.md files for technical detail:
{列出所有 _dev.md 文件的完整绝对路径}
Check consistency with idea.md, opportunity discovery, assumption revision.

{State B only 时（成稿 md 存在，_dev.md 已清理）：}
## Chapter MD Files
Read the following chapter md files:
{列出所有成稿 md 文件路径}

{State A + B 时（两者共存）：}
## Chapter MD Files (Primary) + Dev Files (Cross-reference)
Read chapter md files as primary:
{列出所有成稿 md 文件路径}
Cross-reference _dev.md for derivation details when needed.

{State C 时：}
## Manuscript (Single Source of Truth)
Read `{manuscript.tex 的完整绝对路径}` — specifically the Methodology,
Results/Equilibrium Analysis, Simulation, Discussion, and Limitations sections.
This is a post-finalize project; manuscript.tex is the authoritative technical source.

{M > 1 时追加：}
## Prior Round Context
This is Round {M}. The following issues were already addressed in prior rounds:
{列出所有 confirmed_r*.md 文件的完整绝对路径}
Do NOT repeat suggestions that were already addressed. Only flag NEW issues,
incompletely fixed issues, or issues that prior fixes introduced (regression check).

## Review Instructions
Follow the review output format defined in your agent instructions:
- Part I: Structured assessments (Dim 5 component audit table, Dim 6 assumption inventory table)
- Part II: Overall assessment (总体评价、最大亮点、最大风险、成熟度判断)
- Part III: Numbered actionable suggestions
Each suggestion must specify target: idea.md, manuscript.tex, or both.
用中文输出。
```

保存审稿意见 → `structure/0_global/idea-refine/review_r{M}.md`

### 1.2 用户确认

将审稿意见展示给用户（先展示 Part II 总体评价作为概览，再展示 Part III 编号建议供逐条选择）：

```
📊 第{M}轮总体评价：
  可发表潜力：{强/中/弱}
  最大亮点：{...}
  最大风险：{...}
  成熟度：{...}

📋 第{M}轮审稿建议（共 N 条）：

1. [§X → target] {issue} → {suggestion}
2. [§X → target] {issue} → {suggestion}
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

基于用户确认的意见，按 target 分组生成**具体修改方案**：

```
📝 修改方案（共 K 条）：

=== idea.md 修改 ===

1. [对应意见#1, §2 Gap]
   当前内容: "G1: 现有研究缺乏对XX的系统分析"
   改为: "G1: 现有研究虽从A和B角度探讨了XX，但未考虑C机制在D情境下的调节作用"

=== manuscript.tex 修改 ===

2. [对应意见#3, §6 Discussion → Limitations 第1段]
   当前内容: "First, the model assumes..."
   改为: "First, the additive defect assumption..."

...
```

AskUserQuestion：确认修改方案，或调整某条的具体内容。

### 2.2 执行修改

用户确认方案后，主 agent 分别执行：

**idea.md 修改**（如有）：
- 使用 Edit 工具逐条修改 `structure/0_global/idea.md`
- **只改方案中列出的内容**，不做额外改动
- 保留 idea.md 的整体结构和格式
- 更新 frontmatter 中的版本号（递增末位；如版本字段缺失则新增）
- 更新 frontmatter 中的日期

**manuscript.tex 修改**（如有）：
- 使用 Edit 工具逐条修改 `manuscript.tex`
- **只改方案中列出的内容**，不改变文档整体结构
- 记录本轮是否修改了 manuscript.tex（用于步骤 3 的 git add）

保存修改后快照（仅 idea.md）→ `structure/0_global/idea-refine/idea_v{NEW}_after_r{M}.md`

### 边界处理：文件被外部修改

如果 Edit 工具因找不到 `old_string` 而失败（说明用户在审稿和修改之间手动编辑了文件）：
1. 重新读取当前文件
2. 向用户说明检测到外部修改
3. 基于当前内容重新生成修改方案
4. 重新确认后执行

---

## 步骤 2.5：下一轮决定

展示 reviewer 的总体评价（如 Part II 中有成熟度判断），然后询问：

```
第{M}轮修改完成。Reviewer 成熟度判断：{reviewer Part II 原文摘录}。
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
```

如果本轮修改了 `manuscript.tex`：
```bash
git add manuscript.tex
```

```bash
git commit -m "Checkpoint: idea-refine round {M} complete (v{FINAL_VERSION})"
```

### 3.2 完成展示

```
✅ idea-refine 完成

📊 审稿轨迹：
  - 总轮数：{M}
  - 版本变化：v{START} → v{FINAL}
  - 采纳意见：{总采纳数}/{总意见数}
  - 修改范围：{idea.md / idea.md + manuscript.tex}

📂 工作目录：structure/0_global/idea-refine/
  {列出所有文件}

{State None / State A 时：}
💡 下一步：开始或继续技术章节开发（步骤④）。开发过程中随时可再次 /idea-refine 重新评估。

{State B 时：}
💡 idea.md 已更新，请继续技术章节开发。注意检查 _dev.md / 成稿 md 中是否有内容需要同步调整。

{State C 时：}
💡 idea.md 和 manuscript.tex 已同步更新。下一步可考虑 /pre-submit 投稿终检。
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
| manuscript.tex 被修改 | git add 时包含 manuscript.tex |
| State C 但所有技术 section 均为 % TODO | 降级为 State B 或 None |
