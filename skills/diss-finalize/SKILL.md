---
description: "学位论文定稿收尾：中英文摘要 + 致谢 + 独创性声明 + 格式终检（页眉页脚、图表编号、参考文献格式）"
---

# Diss-Finalize — 学位论文定稿收尾

学位论文所有章节完成并打磨后的最终收尾流程，按固定顺序完成七个阶段：

```
Phase 1: 中文摘要 → Phase 2: 英文摘要 → Phase 3: 致谢 → Phase 4: 独创性声明 → Phase 5: 格式终检 → Phase 6: 编译验证 → Phase 7: 更新项目阶段
```

Phase 1-2 为写作阶段，Phase 3-4 为模板阶段，Phase 5-6 为检查阶段。每个 Phase 完成后 git checkpoint。

**输入** `$ARGUMENTS`：可选，指定从哪个阶段开始。示例：
- `/diss-finalize` — 从 Phase 1 开始，完整走七步
- `/diss-finalize abstract-en` — 从 Phase 2 开始（跳过中文摘要）
- `/diss-finalize ack` — 从 Phase 3 开始
- `/diss-finalize declaration` — 从 Phase 4 开始（独创性声明）
- `/diss-finalize check` — 从 Phase 5 开始（只做格式终检 + 编译验证）

---

## 步骤 0：上下文加载

### 0.1 读取项目配置

- 读取项目 `CLAUDE.md` → 提取：
  - `{DEGREE_TYPE}`（本科 / 硕士 / 博士）
  - `{MAIN_TEX}`（主文件路径，如 `main.tex` 或 `main-thesis.tex`）
  - `{BIB_FILE}`（bib 文件路径）
  - `{SOURCE_PROJECT}`（源英文小论文项目路径）
  - `{SCHOOL}`（学校名称）
  - `{TITLE_ZH}`（中文题目）
  - `{TITLE_EN}`（英文题目）
  - 章节结构与字数分配表
- 缺少关键字段 → 停止，提示补全 CLAUDE.md

### 0.2 读取全文内容

- 编译一次 `{MAIN_TEX}`，确认当前可编译通过
- 读取所有 `chapters/*.tex` → `{FULL_CONTENT}`（按章节顺序拼接）
- 读取源英文论文的 Abstract → `{EN_PAPER_ABSTRACT}`（如源项目存在）
- 读取源英文论文的 `idea.md` → `{IDEA_CONTEXT}`（RQ、Gap、贡献点）

### 0.3 确定起始阶段

根据 `$ARGUMENTS`：
- 空 → 从 Phase 1 开始
- `abstract-en` → 从 Phase 2 开始，检查中文摘要是否已有内容
- `ack` → 从 Phase 3 开始
- `declaration` → 从 Phase 4 开始
- `check` → 从 Phase 5 开始（跳过 0.2 的全文读取，Phase 5 直接检查 tex 文件）

### 0.4 前置门禁检查

在正式开始前，检查章节完成状态：

1. **骨架残留扫描**：扫描所有 `chapters/*.tex`，检查是否存在残留的骨架注释（`% 目标字数：`、`% 内容来源：`、`% Guidelines:`），存在则列出文件和行号
2. **进度状态检查**：读取 CLAUDE.md 撰写进度，检查是否有 `pending` 或 `skipped` 状态的章节
3. **判定**：
   - 发现未完成章节 → 展示清单 + 警告，用户选择：
     - [1] 继续 finalize（跳过门禁，最终报告中标注"部分章节未完成"）
     - [2] 中断，先用 `/diss-draft` 完成对应章节
   - 全部通过 → 正常继续

---

## Phase 1: 中文摘要

### 1.1 定位摘要文件

按优先级查找中文摘要文件：
1. `front/abstract_zh.tex`
2. `front/abstract.tex`（如果同时包含中英文摘要区域）
3. `chapters/abstract.tex`
4. `{MAIN_TEX}` 中内联的 `\begin{cnabstract}` 或 `\begin{abstract}` 环境

找到 → `{ABSTRACT_ZH_FILE}` + `{ABSTRACT_ZH_ENV}`（环境名称）
未找到 → 停止，提示用户指定摘要文件位置

