---
description: "新 session 快速加载项目上下文，让 Claude 立即进入工作状态（Project Context Loader）"
---

# Resume — 项目上下文加载

在新会话开始时快速读取项目关键文件，生成一段简洁的项目简述，让 Claude 立即理解"这篇论文在干嘛、做到哪了"，无需用户反复解释。

**输入** `$ARGUMENTS`：无参数。直接运行 `/resume`。

---

## 步骤 0：前置检查

确认当前目录存在 `CLAUDE.md`。不存在 → 停止，提示用户切换到论文项目根目录。

---

## 步骤 1：读取项目元数据

`CLAUDE.md` 已自动加载，从中提取：

- 项目编号、英文标题、一句话概括
- 方法、目标期刊、模板类型
- structure/ 的目录结构表（确认有哪些章节目录）

### 阶段字段快速定位

优先读取 CLAUDE.md 的 `## 项目阶段` 部分（如存在）：
- `状态: foundation` → idea + 文献 + 技术型章节开发阶段（pipeline ①-⑤.5）。重点看 structure/ 中的 _dev.md 进展、idea.md 版本、citation pool 是否就绪
- `状态: drafting` → 叙述型章节撰写 + 全文定稿阶段（pipeline ⑥-⑨）。重点看各章节 md 和 manuscript.tex 的填充进度
- `状态: submitted` → 已投稿，等待审稿
- `状态: revision-R{N}` → 第 N 轮修改（额外读取基准文件名和轮次历史）
- `状态: accepted` → 已录用

如果有阶段字段，后续步骤可以有的放矢：foundation 阶段重点看 _dev.md 和 idea.md，drafting 阶段重点看章节 md 和 manuscript.tex，revision 阶段重点看 revision/。如果没有阶段字段（遗留项目），按原有逻辑从文件扫描推断。

---

## 步骤 2：读取研究纲领

读取 `structure/0_global/idea.md` **全文**，重点关注：

- 版本号（`> **版本**: vX.X`）
- §2 的 Gap → Objective → RQ 表格
- §3 方法论选择
- §4 预期贡献

这是整个项目的灵魂文件，必须完整理解。

---

## 步骤 3：快速浏览各章节 md

对 structure/ 下**除 idea.md 之外**的每个章节 md，读取**前 50 行**。目的不是精细判定完成度，而是快速知道：

- 这个章节有没有开始写
- 大致在写什么内容
- 叙述型章节（introduction/literature/discussion）的大纲是否已填充
- 技术型章节（methodology/results 等）：优先检查**成稿 md**（X.md）是否有实质内容（非 TODO）；同时检查**过程文件**（X_dev.md）是否存在及内容量，判断研究进展阶段

> **清理后状态识别**：如果 `structure/1_introduction/` 目录不存在且 `drafts/` 目录不存在，说明已完成 `/finalize` Phase 4 清理。此时跳过本步骤，在步骤 4 中直接从 `manuscript.tex` 判断所有章节的完成状态，并在输出中注明"已完成定稿清理，manuscript.tex 为唯一正本"。

同时注意 `2_literature/` 目录下的文献系统产物：
- 是否有 `literature_search_plan.md`（检索规划）
- 是否有 `citation_pool/` 目录（引用池）
- 是否有 `direction*_report.md`（方向报告）

---

## 步骤 4：浏览 manuscript.tex

用 Grep 搜索 `manuscript.tex` 中所有 `\section` 和 `\subsection`，对每个 section 检查其内容是 `% TODO` 还是有实质正文。

目的：知道哪些章节已经从 md 转译到了 tex。

---

## 步骤 5：Git 历史

运行：

```bash
git log --oneline -15 --date=short --format="%ad %s"
```

了解最近的工作轨迹和节奏。

---

## 步骤 6：修改阶段检测（条件执行）

如果存在 `revision/` 目录或 CLAUDE.md 阶段字段为 `revision-R*`，说明项目处于审稿修改阶段，额外读取：

- `revision/comment-letter-clean.md`（审稿意见清单）
- `revision/revision-guide.md`（修改策略，如存在）
- `.revision-baseline`（如存在，读取当前基准文件名以确认轮次）
- 扫描 `revision-R*/` 目录（如存在，统计历史轮次数）
- `response-letter.tex` 中 `[TO BE FILLED]` 数量 → 计算完成进度

如果检测到多轮历史（如 `revision-R1/` 目录存在），在输出中说明当前是第几轮、上一轮完成了多少条。

---

## 步骤 7：输出项目简述

用自然语言输出一段**项目上下文简述**，包含：

1. **项目概况**：一两句话说清楚这篇论文在研究什么、用什么方法、投什么期刊
2. **研究问题**：列出 RQ（从 idea.md 提取）
3. **当前进度**：哪些部分有了、哪些还没开始，manuscript.tex 写到哪了
4. **最近动态**：从 git log 提炼最近在做什么（不要罗列 commit，用自然语言概括）
5. **如果在修改阶段**：简述审稿意见的大致情况

**要求**：
- 简洁，不超过 500 字
- 用中文
- 不要输出表格、不要状态标记符号，就是一段让人（和 Claude）看完就能干活的文字
- 最后一句问用户："需要从哪里继续？"
