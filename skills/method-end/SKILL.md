---
description: "从成熟的过程文件(_dev.md)凝练正文要点，填充技术型章节的成稿md，为 /pen-draft 提供高质量输入（仅在章节结构与字数分配两个节点交互）（Method End — Dev to Final MD）"
---

# Method End — 技术型章节凝练（最小交互）

从经过 `/method-audit` 审计修复的成熟过程文件（`X_dev.md`）中，自动提取正文要点，填充技术型章节的成稿文件（`X.md`）。凝练完成后，成稿 md 即可作为 `/pen-draft` 的唯一素材源。

**核心原则**：
1. **做减法，不做加法**：素材已在 _dev.md 中，凝练是"提取+格式化"，不是创作新内容。
2. **sci-writer 零判断**：凝练后的成稿 md 必须满足"sci-writer 翻译时不需要做任何技术判断"的颗粒度标准。
3. **引用精准标注**：技术型章节引用密度低但必须精准——假设论证、方法对标、参数依据需引用，公式推导和命题陈述不需要。
4. **最小交互**：仅在两个关键节点与用户交互——(a) 章节结构未确认时；(b) 目标字数确定与字数分配表确认。其余环节（逐 subsection 凝练、一致性修复、阶段转换等）全自动执行，问题汇总到最终报告集中 review。

**输入** `$ARGUMENTS`：可选，指定章节。示例：
- `/method-end` — 顺序处理所有技术型章节
- `/method-end methodology` — 只处理 methodology
- `/method-end results` — 只处理 results
- `/method-end simulation` — 只处理 simulation

---

## 步骤 0：前置准备

### 0.1 解析 `$ARGUMENTS`

- 提取 `section` 参数
- 无参数 → 按 CLAUDE.md 中 structure/ 表格识别所有技术型章节，按顺序处理（methodology → results → simulation）
- 有参数 → 仅处理指定章节

### 0.2 读取项目配置

- 读取 `CLAUDE.md` → 提取：
  - `{METHOD_TYPE}`（modeling / survey-sem / panel-regression）
  - `{TARGET_JOURNAL}`（目标期刊）
  - `{PAPER_TITLE}`（论文标题）
  - structure/ 目录结构表 → 识别技术型章节文件路径
  - 技术型颗粒度标准（`## 文件交互规则` 中的要求）
- 读取 bib 文件路径

### 0.3 前置检查

**检查成稿 md 的章节结构**（⚠️ 交互点 1）：

读取每个待处理的成稿 md，检查 `## 正文要点` 下是否有已确认的 `###` 结构：
- 有 `###` 标题且**不全是初始 TODO**（即 `/method-audit` Step 5.7 已执行）→ 通过
- 全是初始 TODO 或无 `###` 标题 → **AskUserQuestion**：

```
⚠️ {X.md} 的章节结构似乎未经 /method-audit 确认。
建议先运行 /method-audit 完成结构确认（Step 5.7）。

(1) 仍然继续（使用现有结构；若无 `###` 标题则从 _dev.md 层级推断）
(2) 退出，先运行 /method-audit
```

用户选 (2) → 退出。用户选 (1) → 继续。

**检查 _dev.md 内容充分性**：

读取对应的 _dev.md，检查是否有实质内容（非空、非纯 TODO）：
- 有实质内容 → 通过
- 内容不足 → **跳过该章节**，记入最终报告（其他章节继续处理）

### 0.4 读取上下文

1. 读取 `{IDEA_PATH}` → `{IDEA_CONTEXT}`（idea.md 全文）
2. 读取当前章节的 `_dev.md` → `{DEV_CONTENT}`（全文）
3. 读取当前章节的成稿 md → `{FINAL_MD_CONTENT}`（全文，含已确认的结构）
4. 读取引用池文件 → `{CITATION_POOL_CONTENT}`（按成稿 md 底部 `## 引用池` 指引）
5. 读取 bib 文件 → 用于验证 citation key 存在性
6. 读取其他章节成稿 md 的标题和已有内容摘要 → `{CROSS_REF_CONTEXT}`（用于一致性参考）
7. 如存在 `structure/2_literature/method_landscape.md`（由 /method-audit 生成），读取其中的方法论创新汇总和对标定位，作为凝练时的参考。