### 1.2 生成中文摘要要点

基于 `{FULL_CONTENT}` 和 `{IDEA_CONTEXT}`，按以下结构提议中文摘要要点：

```
Block A: 研究背景（1-2句）
  → 行业/领域现状 + 现有研究不足（Gap）

Block B: 研究方法（1-2句）
  → 本文采用什么方法 + 研究对象/数据来源

Block C: 主要发现（2-4句）
  → 按 RQ 顺序，凝练核心结论

Block D: 研究意义（1-2句）
  → 理论贡献 + 实践价值
```

### 1.3 逐块交互

按 Block A → B → C → D 顺序，逐块提议 → 用户确认 → 循环。

格式示例：
```
Phase 1 — 中文摘要 > Block A: 研究背景

提议：
> {中文要点，1-2句}

确认？可以调整措辞和侧重点。
```

### 1.4 生成中文摘要全文

所有 Block 确认后，生成完整中文摘要。

**写作规范**：
- 总字数约 500 字（400-600 字均可）
- 一段连续文本，不分段、不加小标题
- 使用第三人称或无主语句式（"本文提出..."、"研究表明..."）
- 不引用文献编号
- 语言简洁精炼，避免口语化

### 1.5 关键词

提议 3-5 个中文关键词，用分号分隔。

关键词选取原则：
- 覆盖研究领域、方法、核心概念
- 避免过于宽泛（如"管理"）或过于狭窄
- 参考源英文论文的 Keywords 对应翻译

### 1.6 用户确认并写入

展示完整中文摘要 + 关键词：

```
Phase 1 — 中文摘要终稿（{CHAR_COUNT} 字）

{中文摘要全文}

关键词：{KW1}；{KW2}；{KW3}；{KW4}

- 确认写入 → 输入 "ok"
- 修改 → 指出具体位置和修改意见
```

用户确认 → 写入 `{ABSTRACT_ZH_FILE}`。

### 1.7 Git Checkpoint

```bash
git add -A && git commit -m "diss-finalize: write Chinese abstract"
```

---

## Phase 2: 英文摘要

### 2.1 定位摘要文件

按优先级查找英文摘要文件：
1. `front/abstract_en.tex`
2. `front/abstract.tex`（英文摘要区域）
3. `chapters/abstract.tex`（英文摘要区域）
4. `{MAIN_TEX}` 中内联的 `\begin{enabstract}` 环境

找到 → `{ABSTRACT_EN_FILE}` + `{ABSTRACT_EN_ENV}`

### 2.2 生成英文摘要

基于两个输入源生成英文摘要：
- **Phase 1 确认的中文摘要**（内容结构）
- **`{EN_PAPER_ABSTRACT}`**（源英文论文摘要，语言风格参考）

如果源英文论文摘要不可用 → 仅基于中文摘要翻译+润色。

**写作规范**：
- 总词数约 300 词（250-350 词）
- 一段连续文本，不分段
- 与中文摘要内容一一对应，但非直译——英文表达习惯优先
- 可复用源英文论文摘要中的术语和表达方式
- 结尾落在研究意义上

### 2.3 逐块交互

展示英文摘要初稿，标注与中文摘要各 Block 的对应关系：

```
Phase 2 — English Abstract（{WORD_COUNT} words）

[Block A → Background] {英文句子}
[Block B → Method] {英文句子}
[Block C → Findings] {英文句子}
[Block D → Significance] {英文句子}

确认？可以逐句修改。
```

### 2.4 英文关键词

基于中文关键词 + 源英文论文 Keywords，提议 3-5 个英文关键词。

### 2.5 用户确认并写入

用户确认 → 写入 `{ABSTRACT_EN_FILE}`。

### 2.6 Git Checkpoint

```bash
git add -A && git commit -m "diss-finalize: write English abstract"
```

---

## Phase 3: 致谢

### 3.1 定位致谢文件

按优先级查找：
1. `back/acknowledgement.tex`
2. `chapters/acknowledgement.tex`
3. `back/thanks.tex`
4. `chapters/thanks.tex`

找到 → `{ACK_FILE}`
未找到 → 提示用户指定，或在最可能的位置创建

