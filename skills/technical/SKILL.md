---
description: "技术型章节 tex 直通写作（Methodology / Results / Simulation）：基于 /method-audit 输出的写作蓝图 + 正文要点直接生成 tex 句子写入 manuscript.tex。串行调度保证符号一致性。逐 subsection 用户句子级 review。"
---

# Technical Workflow — 技术型章节直通写作

基于 `/method-audit` 输出的 X.md（含 `## 正文要点` + `## 写作蓝图` + `## 必备元素` 三个区块），直接生成英文 tex 句子写入 `manuscript.tex`。**不走"中文要点 → 英文翻译"两步**，避免信息损耗。

**核心原则**：
1. **method-audit 是必经前置**：未通过 `/method-audit` 验收的章节（无 `## 写作蓝图` 区块）→ skill 拒绝执行，提示先跑 `/method-audit`
2. **串行调度**：技术型章节的 subsections 必须**严格按顺序**生成（前序的符号、变量、公式定义影响后序），不允许并行
3. **写作蓝图是核心 prompt**：每个 subsection 的 reader journey、entry/exit、跨章节过渡 直接喂给 sci-writer，决定段落组织
4. **句子级 review**：每个 subsection 生成后让用户逐句审阅，不批量

**与相关 skill 的边界**：
- `/method-audit` = 前置必经：审计 + 结构重组 + 字数分配 + 写作蓝图 + 必备元素验收
- `/narrative` = 处理叙述型章节（intro/LR/discussion），与本 skill 互不重叠
- `/polish` = 后置语言润色，写完 + 人工改完后调用
- `/figure` / `/latex-table` = 图表必须在本 skill 启动前已就位（在 X.md 的 `## 必备元素` 中验收过）

**输入** `$ARGUMENTS`：`section=methodology|results|simulation`（必须）

---

## 步骤 0：前置准备与输入验证

### 0.1 参数解析

提取 `section` 参数。允许值：`methodology` / `results` / `simulation`。

不在范围 → AskUserQuestion 让用户选择。

设置全局变量 `{SECTION_TYPE}` ∈ {`"methodology"`, `"results"`, `"simulation"`}。

### 0.2 项目文件路径

- 从 `CLAUDE.md` 获取 `manuscript.tex` 主文件 + `.bib` + `{METHOD_TYPE}`（modeling / survey-sem / panel-regression）
- 记录 `{TEX_PATH}`、`{BIB_PATH}`、`{METHOD_TYPE}`

**前置检查**：`{METHOD_TYPE}` == survey-sem 或 panel-regression 时，没有 simulation section → 若 `section=simulation` 直接报错退出。

### 0.3 定位 X.md

按 `{SECTION_TYPE}` 找对应的成稿 md：

| section | X.md 路径 |
|:---|:---|
| methodology | `structure/3_methodology/methodology.md` |
| results | `structure/4_results/results.md` |
| simulation | `structure/*simulation*/simulation.md`（仅 modeling 类型） |

不存在 → 报错退出（X.md 是 method-audit 的产出，不应缺失）。

记录 `{X_MD_PATH}`。

### 0.4 输入完整性验证（硬约束）

读取 `{X_MD_PATH}` 检查三个必需区块：

| 区块 | 来源 | 缺失处理 |
|:---|:---|:---|
| `## 正文要点` | method-audit step 5.9.4 | 🔴 BLOCK：未跑 method-audit step 5.9 |
| `## 写作蓝图` | method-audit step 5.7+.4 | 🔴 BLOCK：未跑 method-audit step 5.7+ |
| `## 必备元素` | method-audit step 6.5（验收清单） | ⚠️ 警告但不阻塞（可由用户自填） |

**任一区块缺失** → 显示：
```
🔴 X.md 输入不完整：

缺失区块: {list}
原因: 这些区块由 /method-audit 生成。

建议: 先运行 /method-audit section={SECTION_TYPE}（或全流程），完成结构确认 + 字数分配 + 写作蓝图后再调用 /technical。
```
然后退出。

### 0.5 上下文加载

读取以下源：