显示已读取的文件列表：

```
📂 上下文已加载：
- 纲领: structure/0_global/idea.md
- 过程文件: {_dev.md 路径}（{行数} 行）
- 成稿文件: {md 路径}（{N} 个 subsection）
- 引用池: {逐行列出}
- 交叉参考: {有内容的其他章节成稿 md 列表}
```

---

## 步骤 1：展示处理计划（仅展示，不等待确认）

```
📋 凝练计划 — {章节名称}

源文件: {_dev.md 路径}
目标文件: {md 路径}

Subsection 列表：
  [1] ### {subsection_1_title}
  [2] ### {subsection_2_title}
  [3] ### {subsection_3_title}
  ...

模式: 最小交互（仅章节结构 + 字数分配需确认；逐 subsection 凝练全自动）
开始处理...
```

### 1.2 确定处理粒度

- 如果某个 `###` 下有 `####`：按 `####` 粒度逐个处理
- 如果某个 `###` 下无 `####`：按 `###` 粒度处理
- 即：**总是按最小标题单元处理**

---

## 步骤 2：逐 subsection 自动凝练

```
SET progress = 0
SET total = len({ALL_UNITS})  // 所有最小处理单元
SET issues_log = []  // 累积问题，最终报告

FOR each unit IN {ALL_UNITS}:
  progress += 1

  # ────────────────────────────────
  # 2.1 定位 _dev.md 对应内容
  # ────────────────────────────────

  从 {DEV_CONTENT} 中定位该 subsection/subsubsection 对应的内容块。

  **定位策略**：
  - 优先按标题匹配（_dev.md 中的 `###`/`####` 标题 vs 成稿 md 的标题）
  - 标题不完全对应时，按内容语义匹配（如成稿 md 的 "Assumptions" 对应 _dev.md 中所有假设相关内容）
  - 一个成稿 subsection 可能对应 _dev.md 中的多个离散段落——全部收集

  **定位困难时**：按最接近的语义匹配处理，并将该 unit 的定位假设记入 `issues_log`（而非弹窗询问）。

  # ────────────────────────────────
  # 2.2 提取源内容（静默，不展示）
  # ────────────────────────────────

  内部记录本 unit 提取的关键元素清单（公式、假设、命题、引用等），仅用于最终报告统计，不在处理过程中打印。

  # ────────────────────────────────
  # 2.3 生成凝练草案
  # ────────────────────────────────

  按以下规则从 _dev.md 内容中提取和组织正文要点：

  **保留（必须出现在成稿 md 中）**：
  - 每一个会出现在正文中的公式（编号公式用 `$$...(N)$$`，关键行内公式保留）
  - 每一个命题/引理的完整陈述（含编号、条件、结论）
  - 每一个证明的思路骨架（1-3 句话概括证明路径）
  - 每一个假设的文字表述 + 合理性论证
  - 每一个经济直觉/含义解读
  - 每一个模型间的对比说明
  - 变量/参数定义（首次出现时）

  **转换处理**：
  - 完整证明 → 仅保留思路骨架 + `> **Proof (→ Supplementary):** {1-2句证明路径概述}`
  - 推导中间步骤 → 去掉，仅保留起点和终点
  - 版本迭代记录、备注讨论、已否决方案 → 去掉
  - 冗长的分类讨论 → 压缩为结论 + 关键条件

  **正文适配性过滤**（凝练时对每一段内容执行）：

  成稿 md 只收录正文内容。_dev.md 中的非正文内容一律丢弃——它们已保存在 _dev.md 中，需要时可随时查阅。

  | 判断 | 处理 |
  |:-----|:-----|
  | 正文内容（假设陈述、公式、简要合理性论证（1句）、经济直觉、命题陈述、模型间对比） | ✅ 写入成稿 md |
  | 完整证明/推导过程 | 标记 `→ Supplementary` |
  | 其他一切（防御性论证、WLOG 一般性证明、退化验证细节、参数条件充分性证明、"留作 future research"的扩展方向、版本对比记录） | ❌ 丢弃（留在 _dev.md 中） |

  **判断标准**：如果一段内容的存在目的是"防止审稿人质疑"而非"向读者传达模型设定"，则不属于正文。防御性论证是审稿回复信的素材，不是正文或补充材料的内容。

  **图表标注**：
  - 表格 → "此处引用 Table X / Fig. X"（引用 `figures_tables/index.md` 中的编号）
  - 不在成稿 md 中嵌入表格/图表内容

  **引用标注**（技术型章节的引用判断规则）：

  以下类型的句子**需要引用**：
  - 假设的合理性论证（"This assumption is standard in..." → METHOD 标签文献）
  - 方法选择的对标（"Following \citet{xxx}, we adopt..." → METHOD/COMP 文献）
  - 参数校准的依据（"Based on industry data from..." → BG/LR 文献）
  - 与既有文献结果的对比（"Consistent with \citet{xxx}..." → DISC 文献）
  - 行业背景/制度引用（"According to..." → BG 文献）

  以下类型的句子**不需要引用**：
  - 公式推导和数学变换
  - 命题陈述（命题本身是本文贡献）
  - 证明步骤
  - 经济直觉解读（本文自己的分析）
  - 模型间对比说明（本文自己的结果）
  - 变量/参数定义

  **引用来源**：按成稿 md 底部 `## 引用池` 的指引，从对应的 citation pool 文件中匹配最合适的 citation key。
  - 使用 `\citet{}` 当文献作者是句子主语
  - 使用 `\citep{}` 当文献作为括号引用
  - 每处引用不超过 3 个 key
  - citation pool 中找不到合适文献 → 标记 `(ref)`，记入 `issues_log`
  - **所有 citation key 必须在 bib 文件中存在**，不存在则标记 `(ref)` 并记入 `issues_log`

  **书写语言**：中文表述，但以下内容用英文原文：
  - citation key（`\citet{}`/`\citep{}`）
  - 专用术语（如 Stackelberg, Nash equilibrium, moral hazard）
  - 公式符号
  - `###`/`####` 标题（与 manuscript 一致）

  # ────────────────────────────────
  # 2.4 直接写入成稿 md（无交互）
  # ────────────────────────────────

  将凝练内容写入成稿 md 对应的 `###`/`####` 标题下：
  - 替换该标题下的原有内容（通常是 TODO）
  - 保持其他 subsection 不变
  - **不输出引用建议表**——仅在完成后的总结中汇总 (ref) 待补项

  **同步 bib**：写入成稿 md 后，立即将本 subsection 新增的 citation key 同步到项目 bib：
  1. 从刚写入的内容中提取所有 `\citep{}`/`\citet{}` 中的 citation key（正则提取，去重）
  2. 检查每个 key 是否已在项目 bib 中
  3. 不在的 → 从 `structure/2_literature/citation_pool/master.bib` 中提取对应条目，追加到项目 bib 末尾
  4. master.bib 中也找不到 → 记入 `issues_log`

  显示一行进度："✓ [{progress}/{total}] {unit_title} — 已写入 ({N}行, {M}引用)"