### 3.2 生成致谢骨架

**致谢为高度个人化的内容，本 skill 只提供结构化模板，由学生自行填写。**

生成模板：

```latex
\chapter*{致谢}
% ===== 请根据个人实际情况填写，以下为结构建议 =====

% 第一段：导师（必写）
% 感谢导师XXX教授在学术研究、论文写作等方面的悉心指导...
% 提及具体帮助：选题指导、方法论建议、论文修改等

% 第二段：课题组/实验室（可选）
% 感谢课题组其他老师和同学的帮助与支持...

% 第三段：家人与朋友（建议写）
% 感谢家人的理解与支持...

% 第四段：其他致谢（可选）
% 如：基金资助、数据提供方、企业合作方等

% 最后：署名 + 日期
% XXX
% 20XX年X月于苏州
```

### 3.3 展示并确认

```
Phase 3 — 致谢

已生成致谢模板骨架，包含注释指引。
致谢内容高度个人化，请你自行填写真实感受。

写入 {ACK_FILE} ？
- 确认写入模板 → 输入 "ok"
- 已有内容，跳过 → 输入 "skip"
```

### 3.4 Git Checkpoint

```bash
git add -A && git commit -m "diss-finalize: add acknowledgement template"
```

---

## Phase 4: 独创性声明与使用授权声明

中国学位论文必须包含「独创性声明」和「学位论文使用授权声明」页面，通常位于封面之后、摘要之前。

### 4.1 检查模板是否已内置声明页

扫描 `.cls` 文件和 `{MAIN_TEX}`，查找是否已有声明页命令：
- 常见命令：`\makedeclaration`、`\declaration`、`\makeoriginalitystatement`、`\originality`
- 或已内联的 `独创性声明` / `原创性声明` 文本块

**判定**：
- 模板已内置 → 跳到 4.3（仅验证编译正确）
- 模板未内置 → 进入 4.2 生成声明页

### 4.2 生成声明页内容

在适当位置（`front/declaration.tex` 或 `{MAIN_TEX}` 的前言区域）生成标准声明页：

```latex
\chapter*{独创性声明}

本人声明所呈交的学位论文是我个人在导师指导下进行的研究工作及取得的研究成果。据我所知，除文中已经标明引用的内容外，本论文不包含其他个人或集体已经发表或撰写过的研究成果。对本文的研究做出重要贡献的个人和集体，均已在文中以明确方式标明。本声明的法律结果由本人承担。

\vspace{2cm}

\noindent 论文作者签名：\underline{\hspace{4cm}} \hfill 日期：\underline{\hspace{3cm}}

\vspace{4cm}

\chapter*{学位论文使用授权声明}

本人完全了解{SCHOOL}关于收集、保存、使用学位论文的规定，即：学校有权保留学位论文的复印件，允许被查阅和借阅；学校可以公布学位论文的全部或部分内容，可以采用复印、缩印或其他复制手段保存学位论文。

保密的学位论文在解密后适用本声明。

\vspace{2cm}

\noindent 论文作者签名：\underline{\hspace{4cm}} \hfill 导师签名：\underline{\hspace{4cm}}

\noindent 日期：\underline{\hspace{3cm}} \hfill 日期：\underline{\hspace{3cm}}
```

**注意**：以上为通用模板文本。如用户学校（`{SCHOOL}`）有官方指定措辞，应以学校版本为准。向用户确认是否需要调整措辞。

### 4.3 验证声明页编译

编译 `{MAIN_TEX}`，检查：
- 声明页是否正常渲染（无编译错误）
- 声明页位置是否正确（封面之后、摘要之前）
- 页面格式是否符合要求（无页眉页脚、无页码，或按学校要求）

### 4.4 用户确认

```
Phase 4 — 独创性声明

{模板已内置 → "模板 .cls 已包含声明页命令，编译验证通过。"}
{手动生成 → "已生成独创性声明 + 使用授权声明，写入 {DECLARATION_FILE}。"}

声明页内容为标准模板，提交前需手写签名。
确认？
```

### 4.5 Git Checkpoint

