---
description: "定稿收尾四步曲：Conclusion → Abstract → Cover Letter → Structure 清理，交互式逐块确认 + language-polisher 润色（Finalize）"
---

# Finalize — 定稿收尾

论文主体完成后的收尾流程，按固定顺序完成四个阶段：

```
Phase 1: Conclusion → Phase 2: Abstract → Phase 3: Cover Letter → Phase 4: Structure 清理
```

Phase 1-3 为写作阶段，独立交互、逐块确认，前一阶段的产出作为后一阶段的输入。Phase 4 为清理阶段，拆除施工脚手架。每个 Phase 完成后 git checkpoint，Phase 4 额外执行 git push。

**输入** `$ARGUMENTS`：可选，指定从哪个阶段开始。示例：
- `/finalize` — 从 Phase 1 开始，完整走四步
- `/finalize abstract` — 从 Phase 2 开始（跳过 Conclusion，适用于 Conclusion 已写好的情况）
- `/finalize cover-letter` — 从 Phase 3 开始
- `/finalize cleanup` — 只做 Phase 4（Structure 清理）

---

## 步骤 0：上下文加载

### 0.1 读取项目配置

- 读取 `CLAUDE.md` → 提取：
  - `{MAIN_TEX}`（主文件路径）
  - `{BIB_FILE}`（bib 文件路径）
  - `{TARGET_JOURNAL}`（目标期刊）
  - `{PUBLISHER}`（出版社）
  - `{METHOD_TYPE}`（modeling / survey-sem / panel-regression）
  - 作者信息（如有）
- 缺少 TARGET_JOURNAL → 停止，提示补全 CLAUDE.md

### 0.2 读取全文上下文

- 读取 `{MAIN_TEX}` 全文 → `{MANUSCRIPT_CONTENT}`
- 读取 `structure/0_global/idea.md` → `{IDEA_CONTEXT}`（RQ、Gap、贡献点、方法框架）
- 读取 `structure/3_methodology/methodology.md` → `{METHOD_CONTEXT}`（不存在则从 `{MANUSCRIPT_CONTENT}` 中提取 Methodology 章节）
- 读取 `structure/4_results/results.md` → `{RESULTS_CONTEXT}`（不存在则从 `{MANUSCRIPT_CONTENT}` 中提取 Results 章节）
- 读取 `structure/5_simulation/simulation.md` → `{SIMULATION_CONTEXT}`（仅 modeling，不存在则从 `{MANUSCRIPT_CONTENT}` 中提取，仍无则跳过）
- 读取 Discussion 对应的 structure md → `{DISCUSSION_CONTEXT}`（Glob `structure/*discussion*/*.md`，不存在则从 `{MANUSCRIPT_CONTENT}` 中提取 Discussion 章节）

> 注：Phase 4 清理后章节 `.md` 不再存在，重跑 finalize 时自动 fallback 到 manuscript.tex 提取。

**空文件检测**：如果 `{RESULTS_CONTEXT}` 为空或仍为 TODO（无论来源是 `.md` 还是 `.tex`）→ 停止，提示先完成论文主体。

### 0.3 读取 Writing Brief

- 读取 `drafts/writing_brief.md` → `{WRITING_BRIEF}`
- 不存在 → 警告但继续

### 0.4 确定起始阶段

根据 `$ARGUMENTS`：
- 空 → 从 Phase 1 开始
- `abstract` → 从 Phase 2 开始，检查 manuscript.tex 中 Conclusion 是否已有内容（非 TODO）
- `cover-letter` → 从 Phase 3 开始，检查 Abstract 是否已有内容
- `cleanup` → 直接跳到 Phase 4（跳过步骤 0.2-0.3 的上下文加载，Phase 4 不需要章节内容）

跳过阶段时，前置内容不存在 → 警告但允许继续。

---

## Phase 1: Conclusion

### 1.1 识别 Conclusion 结构

根据 `{METHOD_TYPE}` 和 idea.md 中的 RQ 数量，确定 Conclusion 的结构模板：

**统一结构（所有方法类型通用）**：