END FOR
```

---

## 步骤 2.8：字数分配表（交互确认）

所有 subsection 凝练完成后（或当前章节凝练完成后），生成字数分配表并与用户交互确认，再写入成稿 md。

### 2.8.1 确定总字数（⚠️ 交互点 2a）

从成稿 md 头部读取 `> 目标字数: {N} words` 中的数值。

- **读到数值** → 使用该值（由 /method-audit step 5.8 基于 benchmark 写入），直接进入 2.8.2
- **读到 TBD 或无法解析** → **AskUserQuestion**：
  ```
  ⚠️ {md文件名} 的目标字数尚未确定（仍为 TBD）。
  建议先运行 /method-audit 基于 benchmark 论文确定各 section 字数。

  (1) 手动指定字数（输入数字）
  (2) 使用 benchmark 默认值（methodology=2500 / results=3500 / simulation=2000）
  (3) 跳过该章节（先运行 /method-audit 后再来）
  ```
  用户选 (1) → 使用用户指定值
  用户选 (2) → 使用默认值，在最终报告中记录
  用户选 (3) → 跳过该章节，其他章节继续处理

用户可在后续的字数分配确认（step 2.8.4）中再次修改总字数。

### 2.8.2 自动分配各 subsection 字数

- 基础分配 = 总字数 × (该 subsection 凝练内容行数 / 全部 subsection 凝练内容总行数)
- 密度调整：
  - 含大量公式的 subsection：权重 ×1.1
  - 纯方法论概述：不调整
  - 含命题+证明骨架的 subsection：每个命题约需 80-120 词
  - 含比较静态/敏感性分析的 subsection：每个参数约 50-80 词
- 取整到最近的 50

### 2.8.3 生成写作说明

为每个 subsection 生成一句话风格指导，指示 sci-writer 的转译策略：

- **方法论概述类**（如 3.1）："Justify method choice with brief comparison table; concise"
- **模型设定类**（如 3.2）："Define all notation precisely; each assumption needs one-sentence justification"
- **模型求解类**（如 3.3, 3.4）："Present payoff functions → equilibrium derivation → key results; every equation needs economic interpretation"
- **命题分析类**（如 4.2）："State proposition → proof sketch → economic intuition; highlight mechanism"
- **仿真类**（如 5.1-5.5）："Parameter table → figure interpretation → managerial insight; link back to propositions"

### 2.8.4 展示并确认字数分配（⚠️ 交互点 2b）

展示完整的字数分配方案：

```
📊 字数分配方案（总目标: {N} words）