1. **`{X_MD_PATH}`** 全文，提取：
   - `## 正文要点`：subsection 列表 + 字数分配表 + 各 subsection 的内容要点
   - `## 写作蓝图`：整体 Reader Journey + 各 subsection 的 5 字段 + 跨章节过渡
   - `## 必备元素`：验收清单（如有）
2. **`structure/0_global/idea.md`** — 全局纲领（理论框架、变量定义、Gap/RQ）
3. **`manuscript.tex` 已有内容** — 提取：
   - 当前 section 已有内容（如有，作为修改基线）
   - **前序 sections** 中已定义的符号 / 变量 / 命题（用于一致性约束）
4. **`structure/2_literature/citation_pool/`** — 引用池（METHOD / DISC 标签为主）
5. **`{BIB_PATH}`** — 验证 citation key 存在性
6. **跨章节符号库**（仅 results / simulation）：
   - 如果 `{SECTION_TYPE}` == "results" → 读 manuscript.tex 的 `\section{Methodology}` 中的所有 `\begin{equation}` / `\begin{align}` / `\begin{proposition}` 等环境，提取符号定义
   - 如果 `{SECTION_TYPE}` == "simulation" → 读 methodology + results 两个 section 的符号库
   - **空符号库 BLOCK**：前序 section 仍为空骨架 → 直接 🔴 BLOCK 退出：
     ```
     🔴 前序 section "{X}" 仍为空骨架。
     技术型章节必须按 methodology → results → simulation 顺序生成。
     请先运行：/technical section={X}
     ```

显示加载状态：
```
📂 上下文加载完成：
- X.md 区块: 正文要点 ✓ | 写作蓝图 ✓ | 必备元素 ✓（完整）/ ⚠️（缺失但可继续）
- subsections: {N} 个
- 总字数目标: {target} 词
- 现有 tex 内容: {N} 字符
- 引用池 METHOD: {K} 条
[仅 results / simulation]:
- 跨章节符号库: {M} 个符号 / {P} 个命题（来自前序 sections）
```

---

## 步骤 1：subsection 列表 + 串行调度计划

### 1.1 解析 subsection 列表

从 X.md `## 正文要点` 区块按 `### {title}` 顺序提取 subsection 列表 → `{SUBSECTIONS}`。

每个 subsection 关联三类信息：
- 字数目标（来自 `## 正文要点` 的字数分配表）
- 写作说明（来自 `## 正文要点` 的 3 列格式）
- 写作蓝图（来自 `## 写作蓝图` 的 5 字段：Entry / Journey / Exit / Order / Anchor）

### 1.2 串行调度计划展示

```
📋 串行调度计划（technical section={SECTION_TYPE}）

按以下顺序逐个生成（不允许并行）:
  1. {subsection 1 title} - {字数} 词 - {一句蓝图摘要}
  2. {subsection 2 title} - {字数} 词 - {一句蓝图摘要}
  ...

跨章节过渡（来自蓝图）:
  - {prev section} → {当前 section}: "{过渡句指南}"
  - {当前 section} → {next section}: "{过渡句指南}"

[仅 results / simulation]:
跨章节符号继承: {N} 个变量将沿用 methodology 定义

预计交互: 每子节 1-2 轮句子级 review。

确认开始？(1) 开始 (2) 取消
```

AskUserQuestion 等待用户确认。

---

## 步骤 2：逐 subsection 串行生成

```
FOR i, subsection IN {SUBSECTIONS}:
  显示 "▶ [{i+1}/{N}]: {subsection title}"

  2.1 收集 subsection 完整 prompt 输入
  2.2 调用 sci-writer agent 生成英文段落
  2.3 显示完整段落 + 引用密度自检
  2.4 用户句子级 review（循环至确认）

  显示 "✓ [{i+1}/{N}] 已确认"
END FOR
```

### 2.1 收集 subsection prompt 输入

为当前 subsection 准备 sci-writer 的完整输入：

**A0. 章节级写作蓝图**（chapter-level 锚点，整章共享）：
- Overall Reader Journey: 整章读者认知路径（来自 X.md 的 `### 整体 Reader Journey`，1-2 句概述）—— 用于锚定首/末 subsection 的 opener / closer
- Cross-chapter Transitions: 与前后章节的衔接句指南（来自 X.md 的 `### 跨章节过渡`），**仅在该 subsection 是当前 section 的首个 / 末个时注入**