```
Block A: 研究概述（1-2句：这篇研究做了什么——问题+方法+情境）
         紧接过渡句："The conclusions of this paper are as follows."
Block B: 核心发现——按 RQ 组织，用 First/Second/Third 连接
  - First, {对应 RQ1 的核心结论}
  - Second, {对应 RQ2 的核心结论}
  - ...（RQ 数量决定条目数）
Block C: 局限性与未来研究（2-3 个局限 + 对应的未来方向）
```

> 注意：没有单独的"贡献与启示"Block——贡献在 Discussion 中已充分展开，Conclusion 不重复。如果用户要求加，可以在 Block B 之后插入，但默认不加。

### 1.2 逐块交互

**按 Block A → B → C 的顺序，逐块提议 → 用户确认 → 循环。**

对每个 Block：

1. **提议**：基于 `{IDEA_CONTEXT}` + `{RESULTS_CONTEXT}` + `{SIMULATION_CONTEXT}` 的具体内容，生成**中文要点**
2. **用户确认**：AskUserQuestion，循环直到满意
3. **暂存**：记录确认的中文要点，全部 Block 确认后统一转英文

**Block A 示例**：
```
📝 Phase 1 — Conclusion > Block A: 研究概述

提议（1-2句 + 过渡句）：
> {这篇研究做了什么的中文要点}
> 过渡句: "The conclusions of this paper are as follows."

确认？
```

**Block B 示例**（最重要的块，按 RQ 逐条交互）：

对 Block B，**按 RQ 逐条**提议而非一次全部展示：

```
📝 Phase 1 — Conclusion > Block B: 核心发现 > RQ1

RQ1: {RQ1 原文}

提议 First 结论（{N} 个分层要点）：
1. {要点1：从 Proposition X / 核心回归结果 提炼}
2. {要点2：从 Proposition Y / 中介效应 提炼}
3. {要点3：从比较静态/敏感性分析 提炼}

确认这些要点？可以增删改、调整措辞、合并/拆分。
```

确认 RQ1 后继续 RQ2（Second）、RQ3（Third）...

**Block C 示例**：
```
📝 Phase 1 — Conclusion > Block C: 局限性与未来研究

提议 {M} 个局限（每个配一个未来方向）：
1. 局限: {局限1} → 未来: {对应研究方向}
2. 局限: {局限2} → 未来: {对应研究方向}

确认？
```

### 1.3 字数估算

所有 Block 确认后，展示字数预估：

```
📊 Conclusion 字数预估

| Block | 要点数 | 预估字数 |
|-------|--------|---------|
| A: 研究概述 + 过渡句 | — | ~60 |
| B: 核心发现 | {N} RQ × {avg} 要点 | ~{total_B} |
| C: 局限与未来 | {M} | ~{M×50} |
| 合计 | — | ~{total} |

确认？可调整各 Block 比重。
```

### 1.4 生成英文初稿

主 agent 基于确认的中文要点，直接生成英文 LaTeX 内容。

**写作规范**：
- Conclusion 不引用文献（极少数例外：局限性中提及的方法论文献）
- 不重复 Results 的全部细节，只提炼关键发现
- 可引用命题编号（如 "Proposition 1"）、关键数值、效应模式等——但服务于结论陈述，不是堆数据
- Block B 的每条结论对应一个 RQ，用 First/Second/Third 连接，内部可有多个分层要点
- 局限性要诚实但有策略——每个局限后接一个未来研究方向，把"弱点"转化为"机会"

### 1.5 Language Polisher 润色

调用 language-polisher（`subagent_type: "language-polisher"`），prompt 要素：

```
Read `drafts/writing_brief.md` for journal conventions and style guidance.

## Section: Conclusion
## Task: Polish the following academic English text. Improve grammar, coherence, sentence flow, and naturalness while preserving ALL academic content, technical terms, mathematical expressions, and argument structure.

## Text to Polish
{英文初稿}

## Constraints
- Do NOT change any technical content, numbers, or mathematical expressions
- Do NOT add or remove citations
- Do NOT change the argument structure or conclusions
- Target: {TARGET_JOURNAL} style
- Word count: maintain within ±5%
```

### 1.6 用户确认并写入

展示润色后的英文全文。AskUserQuestion：

```
📝 Conclusion 终稿（{WORD_COUNT} 词）

{英文全文预览}

- 确认写入 manuscript.tex → 输入 "ok"
- 修改某处 → 指出具体位置和修改意见
- 重新润色 → 输入 "redo"
```

