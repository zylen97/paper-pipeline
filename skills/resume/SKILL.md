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

## 步骤 0.5：项目类型检测

在加载上下文前，先检测当前项目类型：
1. 存在 `structure/` 目录 + `manuscript.tex` → **英文论文项目**（走现有流程）
2. 存在 `chapters/` 目录 + CLAUDE.md 含 `## 撰写进度` → **学位论文项目**
   - 读取 CLAUDE.md 阶段 + 撰写进度表
   - 读取 chapters/*.tex 了解章节结构
   - 读取源项目信息（如有）
3. 存在 `sections/` 目录 + CLAUDE.md 含 `## 章节规划` → **基金项目**
   - 读取 CLAUDE.md 阶段 + 章节规划
   - 读取 sections/*.md 了解撰写进度
4. 都不匹配 → **通用模式**（仅读 CLAUDE.md + git log）

检测到项目类型后，后续步骤按类型分支执行。英文论文项目走步骤 1-8 完整流程；学位论文和基金项目走各自的简化流程（重点读取对应的章节文件和进度信息）；通用模式跳过步骤 2-4，直接读 CLAUDE.md + git log 后输出简述。

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
- `状态: accepted` → 已录用（`accepted` 由用户手动设置，表示论文已被接收，无主动提醒。）

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
git log -15 --date=short --format="%ad %s"
```

了解最近的工作轨迹和节奏。

---

## 步骤 6：修改阶段检测（条件执行）

如果存在 `revision-R*/` 目录或 CLAUDE.md 阶段字段为 `revision-R*`，说明项目处于审稿修改阶段。检测最新轮次目录（如 `revision-R1/`、`revision-R2/`），额外读取：

- `revision-R{N}/comment-letter-clean.md`（审稿意见清单）
- `revision-R{N}/revision-guide.md`（修改策略，如存在）
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

---

## 步骤 8：Proactive 阶段提醒

根据步骤 1 检测到的项目阶段，在简述末尾输出对应的 skill 建议（一句话，非强制）：

- **foundation**：
  - 如果 _dev.md 有实质内容但成稿 md 仍为空 → 建议 `/method-end`
  - 如果技术章节基本成形 → 建议 `/method-audit`
  - 如果 idea.md 近期有较大改动或用户表达不确定 → 建议 `/idea-refine`
  - 否则 → 不输出建议，直接问用户
- **drafting**：
  - 如果叙述型章节 md 为空 → 建议 `/pen-outline`
  - 如果叙述型章节 md 有内容但 tex 对应 section 仍为 TODO → 建议 `/pen-draft`
  - 如果 tex 有正文但未经 polish → 建议 `/pen-polish`
  - 如果所有章节已写入 tex → 建议 `/finalize`
- **submitted**：无主动提醒
- **revision-R{N}**：
  - 如果 response-letter.tex 中有 `[TO BE FILLED]` → 建议 `/rev-respond`
  - 如果 revision-R*/ 目录不存在 → 建议 `/rev-init`

- **学位论文阶段**（项目类型为学位论文时）：
  - **init**：建议 `/diss-init`（如尚未完成初始化）
  - **literature**：建议 `/lit-plan`（文献检索）或 `/lit-review`（文献分析）
  - **drafting**：
    - 如果有章节未 outlined → 建议 `/diss-outline`
    - 如果有章节已 outlined 但未 drafted → 建议 `/diss-draft`
  - **polishing**：
    - 如果有章节已 drafted 但未 polished → 建议 `/diss-polish`
    - 如果所有章节已 polished → 建议 `/diss-finalize`
- **基金项目阶段**（项目类型为基金项目时）：
  - **init**：建议 `/fund-init`（如尚未完成初始化）
  - **literature**：建议 `/lit-plan` 或 `/lit-review`
  - **outlining**：建议 `/fund-outline`
  - **drafting**：建议 `/fund-draft`
  - **reviewed**：建议 `/fund-polish`（评审完成后进入润色）
  - **polishing**：建议 `/fund-polish`（继续润色）

最后一句问用户："需要从哪里继续？"