**A. 写作蓝图 5 字段（subsection 级）**：
- Reader Entry Point: 读者此时已知什么
- Content Journey: 本节单一观点
- Exit Point: 读者离开时记住什么
- Why This Order: 为什么这个位置
- Visual Anchor: 配图/表锚点

**B. 字数 + 写作说明**：
- 目标字数: {N} 词
- 风格指导: 来自 `## 正文要点` 的写作说明

**C. 内容素材**：
- 该 subsection 的"内容要点"（来自 X.md `### {title}` 下的列表）
- 必备元素清单（公式 / 命题 / 假设 / 证明骨架 / 变量定义 / 表图标注）

**D. 跨章节继承**（仅 results / simulation）：
- 前序 sections 中已定义的符号 / 变量 / 命题（必须沿用，不得重定义）

**E. 跨章节过渡**：
- 如果是当前 section 的**第一个** subsection → 加入 `{prev section} → {当前 section}` 过渡句指南
- 如果是当前 section 的**最后一个** subsection → 加入 `{当前 section} → {next section}` 过渡句指南

**F. 已生成的前序 subsections**（本次 skill 运行内）：
- 第一个 subsection 跳过此项
- 后续 subsection 接收前序 subsections 的英文段落作为术语/符号一致性上下文

**G. 引用池**：
- METHOD 标签的 citation_pool 条目（按子节内容相关性排序）
- 引用形式标记 `[citep]/[citet]/[—]` 内部使用

### 2.2 调用 sci-writer agent

调用 sci-writer subagent，传递 2.1 的所有输入。**Prompt 关键约束**：

```
1. **Granularity**: 段落级生成，每段 4-8 个英文句子，遵循 Visual Anchor 的位置安排
2. **符号一致性**: 任何变量/符号若在前序 sections 已定义，必须沿用同一记号；不得使用替代符号
3. **必备元素**: X.md `## 必备元素` 中标记的元素（如 Proposition/Lemma/Equation）必须在适当位置出现
4. **Reader Journey 双层对齐**:
   - 章节级：开篇句锚定 Overall Reader Journey 的入口（仅首 subsection），末段呼应 Overall Reader Journey 的出口（仅末 subsection）
   - subsection 级：段落组织顺序必须符合 Entry → Journey → Exit 的认知路径
5. **跨章节过渡**: 首 subsection 的开篇段融入 prev→current 过渡句指南；末 subsection 的收尾段融入 current→next 过渡句指南
6. **引用规则**:
   - 仅使用 citation_pool METHOD 标签的 keys
   - 每个 \citep / \citet 必须在 bib 中验证存在
   - 技术型章节引用密度通常 30-60%（远低于叙述型，因为大部分是本文方法陈述）
7. **LaTeX 环境正确**: 公式用 $...$ 或 \begin{equation}; 命题用 \begin{proposition}\label{prop:X}...\end{proposition}; 表用 \begin{table}; 图用 \begin{figure}
```

sci-writer 输出英文段落（含完整 LaTeX 标记）。

### 2.3 引用密度自检

统计当前 subsection 段落：
- `density` = 含 `\citep` 或 `\citet` 的句子数 / 总句子数

技术型章节**没有 85% 强约束**，但显示密度供用户参考。

**符号一致性检查**：
- 提取段落中所有用 $...$ 包围的数学符号
- 与前序 sections 的符号库比对
- 不一致 → ⚠️ 警告（如 "x_t 在 methodology 已定义为 ...，本段使用 X(t) 表示同一变量？"）

### 2.4 用户句子级 review

```
### {subsection title}

[完整英文段落，含 LaTeX 标记]

📊 字数: {actual} / {target} 词 ({±%})
📊 引用密度: {density}%
🔬 必备元素检查: {present}/{required} 已包含
[如有] ⚠️ 符号一致性警告: {list}
[如有] ⚠️ 字数偏差: 实际比目标多/少 {N} 词