```bash
git add -A && git commit -m "diss-finalize: add originality declaration"
```

---

## Phase 5: 格式终检

### 5.1 图表编号连续性检查

扫描所有 `chapters/*.tex`，检查：

- `\label{fig:X-Y}` / `\label{tab:X-Y}` 的编号是否与章节对应
- `\ref{fig:...}` / `\ref{tab:...}` 是否都有对应 `\label`
- 是否存在未被引用的图表（有 `\label` 但全文无 `\ref`）
- 图表标题格式：`图X-Y` / `表X.Y`（或英文 `Figure X.Y` / `Table X.Y`，取决于模板设定）
- 编号是否连续（不跳号）

输出检查报告：
```
Phase 5.1 — 图表编号检查

[PASS] 图编号连续性：共 {N} 张图，编号连续
[WARN] 表3.2 未在正文中引用（chapters/ch3.tex L120）
[FAIL] \ref{fig:4-3} 找不到对应 \label（chapters/ch4.tex L85）
```

### 5.2 参考文献格式检查（GB/T 7714-2015）

检查 `{BIB_FILE}` 和编译产物：

- bib 条目的必填字段是否完整（author, title, year, journal/booktitle）
- 是否使用了 GB/T 7714 兼容的 bst/biblatex 样式
- 编译 log 中是否有 `Citation undefined` 或 `Empty bibliography` 警告
- 正文中 `\cite` 命令格式是否统一（`\cite{key}` vs `\citep{key}` vs `\parencite{key}`）

### 5.3 页眉页脚检查

检查 `.cls` 文件和 `{MAIN_TEX}` 中的页眉页脚设置：

- 奇数页页眉：章标题（或学校要求的格式）
- 偶数页页眉：论文题目（或学校要求的格式）
- 页脚：页码居中
- 摘要、目录页的页眉页脚是否符合要求（通常为空或罗马数字页码）

### 5.4 目录检查

编译后检查 `.toc` 文件：

- 目录层级是否正确（章 → 节 → 小节）
- 目录中标题与正文标题是否一致
- 页码是否正确（无 "??" 或 "0"）
- 目录是否包含不应出现的内容（如致谢、附录标题格式）

### 5.5 字体字号检查

检查 `.cls` 和 `{MAIN_TEX}` 中的字体设置：

- 正文：宋体/Times New Roman，小四号（12pt）
- 章标题：黑体，三号（16pt）或按学校要求
- 节标题：黑体，四号（14pt）或按学校要求
- 摘要标题、关键词：按学校模板要求
- 是否正确加载了中文字体包（ctex / xeCJK）

### 5.6 页边距检查

检查 `.cls` 或 `{MAIN_TEX}` 中的 geometry 设置：

- 上下左右边距是否符合学校要求（常见：上2.5cm，下2.5cm，左3cm，右2cm）
- 装订线是否设置

### 5.7 行距检查

- 正文行距：1.5 倍行距（`\linespread{1.5}` 或 `\onehalfspacing`）
- 脚注、表格内容等是否为单倍行距

### 5.8 格式检查汇总

汇总所有检查结果：

```
Phase 5 — 格式终检报告

| 检查项 | 状态 | 详情 |
|--------|------|------|
| 图表编号 | PASS | 共 12 图 8 表，编号连续 |
| 参考文献 | WARN | 2 条 citation undefined |
| 页眉页脚 | PASS | 符合模板设定 |
| 目录 | PASS | 三级目录正确 |
| 字体字号 | PASS | CTeX 配置正确 |
| 页边距 | PASS | geometry 设置符合要求 |
| 行距 | PASS | 1.5 倍行距 |

FAIL: 0 | WARN: 1 | PASS: 6
```

- FAIL 项 → 逐条展示问题 + 修复方案，AskUserQuestion 确认后修复
- WARN 项 → 展示警告，用户决定是否处理
- 全部 PASS → 继续

### 5.9 本科特殊检查（仅 `{DEGREE_TYPE}` == 本科）

#### 5.9.1 外文翻译附录

检查 `appendix/trans-body.tex`（或类似路径）：
- 文件是否存在
- 内容是否为空或仍为 TODO
- 翻译字数是否达到要求（通常 >=3000 字）