用户确认 → 用 Edit 工具将内容写入 `{MAIN_TEX}` 的 `\section{Conclusion` 下（替换 TODO 或现有内容）。

### 1.7 Git Checkpoint

```bash
git add -A && git commit -m "finalize: write Conclusion"
```

---

## Phase 2: Abstract

### 2.1 读取 Conclusion

如果 Phase 1 刚完成 → 复用已有内容。
如果从 Phase 2 开始 → 从 `{MAIN_TEX}` 中提取 Conclusion 内容 → `{CONCLUSION_CONTENT}`。

### 2.2 识别 Abstract 结构

Abstract 采用固定的 5 块结构（适用于所有方法类型）：

```
Block 1: Background（研究背景 + 问题，1-2 句）
Block 2: Purpose（研究目的 + 理论框架，1-2 句）
Block 3: Method（方法 + 数据/样本，1-2 句）
Block 4: Findings（核心发现，2-4 句——从 Conclusion Block B 浓缩）
Block 5: Implications（理论/实践价值，1-2 句）
```

### 2.3 逐块交互

按 Block 1 → 2 → 3 → 4 → 5 顺序，逐块提议中文要点 → 用户确认。

格式示例（Block 1）：
```
📝 Phase 2 — Abstract > Block 1: Background

提议：
> {研究背景的中文要点，1-2 句。从 idea.md 的 Gap 中提炼}

确认？可以调整措辞和侧重点。
```

**Block 4 特殊处理**：Findings 从 Phase 1 确认的 Conclusion Block B 中进一步浓缩。展示 Conclusion 的核心发现作为参考，提议更简洁的摘要版本。

### 2.4 字数控制

所有 Block 确认后，展示字数预估：

```
📊 Abstract 字数预估

| Block | 预估字数 |
|-------|---------|
| Background | ~30 |
| Purpose | ~30 |
| Method | ~30 |
| Findings | ~60 |
| Implications | ~30 |
| 合计 | ~180 |

目标期刊 {TARGET_JOURNAL} 的摘要字数限制：{如已知则展示，否则标注"未知，建议 150-250 词"}
```

### 2.5 生成英文初稿

主 agent 基于确认的中文要点，生成英文摘要。

**写作规范**：
- 一段连续文本（不分段、不加小标题）
- 不引用文献
- modeling 类：可包含关键数学结果（如 zy03 摘要中的 $\eta^* \approx 0.572$）
- survey-sem 类：包含样本信息（如 "255 large-scale construction project teams"）
- 结尾落在 implications 或 practical guidance 上，不落在 limitations 上

### 2.6 Language Polisher 润色

调用 language-polisher（`subagent_type: "language-polisher"`），prompt 同 Phase 1 结构，section 改为 "Abstract"。

### 2.7 用户确认并写入

展示润色后的英文摘要。用户确认 → 写入 `{MAIN_TEX}` 的 `\begin{abstract}...\end{abstract}` 之间。

同时提醒用户检查 Keywords（`\begin{keyword}` 或 `\keywords{}`），如果仍为 TODO 则提议 4-6 个关键词供确认。

### 2.8 Git Checkpoint

```bash
git add -A && git commit -m "finalize: write Abstract and Keywords"
```

---

## Phase 3: Cover Letter

### 3.1 读取前置内容

- `{ABSTRACT_CONTENT}`：从 Phase 2 复用，或从 `{MAIN_TEX}` 提取
- `{IDEA_CONTEXT}`：idea.md（贡献点）
- `{WRITING_BRIEF}`：期刊信息

### 3.2 搜索期刊信息

从目标期刊获取：
- **主编姓名** `{EDITOR_NAME}`
- **Aims & Scope 关键方向** `{JOURNAL_SCOPE}`

获取方式：
1. 优先从 `drafts/writing_brief.md` 提取
2. 否则 Web 搜索：`"{TARGET_JOURNAL}" aims scope editor-in-chief`
3. 搜索失败 → `{EDITOR_NAME}` 设为 "Editor"

### 3.3 Cover Letter 结构

参照 xq01 的写法，固定结构：