确认 / 修改某句 / 整段重写？
(1) 确认进入下一子节
(2) 修改具体句子（"第 N 句改成..." 或 "第 N-M 句改为..."）
(3) 重新生成整段
(4) 调整引用
```

AskUserQuestion 句子级 review。

**循环**：用户不满意 → 主 agent 直接修改对应句子（或重新调用 sci-writer 整段重写）→ 再展示 → 直到确认。选 (4) 调整引用后回到 2.3 重新自检再展示。

---

## 步骤 3：跨章节一致性扫描（写入前）

所有 subsections 确认完毕后，在写入 tex **之前**做一次全 section 一致性扫描：

### 3.1 符号一致性

扫描本次生成的所有 LaTeX 数学环境（`\begin{equation}` / `\begin{align}` / `$...$` 等），对每个声明式定义（如 `Let $x_t$ denote...`）提取"变量名 → 记号"映射，与前序 sections 符号库比对。

冲突类型：
- 同一变量名，记号不同 → 标记冲突
- 不同变量名，记号相同 → 标记符号重载风险

发现冲突 → ⚠️ 列出 + AskUserQuestion：

```
⚠️ 跨章节符号冲突 ({N} 项):
  1. 变量"goodwill"在 methodology 用 $G_t$，在本次生成的 results 用 $\Gamma(t)$
  ...

(1) 统一为前序 sections 的记号（推荐）
(2) 用户指定统一记号
(3) 忽略，继续写入
```

选 (1)/(2) → 主 agent 在内存中对当前段落字符串做替换 → 重新扫描，直至冲突清零。
选 (3) → 直接进入 3.2，但 4.1 写入前最终确认中标注"⚠️ 已忽略 {N} 项符号冲突"。

### 3.2 命题/引理编号衔接

如果 `{SECTION_TYPE}` == "results"：
- 前序 methodology 中已有 Proposition 1, Lemma 1 等 → results 的命题从下一编号开始
- 检查本次生成的 `\begin{proposition}` 是否正确编号

发现编号冲突 → 自动修复 + 报告用户。

### 3.3 引用池一致性

检查本次生成的所有 `\citep` / `\citet` keys：
- 是否在 citation_pool METHOD 标签中？（不在的标记为"用户手动添加"）
- 是否在 `{BIB_PATH}` 或 `master.bib` 中？

不存在的 key → ⚠️ 警告但不阻塞（标记为 (ref) 占位）。

---

## 步骤 4：写入 manuscript.tex

### 4.1 写入前最终确认

```
📝 即将写入 {TEX_PATH} 的 \section{{SECTION_TYPE}}：

总字数: {N} 词（目标: {target} 词，偏差 {±%}）
subsections 数: {M}
总引用: {N_citep} \citep + {N_citet} \citet
新增 bib keys: {list}

子节预览（每节首句）:
  - {sub 1}: "{首句..."}"
  - {sub 2}: "{首句..."}"
  ...

跨章节一致性: {符号 ✓ | 命题编号 ✓ | 引用 ✓}

确认写入？(1) 写入 (2) 回退到某子节修改 (3) 取消
```

AskUserQuestion 等待用户最终确认。

### 4.2 写入

用户确认后：

1. 用 Edit 工具替换 `manuscript.tex` 中 `\section{{SECTION_TYPE_TITLE}}` 至**结束位置**之间的内容。结束位置 = 下一个 `\section`（含 `\appendix` 之后的）/ `\appendix` / `\bibliography{...}` / `\printbibliography` / `\end{document}` 中**最先出现的一行的前一行**
2. **保留** `\section{...}` 行本身和 `\label{...}`（如有）
3. 写入新内容（含 `\subsection{}` / `\subsubsection{}` / `\begin{equation}` / `\begin{proposition}` / `\begin{table}` / `\begin{figure}` / `\citep{}` / `\citet{}`）

### 4.3 bib 同步

写入 tex 后，立即同步 bib：

1. 提取本次写入的所有 `\citep{...}` / `\citet{...}` keys → 去重
2. 检查每个 key 是否已在 `{BIB_PATH}` 中
3. 不在的 → 从 `master.bib` 提取条目，追加到项目 bib 末尾
4. master.bib 也找不到 → 标记 ⚠️

显示同步结果：
```
📚 bib 同步: 共 {N} 个 keys，新增 {M} 条到项目 bib
[如有] ⚠️ 找不到的 keys: {list}（标记为 (ref) 占位，需后续手动补充）
```

---

## 步骤 5：完成提示

```
✅ /technical section={SECTION_TYPE} 完成