| Subsection | 内容密度 | 目标字数 | 写作说明 |
|:-----------|:-------:|:-------:|:--------|
| ### 3.1 ... | 6行 | 200 | {风格指导} |
| ### 3.2 ... | 45行 | 550 | {风格指导} |
| ### 3.3 ... | 38行 | 500 | {风格指导} |
| ### 3.4 ... | 52行 | 750 | {风格指导} |
| 合计 | — | {N} | — |

你可以修改总字数、单个 subsection 字数或写作说明。确认后写入成稿 md。
```

**AskUserQuestion**：
```
(1) 确认,按上表写入
(2) 调整（说明要改哪里，如"总字数改成 3000"、"3.3 给 600 words"、"3.1 风格改成..."）
```

用户选 (2) → 按用户意见修改 → 重新展示 → 再次确认（循环直到确认）。
用户选 (1) → 进入 2.8.5 写入。

### 2.8.5 写入成稿 md（**双写**：正文要点区 + 头部目标字数）

用户确认后，自动完成两处同步写入：

1. **写入 `## 正文要点` 区块开头**（subsection 级分配表，供 /pen-draft 读取）
2. **回写 md 头部 `> 目标字数: {N} words`**（section 级目标，供 /pen-outline 步骤 6.1 读取）

> 防错机制：若只写 `## 正文要点` 不回写头部，后续 /pen-outline 会从头部读到过时的旧值，造成口径错位。二者必须同步。

具体写入 `## 正文要点` 的格式（在第一个 `###` 之前）：

```markdown
## 正文要点

**目标总字数: {N} words**

| Subsection | 目标字数 | 写作说明 |
|:-----------|:-------:|:--------|
| {title1} | {n1} | {说明1} |
| {title2} | {n2} | {说明2} |
| ... | ... | ... |

### {title1}
{凝练内容}
...
```

> 技术型章节使用 3 列（Subsection | 目标字数 | 写作说明），叙述型章节（`/pen-outline`）使用 4 列（多一列"要点数"）。`/pen-draft` 根据列数自适应解析。

---

## 步骤 3：交叉一致性检查（静默，结果入报告）

所有章节凝练完成后，执行一致性检查。发现的问题全部记入 `issues_log`，在步骤 4 的报告中集中展示——**不弹窗询问用户**。

### 3.1 成稿 md 内部一致性