```
[自动] 称呼（Dear {Professor {EDITOR_NAME} | Editor},）

Block 1: 投稿声明 + 论文概述
  - submit manuscript titled "XXX" for consideration in {JOURNAL}
  - 1-2 句研究背景（问题+情境）
  - 1-2 句方法和关键发现
  - RQ 列表（加粗，如 xq01 格式）

Block 2: 贡献 1 — 与期刊范围的匹配度（Journal Fit）
  - 粗体标题："\textbf{1. Direct relevance to ...}"
  - 说明本研究主题如何匹配期刊 Aims & Scope
  - 引用论文内部具体内容（如 "As shown in Table 1 of the manuscript"）

Block 3: 贡献 2 — 理论推进（Theoretical Advancement）
  - 粗体标题："\textbf{2. Theoretical advancement through ...}"
  - 核心理论贡献，区别于现有研究

Block 4: 贡献 3 — 实践意义（Practical Implications）
  - 粗体标题："\textbf{3. Actionable practical guidance for ...}"
  - 实践层面的价值，引用论文中的具体产出（如 "visualized in Figure 4"）

[自动] 标准结尾（未在他处投稿 + 所有作者同意 + 无利益冲突）+ 署名
```

> 贡献段数量随 idea.md 实际贡献点调整（2-4 段），不强制 3 段。每段的粗体标题应针对论文具体内容定制，不是通用模板。

### 3.4 逐块交互

Block 1-4 逐块提议中文要点 → 用户确认。称呼和标准结尾自动生成，不交互。

格式示例（Block 3）：
```
📝 Phase 3 — Cover Letter > Block 3: 贡献 1 — Journal Fit

参考 idea.md 贡献点 #1：{原文}
参考期刊 Scope：{JOURNAL_SCOPE}

提议：
> {中文要点：本研究的主题如何匹配期刊定位，对期刊读者群的价值}

确认？可以调整侧重点。
```

### 3.5 生成英文全文

主 agent 基于确认的中文要点，生成完整英文 cover letter 正文（`\begin{document}` 到 `\end{document}` 之间的内容）。

**写作规范**：
- 正式学术英文，400-600 词
- 引用论文中的具体内容（"as shown in Table X"、"based on data from N teams"）
- 不使用 "novel"、"first of its kind"、"groundbreaking" 等过度宣称词汇
- 不复述整个摘要——cover letter 是"卖点提炼"
- 使用 "we"，不使用第一人称单数
- 不提及审稿人推荐

### 3.6 Language Polisher 润色

调用 language-polisher（`subagent_type: "language-polisher"`），prompt 同前，section 改为 "Cover Letter"。

### 3.7 用户确认并写入

展示润色后的英文全文。用户确认 → 读取 `submission/coverletter.tex`，保留 LaTeX preamble，替换 `\begin{document}` 到 `\end{document}` 之间的正文内容。

**cover letter 不存在** → 停止，提示先运行 `/paper-init` 或手动创建。
**已有实质内容** → AskUserQuestion 确认覆盖。

编译验证：
```bash
cd submission && latexmk coverletter.tex 2>&1 | tail -20
```

### 3.8 Git Checkpoint

```bash
git add -A && git commit -m "finalize: write Cover Letter"
```

---

## Phase 4: Structure 清理

> Pipeline 的施工脚手架——叙述型章节目录、技术章节 md、`drafts/` 目录——在 manuscript.tex 定稿后不再是 source of truth，保留它们只会制造一致性负担。此阶段拆除脚手架，仅保留 `0_global/`（idea.md + idea-refine/）、`2_literature/`（citation_pool、method_landscape.md 等）、`figures_tables/`，以及技术章节中 `/method-audit` 产出的 `benchmark/` 子目录。

### 4.1 扫描并生成清理清单

扫描 `structure/` 和项目根目录，列出待删除项：