📊 写入摘要:
- {section title}: {N} 词
- subsections: {M} 个
- 总引用: {citep} \citep + {citet} \citet
- 新增 bib: {K} 条
- 必备元素: {present}/{required} 已包含

🔗 跨章节一致性:
- 符号沿用前序 sections: {N} 个 ✓
- 命题编号衔接: ✓
- 引用池一致: ✓

💡 后续推荐流程（基于 {METHOD_TYPE}）:

  /narrative 的三个 section 推荐分两批跑：

  **第一批（不依赖 results，可在 /technical 进行中或完成后任意顺序跑）**：
  - /narrative section=introduction
  - /narrative section=literature

  **第二批（必须等 results 完成后）**：
  - /narrative section=discussion ← 🔴 硬约束：results 未完成时 /narrative 步骤 3.1 会 BLOCK 退出

  按 {METHOD_TYPE} 的"全部技术型完成"标准：
  - **modeling**: methodology ✓ + results ✓ + simulation ✓ → 可跑 discussion
  - **survey-sem / panel-regression**: methodology ✓ + results ✓ → 可跑 discussion

- 你可以在 manuscript.tex 中亲自再改一轮
- 改完后可调用 /polish 做语言润色
- 所有 sections 完成 → /finalize 收尾
```

---

## 共享约束

### sci-writer agent 的硬约束（写入 prompt）

1. **不发明符号**：所有数学符号必须来自 X.md `## 必备元素` 或前序 sections
2. **不跳过必备元素**：X.md `## 必备元素` 中的公式/命题/假设必须在段落中出现
3. **遵守 Reader Journey**：段落组织必须符合 Entry → Journey → Exit
4. **遵守字数**：偏差 ≤ ±15%
5. **引用形式区分**：`\citep` 用于括号引用支撑性陈述，`\citet` 用于以作者为主语的具体发现
6. **不写无支撑的"业内共识"**：如需声明"prior work has established X"，必须配 `\citep`
7. **段落首尾留过渡**：首段引出，末段衔接下一 subsection（如有跨章节过渡指南，遵循之）

### 失败模式

| 失败 | 处理 |
|:---|:---|
| `## 写作蓝图` 缺失 | 步骤 0.4 BLOCK，提示先跑 method-audit |
| 前序 section 空骨架 | 步骤 0.5 BLOCK |
| sci-writer 输出字数严重偏差（>±30%）| 自动重新调用 + 调整 prompt |
| 符号冲突无法自动解决 | AskUserQuestion 让用户手动决定 |
| Citation key 缺失 | 标记 (ref) 占位 + 警告，不阻塞 |

### 与 /narrative 的协调

- /technical 处理 methodology / results / simulation
- /narrative 处理 introduction / literature / discussion
- 两者**互不重叠**，但通过 manuscript.tex 共享上下文（discussion 必读 results 才能写好）

### 与 /polish 的接力

`/technical` 写出的 tex 段落可调 `/polish` 做语言润色，但 polish 必须**保护 citation 和 LaTeX 环境**：
- 不增删 \citep / \citet 的 keys
- 不修改 \begin{equation} / \begin{proposition} / \begin{table} 等环境内的内容
- 仅润色非环境内的散文部分

---

## 设计原则备忘

1. **method-audit 是前置硬约束**——没有写作蓝图不让写
2. **串行不并行**——技术型符号一致性必须保证
3. **写作蓝图是核心 prompt**——5 字段 + 跨章节过渡决定段落组织
4. **跨章节符号继承**——results / simulation 必须沿用 methodology 定义
5. **引用密度无 85% 约束**——技术型章节本身少引用是常态
6. **句子级 review**——和 /narrative 一致，最后人工把关在句子粒度