#### 5.9.2 原文 PDF

检查 `appendix/origin.tex` 或 `appendix/origin.pdf`：
- 文件是否存在
- 是否已通过 `\includepdf` 或类似方式引入 main.tex

```
Phase 5.9 — 本科附录检查

| 检查项 | 状态 | 详情 |
|--------|------|------|
| 外文翻译 | {PASS/FAIL} | {详情} |
| 原文PDF | {PASS/FAIL} | {详情} |
```

### 5.10 Git Checkpoint

```bash
git add -A && git commit -m "diss-finalize: format compliance fixes"
```

（如无修改则跳过 commit）

---

## Phase 6: 编译验证

### 6.1 清理并完整编译

```bash
latexmk -C
latexmk {MAIN_TEX}
```

### 6.2 检查编译输出

分析编译 log，分类报告：

```
Phase 6 — 编译验证

Errors: {N}
Warnings: {N}（其中 {M} 条需关注）
Overfull/Underfull boxes: {N}

需关注的 Warning：
1. {warning 内容}（{文件}:{行号}）
2. ...
```

- Error > 0 → 逐条修复，重新编译
- 关键 Warning（如 `Citation undefined`、`Reference undefined`、`Float specifier changed`） → 报告并建议修复
- Overfull box > 5mm → 报告位置，建议调整

### 6.3 PDF 页数验证

检查生成的 PDF 页数是否合理（根据学位类型）：
- 本科：30-60 页
- 硕士：80-140 页
- 博士：100-200 页

超出范围 → 警告（不阻塞）

### 6.4 Git Checkpoint

```bash
git add -A && git commit -m "diss-finalize: final compilation verified"
```

---

## Phase 7: 更新项目阶段

### 7.1 更新 CLAUDE.md

在项目 CLAUDE.md 中查找 `## 项目阶段` 部分，根据条件判定目标阶段：

- **Phase 5 格式终检全部 PASS（无 FAIL 项）且用户明确确认准备提交** → 更新为 `submitted`，更新时间为 `{TODAY}`
- **否则** → 保持 `polishing`，更新时间为 `{TODAY}`，并附注说明：
  - 如有 FAIL 项未修复 → 列出待修复项
  - 如用户未确认提交 → 提示"全部检查通过后，再次运行 `/diss-finalize check` 并确认提交即可转为 submitted"

### 7.1.5 Git Push（里程碑：定稿完成）

```bash
git push
```

### 7.2 完成报告

```
diss-finalize 完成！

中文摘要：{CHAR_COUNT} 字 → {ABSTRACT_ZH_FILE}
英文摘要：{WORD_COUNT} words → {ABSTRACT_EN_FILE}
致谢模板：{ACK_FILE}（请自行填写）
格式终检：{FAIL_COUNT} FAIL / {WARN_COUNT} WARN / {PASS_COUNT} PASS
编译验证：{ERROR_COUNT} errors / {WARN_COUNT_COMPILE} warnings
PDF 页数：{PAGE_COUNT} 页

下一步：
- 填写致谢内容
- 处理剩余 WARN 项（如有）
- 检查 PDF 排版效果（逐页翻阅）
- 提交给导师审阅
```

---

## 全局约束

### 交互模式
- Phase 1-2：逐块提议 → 用户确认 → 循环
- Phase 3-4：模板确认，一步完成
- Phase 5：自动检查 → 汇总报告 → FAIL 项交互修复
- 用户可以在任何 Phase 输入 "skip" 跳过该阶段
- 用户可以在任何 Phase 结束后输入 "stop" 中断流程

### 语言
- 中文摘要：纯中文
- 英文摘要：纯英文
- 交互对话：中文
- 格式检查报告：中文

### 不越界
- Phase 1-4：不修改正文章节内容（chapters/*.tex 的正文部分），只写摘要、致谢和声明
- Phase 5：格式问题修复限于标签、引用、cls/sty 配置层面，不改正文内容
- 不修改 bib 条目内容（只报告问题）

### 幂等
可以反复运行。每次运行覆盖对应位置的内容。支持从任意 Phase 开始。