```
🗑️ 即将删除（施工脚手架）：

structure/1_introduction/          ← 叙述型章节，整个目录
structure/*discussion*/            ← 叙述型章节，整个目录（modeling: 6_discussion/, 其他: 5_discussion/）
structure/2_literature/literature.md  ← 叙述型章节 md
structure/3_methodology/*.md        ← 技术章节 md（methodology.md, methodology_dev.md）
structure/3_methodology/_citation_paths.json
structure/4_results/*.md            ← 技术章节 md（results.md, results_dev.md）
structure/4_results/_citation_paths.json
structure/5_simulation/*.md         ← 技术章节 md（仅 modeling，不存在则跳过）
structure/5_simulation/_citation_paths.json
注：技术章节目录中的 benchmark/ 子目录（/method-audit 产出）保留不删
drafts/                            ← 写作中间产物（writing_brief 等，需要时自动重建）

✅ 保留不动：
structure/0_global/                ← idea.md + idea-refine/（迭代审稿轨迹）+ 项目资产
structure/2_literature/（除 literature.md）  ← search plan、direction reports、citation_pool/、method_landscape.md
structure/figures_tables/          ← 图表资产
structure/3_methodology/benchmark/ ← /method-audit 产出（对标论文 + 审计报告），如存在则保留
```

> 注意：只列出实际存在的文件/目录。不存在的项不显示。

### 4.2 用户确认

AskUserQuestion：

```
📋 以上是 Structure 清理清单。

- 确认执行 → 输入 "ok"
- 跳过清理 → 输入 "skip"
- 调整清单 → 指出要保留或额外删除的项
```

用户输入 "skip" → 跳过整个 Phase 4，直接进入步骤 Final。

### 4.3 执行清理

用户确认后，用 Bash 工具逐项删除：

```bash
# 叙述型章节目录（discussion 编号因方法类型而异：modeling=6, 其他=5）
rm -rf structure/1_introduction/
rm -rf structure/*discussion*/

# 叙述型章节 md
rm -f structure/2_literature/literature.md

# 技术章节——只删 md 和临时文件，保留 benchmark/ 等研究资产
rm -f structure/3_methodology/*.md structure/3_methodology/_citation_paths.json
rm -f structure/4_results/*.md structure/4_results/_citation_paths.json
rm -f structure/5_simulation/*.md structure/5_simulation/_citation_paths.json
# 如果技术章节目录删完 md 后只剩空目录（无 benchmark/ 等子目录），则删除空目录
find structure/3_methodology/ structure/4_results/ structure/5_simulation/ -maxdepth 0 -empty -delete 2>/dev/null

# 写作中间产物
rm -rf drafts/
```

### 4.4 Git Checkpoint & Push

```bash
git add -A && git commit -m "chore: clean up structure scaffolding after finalize"
git push
```

---

## 步骤 Final：更新阶段 + 完成提示

在 CLAUDE.md 中查找 `## 项目阶段` 部分：
- 已存在 → 更新 `更新时间: {TODAY}`（状态保持 `drafting` 不变——投稿前终检 `/pre-submit` 完成后才转为 `submitted`）
- 不存在 → 不追加（遗留项目不强制）

```
✅ 定稿收尾完成！

📄 Conclusion: {WORD_COUNT_CONC} 词 → manuscript.tex
📄 Abstract: {WORD_COUNT_ABS} 词 → manuscript.tex
📄 Cover Letter: {WORD_COUNT_CL} 词 → submission/coverletter.tex
🗑️ Structure 清理完成（施工脚手架已拆除）
🚀 已推送至远程仓库

下一步：
- 运行 /pre-submit 做投稿前终检
- 确认 submission/ 目录下所有文件已就绪后投稿
```

---

## 全局约束

### 交互模式
- 每个 Block 都走"提议中文要点 → 用户确认 → 循环"
- 用户可以在任何 Block 输入 "skip" 跳过该块（保留现有内容或 TODO）
- 用户可以在任何 Phase 结束后输入 "stop" 中断流程

### 语言流程
- 交互阶段：中文要点
- 英文生成：主 agent 直接写
- 润色：language-polisher agent
- 写入文件：英文 LaTeX

### 不越界
- Phase 1-3：不修改论文主体（Introduction, Literature Review, Methodology, Results, Discussion），不修改 bib 文件，只写 Conclusion、Abstract、Cover Letter
- Phase 4：只删除指定的脚手架文件，不修改任何保留文件的内容

### 署名信息
Cover letter 中的署名来源优先级：
1. CLAUDE.md 中的作者信息
2. `submission/titlepage.tex` 中的作者信息
3. 都没有 → 保留 TODO 占位符

### 幂等
可以反复运行。每次运行覆盖对应位置的内容。支持从任意 Phase 开始。