逐个检查已填充的成稿 md：
- 符号定义与后续使用是否一致
- 假设编号是否连续、引用是否正确
- 命题编号是否连续
- 公式编号（如有 tag）是否连续
- 证明骨架中引用的命题号是否正确

### 3.2 成稿 md 之间一致性

跨技术型成稿 md 检查：
- methodology.md 定义的符号 → results.md 和 simulation.md 中的使用是否一致
- methodology.md 定义的假设编号 → results.md 命题证明中的引用是否正确
- results.md 定义的命题编号 → simulation.md 仿真验证中的引用是否正确

### 3.3 成稿 md 与 idea.md 一致性

- RQ 编号和措辞：idea.md §2 → simulation.md/results.md 中的 RQ 引用
- 贡献声明对应关系：idea.md §4 → results.md 中的命题是否覆盖所有贡献点

### 3.4 处理不一致

- **小问题**（拼写、编号错位、标点）→ 直接修复，记入报告
- **实质问题**（符号定义冲突、命题遗漏、RQ 编号漂移）→ **不自动改**，记入 `issues_log`，在报告中以 🔴 标记，由用户在 review 阶段决定

---

## 步骤 4：完成摘要 + Git checkpoint

### 4.1 输出总结（集中 review 入口）

```
📋 技术型章节凝练完成

═══════════════════════════════════════
📊 处理统计
═══════════════════════════════════════

| 章节 | Subsection | 已填充 | 跳过 | 引用数 | (ref)待补 | 目标字数 |
|------|-----------|--------|------|--------|----------|----------|
| methodology.md | {n} | {a} | {b} | {c} | {d} | {w} |
| results.md | {n} | {a} | {b} | {c} | {d} | {w} |
| simulation.md | {n} | {a} | {b} | {c} | {d} | {w} |

═══════════════════════════════════════
🔍 一致性检查结果
═══════════════════════════════════════

✅ 已自动修复 ({M} 处):
- {file}:{location} — {问题 → 修复}
- ...

🔴 需用户 review ({K} 处):
- {file}:{location} — {问题描述}
- ...

═══════════════════════════════════════
⚠️  其他待处理项
═══════════════════════════════════════

📝 (ref) 待补引用 ({R} 处):
- {file}:{location} — 需补: {引用类型}
- ...

📐 字数使用默认值 ({W} 处):
- {file} — 头部为 TBD, 使用默认 {N} words
- ...

📚 Bib 未匹配 citation key ({B} 处):
- {key} — master.bib 中未找到
- ...

═══════════════════════════════════════
📁 已修改文件
═══════════════════════════════════════
- {file1}
- {file2}
- ...

💡 下一步：
- 审查 🔴 标记项，必要时手动修改成稿 md
- 审查 (ref) 待补项，从 citation pool 补全引用
- 技术型章节定稿后运行 /pen-draft section={章节} 生成 manuscript 正文
```

### 4.2 阶段转换（自动，基于前置校验）

**按 `{METHOD_TYPE}` 查表确定"所有技术型章节"集合**：

| METHOD_TYPE | 技术型章节集合 |
|:-----------|:---------------|
| `modeling` | `methodology.md` + `results.md` + `simulation.md` |
| `survey-sem` | `methodology.md` + `results.md` |
| `panel-regression` | `methodology.md` + `results.md` |

**前置校验**（严格，不通过则不转换）：
1. 遍历该 METHOD_TYPE 下所有成稿 md，若**任一** md 仍含 `% TODO` / `[TODO]` / `[TBD]` / `???` 占位符 → **不转换**，在报告中说明。
2. 遍历成稿 md，确认 `## 正文要点` 区块字数分配表已写入 → 缺失则**不转换**。
3. issues_log 中有 🔴 实质问题 → **不转换**，提示用户先处理。
4. 读取 `benchmark/method_audit_report.md`（若存在），若有 `🔴 MUST-FIX` 未修复 → **不转换**。

前置校验**全部通过**、且本次 `/method-end` 为**多章节模式**（无 `$ARGUMENTS`）时：

```
🎯 前置校验全部通过，自动转换项目阶段：foundation → drafting
- 已更新 CLAUDE.md: 状态: drafting, 更新时间: {TODAY}
```

在 CLAUDE.md 中更新 `## 项目阶段`：
- `状态: drafting`
- `更新时间: {TODAY}`

前置校验**未通过**时：

```
⏸  前置校验未通过，保持 foundation 阶段。
阻塞原因:
- {原因1}
- {原因2}
用户解决后可再次运行 /method-end（或手动编辑成稿 md 后自行切换阶段）。
```

> 单章节模式下不触发阶段转换——用户可能只是补充某一章，不代表全部完成。

### 4.3 Git checkpoint

```bash
git add {所有被修改的成稿 md 文件} {项目 bib 文件（如有更新）}
git commit -m "Checkpoint: method-end condense complete"
```

> 仅 `git add` 实际被修改的文件。

---

## 全局约束

### 输出语言
- 凝练内容用**中文**（与 _dev.md 一致，后续由 sci-writer 翻译为英文）
- citation key、专用术语、公式符号、`###` 标题用**英文原文**
- 进度日志和最终报告用**中文**

### 不越界
- **只做提取和格式化**：不修改 _dev.md 中的技术内容实质（公式、命题、数值结果）
- **不替代研究判断**：_dev.md 中某个推导看起来有问题，记入 🔴 问题清单，不自行修正
- **不涉及叙述型章节**：Introduction, Literature Review, Discussion 由 `/pen-outline` 处理
- **不写入 manuscript.tex**：成稿 md 是本 skill 的终点，manuscript.tex 由 `/pen-draft` 处理

### 颗粒度标准（验证清单）

凝练完成的每个 `###` subsection 必须包含以下全部适用项（缺项即不达标，记入 issues_log）：

- [ ] 每一个会出现在正文中的编号公式
- [ ] 每一个关键行内公式
- [ ] 每一个命题/引理的完整陈述（编号 + 条件 + 结论）
- [ ] 每一个证明的思路骨架（+ Supplementary 标记）
- [ ] 每一个假设的文字表述 + 合理性论证（+ 引用）
- [ ] 每一个经济直觉/含义解读
- [ ] 每一个模型间的对比说明
- [ ] 表格和图表的引用标注

### 与其他 skill 的关系

- **前置**：`/method-audit`（Step 5.7 确认结构 → 本 skill 填充内容）
- **后继**：`/pen-draft`（读取本 skill 产出的成稿 md → 生成 manuscript.tex 正文）
- **不依赖**：`/pen-outline`（处理叙述型章节，与本 skill 互不干涉）

### 可重复运行

- 支持对已填充的成稿 md 重新运行 `/method-end`
- 处理每个 unit 时，如果该 subsection 已有实质内容（非 TODO）：
  - **默认行为**：重新凝练覆盖（幂等性优先，确保最新 _dev.md 内容传递到成稿）
  - 保留的原则：如果新凝练结果与原有内容差异显著（> 30% 行数变化），在报告中以 ⚠️ 标记，提醒用户 review 差异

### 交互边界

本 skill **仅在两个节点使用 AskUserQuestion**：
1. **交互点 1**（步骤 0.3）：章节结构未经 /method-audit Step 5.7 确认时，询问"继续/退出"
2. **交互点 2**（步骤 2.8.1 + 2.8.4）：目标字数 TBD 时询问来源；字数分配表生成后逐章确认

**其他分叉点一律非交互**，采用以下策略：
- 逐 subsection 凝练：直接写入，不逐节确认
- 定位困难：按语义最近匹配处理，记入 issues_log
- 小的一致性问题（拼写、编号错位）：直接修复
- 实质一致性问题（符号冲突、命题遗漏）：以 🔴 记入最终报告，不自动改
- 章节边界（当前章完成后是否继续下一章）：自动继续
- 阶段转换（foundation → drafting）：前置校验全过则自动转

用户在完成后的**最终报告**中集中 review：🔴 实质问题、(ref) 待补引用、默认字数使用记录、bib 未匹配 key 等。
