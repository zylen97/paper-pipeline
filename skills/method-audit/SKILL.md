---
description: "方法论优化：对标行业实践 → 审计方法问题 → 优化论文结构，基于对标论文的行业基线精准定位问题并逐条交互修复（Method Audit & Optimization）"
---

# Method Audit — 方法论审计与优化

对标同方法的已发表论文，建立行业基线，再基于基线审计当前论文的方法论问题并提出对标借鉴建议（结构优化、模型创新、图表设计）。

**核心原则**：
1. **对标先于审计**：先看行业怎么做，再评判我们做得够不够。没有对标数据的审计是盲审。
2. **具体性**：每条质疑必须指向 md 中的具体位置，且不能"换论文仍成立"。
3. **对标借鉴是必做项**：从对标论文中学习章节结构、模型设计技巧和图表呈现方式。

**输入** `$ARGUMENTS`：可选，指定审计范围。示例：
- `/method-audit` — 全流程（对标 + 审计 + 对标借鉴）
- `/method-audit methodology` — 只审计 methodology
- `/method-audit results` — 只审计 results

---

## 步骤 0：上下文加载

### 0.1 读取项目配置

- 读取 `CLAUDE.md` → 提取：
  - `{METHOD_TYPE}`（modeling / survey-sem / panel-regression）
  - `{TARGET_JOURNAL}`（目标期刊）
  - `{PAPER_TITLE}`（论文标题）
- 缺少 METHOD_TYPE → 停止，提示用户补全 CLAUDE.md

### 0.2 读取研究纲领

- 读取 `structure/0_global/idea.md` → 提取：
  - RQ（研究问题）
  - Gap（研究缺口）
  - 方法论框架概述
  - 核心贡献声称
- 不存在 → 警告但不停止（允许在没有 idea.md 的老项目上运行）

### 0.3 读取过程文件

按 `$ARGUMENTS` 和 `{METHOD_TYPE}` 读取**过程文件**（`X_dev.md`）：

| 文件 | 路径 | 条件 |
|------|------|------|
| methodology_dev.md | `structure/3_methodology/methodology_dev.md` | 始终读取 |
| results_dev.md | `structure/4_results/results_dev.md` | `$ARGUMENTS` 为空或含 "results" |
| simulation_dev.md | `structure/5_simulation/simulation_dev.md` | 仅 modeling 类型 + `$ARGUMENTS` 为空或含 "simulation" |

> **审计对象是过程文件（`X_dev.md`）**——完整的技术细节在这里。审计修复也回写到 `_dev.md`。审计完成后，用户从 `_dev.md` 凝练到成稿 `X.md`。

**空文件检测**：如果 `_dev.md` 内容过少（不足以支撑审计），停止并提示：

```
⚠️ {文件名} 内容不足，无法审计。
请先在过程文件中填充足够的技术内容，再运行 /method-audit。
```

**跨文件一致性检查**：扫描所有 `_dev.md`，检查以下元素是否一致：
- 符号名称和定义（methodology_dev.md 定义 → results_dev.md 和 simulation_dev.md 引用）
- 假设编号（methodology_dev.md 定义 → results_dev.md 引用）
- 命题编号（results_dev.md 定义 → simulation_dev.md 和 discussion.md 引用）
- 不一致项标记为 🔴 MUST-FIX

### 0.4 识别具体方法

不要用粗粒度标签（如"博弈论"）。基于读取的实际内容，识别**精确的方法描述**。示例：

- ❌ "博弈论"
- ✅ "三阶段 Stackelberg 博弈 + 逆向溯源信号机制，含分离/混同均衡分析，考虑制造商质量努力连续决策和区块链溯源成本"
- ❌ "SEM"
- ✅ "CB-SEM + fsQCA 混合设计，DV 为项目沟通效果，基于 Media Synchronicity Theory，含两个中介变量和一个调节变量"
- ❌ "网络分析"
- ✅ "SAOM 纵向网络模型，4 期专利合作网络（2011-2025），Top 200 创新申请人，行为变量为组织间互补性指数"

记录为 `{METHOD_DETAIL}`，后续审计基于此展开。

---

## 步骤 1：基线完整性检查

**目的**：快速扫描必备元素是否齐全。30 秒出结果，发现缺失直接打回。不需要对标，纯粹是"该有的东西有没有"。

### 1.1 加载必备元素清单

读取各成稿 md 的 `## 必备元素` 列表，逐项检查对应的 `###` 小节是否有实质内容。同时检查以下维度是否覆盖：

**modeling**：
- [ ] methodology.md: 方法选择论证（为什么用此方法 + 对比表）
- [ ] methodology.md: 问题描述与假设（供应链结构 + 假设 + 符号表 → Table）
- [ ] methodology.md: 各模型的收益函数 + 均衡求解结果
- [ ] results.md: 命题（显式编号 + 证明思路 + 经济直觉）
- [ ] results.md: 比较静态 / 参数敏感性（汇总表 → Table）
- [ ] simulation.md: 参数校准（取值来源论证）
- [ ] simulation.md: 仿真结果（图表 + 数值验证命题）

**survey-sem**：
- [ ] methodology.md: Data collection（目标群体 + 抽样方式 + 样本量论证 + 回收率）
- [ ] methodology.md: Bias mitigation（CMV 预防措施 + 检验方法）
- [ ] methodology.md: Questionnaire development（量表来源 + 预测试）
- [ ] methodology.md: Measures（DV/IV/中介/调节/控制变量定义）
- [ ] methodology.md: Analytical methods（方法选择论证 + 软件版本）
- [ ] results.md: Reliability and validity（α, CR, AVE, 判别效度）
- [ ] results.md: Hypothesis testing（路径系数 + 显著性 + 效应量）
- [ ] results.md: Robustness checks（至少一种稳健性检验）

**panel-regression**：
- [ ] methodology.md: Sampling and data collection（数据源 + 时间窗口 + 筛选标准 + 样本量）
- [ ] methodology.md: Measures（DV/IV/控制变量/工具变量定义 + 计算公式）
- [ ] methodology.md: Methods of analysis（回归方程 + 模型选择论证 + 内生性策略）
- [ ] results.md: Descriptive statistics（描述性统计 + 相关系数 + VIF）
- [ ] results.md: Hypothesis testing（主回归 + 逐步模型）
- [ ] results.md: Robustness checks（内生性检验 + 替换变量/子样本/替换模型）

### 1.2 逐项扫描

对每个必备元素，在对应 md 文件中搜索相关内容：
- **已覆盖**：找到了实质性内容（不是 TODO）→ ✅
- **部分覆盖**：有内容但不完整（如符号表只列了一半、缺某类变量）→ ⚠️
- **缺失**：找不到或仍为 TODO → ❌

### 1.3 基线报告

输出基线检查结果：

```
📋 基线完整性检查 — {PAPER_TITLE}
方法类型: {METHOD_TYPE} | 具体方法: {METHOD_DETAIL}

methodology.md:
  ✅ §3.1 方法选择论证 — 完整，含对比表
  ✅ §3.2 问题描述与假设 — 符号表 18 项，假设 4 个
  ⚠️ §3.3 Model A — 均衡结果有，但缺经济直觉解读

results.md:
  ✅ Equilibrium analysis — 5 个命题，均有证明
  ❌ Comparative analysis — 仍为 TODO
```

**如果有 ❌ 项**：AskUserQuestion：

```
基线检查发现 {N} 项缺失（标记 ❌）。建议先补全再继续。
(1) 继续（跳过缺失部分）
(2) 停止，先去补全
```

---

## 步骤 2：对标分析

**目的**：在审计之前建立行业基线。找出同方法的已发表论文，系统提取它们的方法论处理方式和论文结构，为步骤 3 的审计提供硬数据支撑。

### 2.0 对标入口判定

按优先级依次检查（命中即停，不继续后续判断）：

```
1. 检查缓存（最高优先级）：
   IF structure/3_methodology/benchmark/cross_comparison.md 存在且时间戳 < 7 天:
     → AskUserQuestion：
       "检测到已有对标分析（{date}，{N} 篇论文）。
       (1) 复用现有对标数据（推荐）
       (2) 重新分析"
     用户选 (1) → 跳过 2.1-2.5，直接读取 cross_comparison.md，进入 2.6
     用户选 (2) → 继续检查下一条件

2. 检查引用池：
   IF citation pool 中无 METHOD/COMP 标签的论文:
     → AskUserQuestion：
       "引用池中未找到同方法的对标论文。
       (1) 手动指定论文（提供 citation key 或标题，我来生成候选列表）
       (2) 跳过对标，使用 Claude 知识进行审计（降级模式）"
     用户选 (2) → 跳过整个步骤 2，步骤 3 回退为纯知识审计（不附带行业基线标注）
     用户选 (1) → 进入 2.1（用户手动提供列表）

3. 正常流程：
   ELSE → 正常执行 2.1
```

### 2.1 筛选对标论文

**信息源**：从 `structure/2_literature/citation_pool/` 中的 METHOD.md 和 COMP.md 读取候选论文。

**筛选逻辑**（按优先级）：
1. 同方法 + 同行业（第一梯队）
2. 同方法 + 不同行业但高质量期刊（第二梯队）
3. 同方法 + 最近 2 年发表（第三梯队，捕捉最新报告规范）

**候选数量**：5-8 篇。

**输出格式**：

```
📚 对标论文候选（共 {N} 篇）

第一梯队（同行业同方法）：
1. {citation_key} — {一句话描述}, {期刊}
2. ...

第二梯队（同方法不同行业）：
3. {citation_key} — {一句话描述}, {期刊}
4. ...

第三梯队（最新前沿）：
5. {citation_key} — {一句话描述}, {期刊}
...

确认论文列表？可增删。确认后请将 PDF 放入 structure/3_methodology/benchmark/
```

AskUserQuestion 让用户确认/增删。

### 2.2 生成 RIS 下载清单

用户确认列表后：

1. 如 `structure/3_methodology/benchmark/` 不存在则创建
2. 从项目 bib 文件中提取每篇确认论文的完整引用信息（TY、TI、AU、JO、PY、DO 等字段），生成 RIS 格式文件保存至 `structure/3_methodology/benchmark/benchmark_papers.ris`
3. 如 bib 中缺少 DOI，尝试用 WebSearch 补全后再写入 RIS
4. 提示用户："RIS 已生成于 `structure/3_methodology/benchmark/benchmark_papers.ris`，请用文献管理工具导入后下载 PDF，放回同一目录。"

### 2.3 检测 PDF

Agent 用 Glob 检测 `structure/3_methodology/benchmark/*.pdf`，模糊匹配文件名。

**如果部分 PDF 缺失**：允许 ≥3 篇即可继续，行业基线的可信度注明样本量（如"基于 5/8 篇论文"）。

### 2.4 并行 subagent 分析

每篇 PDF 启动一个 subagent（`run_in_background: true`，最多 8 个并行），使用标准化提取模板。

**Subagent prompt 模板**：

```
你是一个 {METHOD_TYPE} 方法论审计专家。请阅读以下论文 PDF，生成结构化的方法论对标报告。

**论文**: {PDF 路径}
**Citation key**: {key}

**我们论文的基本参数**（用于 A 部分对比）：
{从步骤 0 提取的 METHOD_DETAIL + 关键参数摘要}

**我们论文的写作现状**（用于 B 部分评估适配性）：
- 当前 Methodology 结构：{从 methodology.md 提取的小节标题列表}
- 当前 Results 结构：{从 results.md 提取的小节标题列表}
- 核心发现摘要：{从 results.md 关键发现部分提取，含核心效应的参数值和显著性}
- 数据特征：{节点数、期数、密度范围、度分布偏斜情况、行为变量分布}
- 已有/计划中的图表：{列出当前 md 中提及的表格和图}

**请提取以下信息**：

## A. 事实提取（纯客观记录）

1. **基本信息**：标题、期刊、年份、研究情境、软件版本
2. **数据与样本**：节点数、期数、窗口长度、密度、网络类型
3. **模型设定**：效应/变量完整列表、嵌套模型策略、估计方法和参数
4. **诊断与检验**：收敛诊断、GOF（统计量+结果+处理方式）、稳健性检验（数量+具体项目）
5. **报告规范**：显著性标准、效应量报告方式（exp(β)/odds ratio）、缺失数据处理、边缘显著处理
6. **章节结构**（⭐ 关键提取项——直接影响后续结构决策）：
   - Methodology 完整层级（大标题→小标题→subsubsection→每节核心内容+估算篇幅占比）
   - Results/Analysis 完整层级（报告顺序、独立小节划分、各节衔接方式）
   - Simulation/Numerical Analysis 完整层级（若存在：参数设定→基准情景→敏感性分析→管理启示的组织方式）
   - 对于博弈论/建模论文额外记录：模型数量及命名方式、假设集中呈现还是分散嵌入、命题/引理的放置位置（正文 vs 附录）、证明的呈现方式（正文完整证明/正文sketch+附录完整/纯附录）
7. **图表清单**：所有方法/结果相关图表（编号+标题+内容简述+呈现方式）
8. **各 section 字数统计**：
   统计论文每个一级 section 的估算字数（Introduction, Literature Review,
   Methodology/Research Design, Results/Analysis, Discussion, Conclusion，
   以及 Simulation/Numerical Analysis 如存在）。
   - 统计方法：按 section 起止页计算正文面积，扣除图表、公式块、表格占位面积，
     按每页约 600-800 词（单栏）或 1000-1200 词（双栏）估算
   - 如果 section 内有 subsection，同时统计每个 subsection 的字数
   - 输出格式：
     | Section | Subsections | 估算字数 |
     |:--------|:-----------|:---------|
     | Introduction | — | {N} |
     | Literature Review | {sub1}, {sub2}, ... | {N} |
     | Methodology | {sub1}, {sub2}, ... | {N} |
     | Results | {sub1}, {sub2}, ... | {N} |
     | Simulation（如有） | {sub1}, {sub2}, ... | {N} |
     | Discussion | {sub1}, {sub2}, ... | {N} |
     | Conclusion | — | {N} |
     | **正文合计** | | **{total}** |
   注：字数为估算值（±10%），不含 Abstract、References、Appendix。

{METHOD_TYPE 差异化补充——见下方}

## B. 对标评估（每条须结合"我们论文的写作现状"做适配性判断）

### B1. 方法论对比
该文 vs 本文在模型设定、诊断检验、报告规范上的关键差异，明确指出我们的优势和短板。

### B2. 结构借鉴
基于 A6，该文的章节组织中哪些安排值得本文采纳？哪些是我们缺失的？

### B3. 模型创新
基于 A3，该文有什么独特的模型设计技巧（效应选择、变量构造、估计策略、诊断方法）？逐条评估是否适用于本文，如适用则说明如何纳入。

### B4. 图表借鉴
基于 A7，哪些图表设计出色（说明好在哪里）？逐条分析是否适配本文数据和结果，如适配则建议如何借鉴。

报告用中文写，技术术语保留英文。
写入: structure/3_methodology/benchmark/{citation_key}_benchmark.md
```

**METHOD_TYPE 差异化补充**（追加到 subagent prompt 末尾）：

- **SAOM/网络模型**：额外提取 Jaccard index、score test、composition change 处理、forcing model 设定、MaxDegree 约束
- **SEM/问卷**：额外提取 CFA 报告方式、AVE/CR 阈值、CMV 检验方法、measurement model 是否独立报告
- **博弈论/建模**：额外提取参数校准来源、命题证明详细程度、数值模拟的参数取值论证、数值模拟章节的完整小节结构（参数设定节→基准情景节→敏感性分析节→管理启示节的层级与篇幅分配）
- **面板回归**：额外提取内生性策略（IV/GMM/DID）、工具变量选择论证、固定效应 vs 随机效应的 Hausman 检验

### 2.5 横向比对表

所有 subagent 完成后，自动生成 `structure/3_methodology/benchmark/cross_comparison.md`：

**表 1：数据与模型比对**

```markdown
| 论文 | 期刊 | 年份 | 节点/样本 | 期数 | 密度 | 效应数 | 行为共演 | ... |
|:-----|:-----|:--:|:--:|:--:|:-----|:--:|:--:|
| **本文** | **{TARGET_JOURNAL}** | ... | ... | ... | ... | ... | ... |
| {key1} | ... | ... | ... | ... | ... | ... | ... |
| ... |
```

**表 2：方法论规范比对**

```markdown
| 维度 | 本文 | {key1} | {key2} | ... | 行业基线 |
|:-----|:--:|:--:|:--:|:--|:---------|
| GOF/拟合 | {状态} | {状态} | {状态} | | {N}/{M} 篇报告 |
| 稳健性检验 | {N}项 | {N}项 | {N}项 | | 中位数 {X} 项 |
| 嵌套模型 | {状态} | {状态} | {状态} | | {N}/{M} 篇使用 |
| exp(β)/效应量 | {状态} | {状态} | {状态} | | {N}/{M} 篇报告 |
| 收敛诊断 | {状态} | {状态} | {状态} | | {N}/{M} 篇报告 |
| 缺失数据讨论 | {状态} | {状态} | {状态} | | {N}/{M} 篇讨论 |
| Score test | {状态} | {状态} | {状态} | | {N}/{M} 篇使用 |
```

**表 3：章节结构详细比对**

```markdown
| 论文 | Methodology 层级结构 | Results/Analysis 层级结构 | Simulation/Numerical 层级结构 | 证明放置方式 | 模型创新（适用于本文的） | 推荐图表（适配本文数据的） |
|:-----|:--------------------|:------------------------|:----------------------------|:-----------|:------------------------|:-------------------------|
| **本文** | {当前 ### + #### 结构} | {当前 ### + #### 结构} | {当前 ### + #### 结构} | {当前方式} | | |
| {key1} | {### + #### 结构} | {### + #### 结构} | {### + #### 结构，若无标 N/A} | {正文/附录/混合} | {从 B3 提取} | {从 B4 提取} |
| ... |
```

> 注：结构列须包含 subsubsection 级别（即 `####` 对应的层级），每级用缩进表示层级关系。对于博弈论/建模论文，Methodology 列须标注各模型的起止小节和假设集中区段。

**表 4：各章节字数对比**

```markdown
| 论文 | Intro | Lit Review | Methodology | Results | Simulation | Discussion | Conclusion | 正文合计 |
|:-----|:-----:|:---------:|:-----------:|:-------:|:----------:|:----------:|:----------:|:--------:|
| **本文** | **TBD** | **TBD** | **TBD** | **TBD** | **{如适用}** | **TBD** | **TBD** | **TBD** |
| {key1} | ... | ... | ... | ... | ... | ... | ... | ... |
| ... |
| **中位数** | {N} | {N} | {N} | {N} | {N/—} | {N} | {N} | {N} |
| **范围** | {min}-{max} | ... | ... | ... | ... | ... | ... | ... |

> Simulation 列：仅部分论文含独立 Simulation 章节，中位数基于含该章节的论文计算；无该章节的论文标 "—"。
```

末尾附 **行业基线总结**：

```markdown
## 行业基线总结（基于 {M} 篇对标论文）

### 方法论规范达标率
- GOF/模型拟合：{N}/{M} 篇报告（{比例}%）
- 稳健性检验：中位数 {X} 项，范围 {min}-{max}
- 嵌套模型对比：{N}/{M} 篇使用
- exp(β) 效应量：{N}/{M} 篇报告
- 行为共演化：{N}/{M} 篇包含
- ...

### 模型创新汇总（从各报告 B3 聚合）
- {创新1}：{N} 篇使用 → 适用性评估
- {创新2}：...

### 图表推荐汇总（从各报告 B4 聚合）
- {图表类型1}：{N} 篇使用 → 适配性评估
- {图表类型2}：...

### 技术型章节结构共性模式（从各报告 A6 聚合）

**Methodology 章节**：
- 常见小节划分：{列出 ≥50% 论文采用的小节名}
- 假设呈现：{N}/{M} 篇集中呈现 vs {N}/{M} 篇分散嵌入
- 模型组织：{N}/{M} 篇按情景分模型 / {N}/{M} 篇按决策阶段分节

**Results/Analysis 章节**：
- 常见报告顺序：{列出最常见的小节排列}
- 命题/定理呈现：{N}/{M} 篇正文完整证明 / {N}/{M} 篇正文sketch+附录 / {N}/{M} 篇纯附录
- 比较静态/Corollary 放置：{N}/{M} 篇在主定理后立即 / {N}/{M} 篇独立成节

**Simulation/Numerical 章节**（若适用）：
- {N}/{M} 篇包含独立数值分析章节
- 常见小节划分：{参数设定→基准情景→敏感性分析→管理启示 等}
- 图表密度：平均 {X} 张/章

### 章节字数基线（基于 {M} 篇对标论文）

| Section | 中位数 | 范围 | 占比 |
|:--------|:-----:|:----:|:----:|
| Introduction | {N} | {min}-{max} | {%} |
| Literature Review | {N} | {min}-{max} | {%} |
| Methodology | {N} | {min}-{max} | {%} |
| Results | {N} | {min}-{max} | {%} |
| Simulation（如适用） | {N} | {min}-{max} | {%} |
| Discussion | {N} | {min}-{max} | {%} |
| Conclusion | {N} | {min}-{max} | {%} |
| **正文合计** | **{N}** | {min}-{max} | 100% |

> 注：字数为估算值（±10%），基于 PDF 页面分析。不含 Abstract、References、Appendix。
> Simulation 行仅基于含该独立章节的论文（{K}/{M} 篇），其余论文标 "—" 不参与统计。
```

### 📌 Checkpoint C1：Git 备份对标分析（不可跳过）

对标分析产出的 benchmark 报告和横向比对表是后续审计的基础数据，必须在进入审计前备份。

```bash
git add structure/3_methodology/benchmark/*_benchmark.md \
       structure/3_methodology/benchmark/cross_comparison.md
git commit -m "Checkpoint: method-audit benchmark complete ({M} papers)"
```

### 2.6 展示比对结果

向用户展示比对的**关键发现**（摘要级别，不展示全表）：

```
📊 对标分析完成（{M} 篇论文）

关键发现：
- GOF: {N}/{M} 篇报告 → {我们的定位}
- 稳健性: 行业中位数 {X} 项，我们 {Y} 项 → {判断}
- ...

论文结构共性模式（详见 cross_comparison.md → 技术型章节结构共性模式）：

  Methodology:
  - {N}/{M} 篇将 Problem Description/Assumptions 独立为首节
  - {N}/{M} 篇按情景/制度分模型，{N}/{M} 篇按决策阶段分节
  - 假设呈现：{集中/分散} 为主流（{N}/{M} 篇）

  Results/Analysis:
  - 常见顺序：{最常见的 3-4 节排列}
  - 证明方式：{主流方式}（{N}/{M} 篇）

  Simulation/Numerical（若适用）：
  - {N}/{M} 篇设独立章节，常见分节：{模式}

可借鉴的模型创新：
- {创新1}（{N} 篇使用）→ {适用性判断}
- ...

可借鉴的图表设计：
- {图表类型1}（{来源论文}）→ {适配性判断}
- ...

完整比对表已保存至 structure/3_methodology/benchmark/cross_comparison.md
```

AskUserQuestion（允许用户在进入审计前做策略性决定）：

```
基于以上对标发现，进入深度审计前有什么想法？
(1) 直接进入审计（推荐）
(2) 先讨论某个维度的策略（如"GOF 要不要报"）
(3) 调整对标论文列表后重新分析
```

用户选 (1) → 进入步骤 3
用户选 (2) → 讨论后再进入步骤 3（讨论结果作为审计的额外约束，如"GOF 不报→审计时不将 GOF 列为问题"）
用户选 (3) → 回到 2.1

---

## 步骤 3：深度审计

**核心价值所在。** 基于对标数据 + Claude 方法论知识 + 论文具体内容，提出方法论问题和对标借鉴建议。

### 3.1 审计信息源（三源融合）

```
审计依据 = 对标数据（步骤 2 的 cross_comparison.md + 行业基线）
         + Claude 方法论知识（理论最佳实践、常见审稿意见）
         + 论文具体内容（methodology.md + results.md 的实际情况）
```

**降级模式**（跳过了步骤 2 时）：仅基于 Claude 知识 + 论文内容，不附带行业基线标注。

### 3.2 审计维度（6 维度，不变）

按以下 6 个维度逐一审查。**每个维度都必须基于论文的具体内容提出质疑，不允许泛泛而谈。**

#### 维度 A：假设合理性

逐个审查 methodology.md 中的每条假设：
- 合理性论证是否充分？有没有遗漏的边界条件？
- 假设之间是否存在矛盾或冗余？
- 放松某个假设后，核心结论是否仍然成立？（识别最脆弱的假设）
- 和该领域的主流假设相比，有没有不一致的地方需要额外论证？

#### 维度 B：模型/方法设定

- 方法选择论证是否令人信服？审稿人会不会建议换成替代方法？
- 变量定义是否清晰、可操作、可复现？
- 公式/方程是否完整？有没有遗漏的约束条件或边界情形？
- 求解方法是否标准且可复现？有没有更优或更常用的替代？

#### 维度 C：参数与数据

- 参数取值是否有明确来源（文献、行业数据、调查）？
- 参数范围是否合理？极端值下模型行为如何？
- 数据样本的代表性和选择偏差如何？
- 缺失数据/异常值的处理方式是否交代？

#### 维度 D：结果可靠性

- 命题/结论的证明逻辑是否严密？有没有跳步？
- 统计检验的选择是否恰当？显著性标准是否一致？
- 结果是否可复现？（信息是否足够让其他研究者复现）
- 效应量 / 经济显著性是否讨论？（不能只看统计显著性）

#### 维度 E：稳健性与内生性

- 已有的稳健性检验是否足够？还缺哪些？
- 内生性问题是否存在？处理策略是否恰当？
- 模型的边界条件：在什么情况下模型/结论会失效？
- 和已有文献的结果一致吗？不一致的地方有没有解释？

#### 维度 F：方法论表述

- 符号使用是否一致（methodology ↔ results ↔ simulation 之间）？
- 术语是否标准？有没有自造术语需要额外定义？
- 技术细节的详略是否得当？（太多→审稿人烦，太少→审稿人质疑）

### 3.3 分级标准（基于行业基线）

**有对标数据时**（正常模式）：

```
🔴 MUST-FIX：本文在该维度明显低于行业基线
  判定方法：对标论文中 ≥60% 做了某项，但我们没做或严重不足
  示例："稳健性检验 1 项，行业中位数 3-5 项"

🟡 STRENGTHEN：本文处于行业基线水平，但有提升空间
  判定方法：对标论文中 30-60% 做了，或我们做了但不够深入
  示例："报告了收敛诊断，但未报告 exp(β) 效应量解读"

🟢 PREEMPT：超出行业基线的加分项，或审稿人可能提的刁钻问题
  判定方法：对标论文中 <30% 做了，但做了能加分
  示例："时间同质性检验——0/8 篇做了，但做了能增强说服力"
```

**硬性规则**：如果一条质疑的行业基线是"0/N 篇做了"（即没有对标论文做过），不得标为 🔴，最高 🟢。

**无对标数据时**（降级模式）：回退为主观判定：
- 🔴 = 审稿人会写 "This is a serious concern"
- 🟡 = 审稿人会写 "The authors should consider..."
- 🟢 = 审稿人会写 "It would be helpful if the authors could clarify..."

### 3.4 审计产出（两类）

#### 类型一：方法论问题（MF / ST / PM）

格式与行业基线标注：

```
### MF-1: {一句话标题}

**位置**: methodology.md → {具体章节/假设/公式编号}
**行业基线**: {N}/{M} 篇对标论文做了此项 → {行业惯例/我们的短板/加分项}
**质疑**: Reviewer 可能会问："{模拟审稿人的具体措辞，用英文}"
**分析**: {为什么这是一个问题，用中文解释}
**建议**: {具体的应对方案}
```

质量控制（保留）：
- 每条质疑必须**指向 md 文件中的具体位置**
- 每条质疑必须包含**审稿人的具体措辞**
- 如果一条质疑**适用于任何同类论文**，则不够具体，删除或重写
- 总数控制：🔴 不超过 5 条，🟡 不超过 8 条，🟢 不超过 5 条

#### 类型二：对标借鉴建议（SO）

基于步骤 2 的横向比对（表 3 + 行业基线总结），提出三类借鉴建议：

**SO-结构**：章节组织优化（来源：各报告 B2 → 表 3 结构列）

```
### SO-S1: {一句话标题}

**对标发现**: {N}/{M} 篇对标论文采用 {某种组织方式}
**当前状况**: 我们的 {章节} 目前 {如何组织}
**建议**: {具体调整方案——改什么标题、拆分/合并什么小节、调整什么顺序}
```

**SO-模型**：模型设计借鉴（来源：各报告 B3 → 行业基线模型创新汇总）

```
### SO-M1: {一句话标题}

**来源论文**: {citation_key}（{期刊}, {年份}）
**创新做法**: {该文的具体做法}
**适用性**: {为什么适用于本文，如何纳入}
```

**SO-图表**：图表设计借鉴（来源：各报告 B4 → 行业基线图表推荐汇总）

```
### SO-F1: {一句话标题}

**来源论文**: {citation_key}（{期刊}, {年份}）
**图表描述**: {该图/表的内容和呈现方式}
**适配分析**: {为什么适配本文数据，建议如何借鉴}
```

- SO 条目统一标记为 📐，不分 🔴/🟡/🟢
- 数量控制：SO-结构 ≤3 条，SO-模型 ≤3 条，SO-图表 ≤3 条
- **无对标数据时**（降级模式）：不产出 SO 条目

---

## 步骤 4：生成审计报告 + 展示摘要

### 4.1 报告格式

将审计结果写入 `structure/3_methodology/benchmark/method_audit_report.md`：

```markdown
# Method Audit Report — {PAPER_TITLE}

> Generated: {date}
> Method: {METHOD_DETAIL}
> Target journal: {TARGET_JOURNAL}
> Benchmark: {M} 篇对标论文 | 数据: structure/3_methodology/benchmark/cross_comparison.md
> Audited files: methodology.md, results.md[, simulation.md]

---

## Baseline Check

{步骤 1 的基线结果}

---

## 🔴 MUST-FIX

### MF-1: {标题}

**位置**: ...
**行业基线**: ...
**质疑**: ...
**分析**: ...
**建议**: ...

---

## 🟡 STRENGTHEN

### ST-1: {标题}
（同上格式）

---

## 🟢 PREEMPT

### PM-1: {标题}
（同上格式，建议部分为可直接插入论文的化解措辞）

---

## 📐 对标借鉴

### 结构优化
SO-S1: ...

### 模型借鉴
SO-M1: ...

### 图表借鉴
SO-F1: ...

---

## Summary

| 级别 | 数量 | 涉及维度 |
|------|------|---------|
| 🔴 MUST-FIX | {n} | {A/B/C/D/E/F} |
| 🟡 STRENGTHEN | {n} | {A/B/C/D/E/F} |
| 🟢 PREEMPT | {n} | {A/B/C/D/E/F} |
| 📐 对标借鉴 | {n} (结构{a} + 模型{b} + 图表{c}) | — |
```

### 📌 Checkpoint C2：Git 备份审计报告（不可跳过）

审计报告是后续逐条处理的依据，生成后立即备份。

```bash
git add structure/3_methodology/benchmark/method_audit_report.md
git commit -m "Checkpoint: method-audit report generated"
```

### 4.2 展示摘要（仅标题，不展开细节）

```
📋 方法论审计完成 — {PAPER_TITLE}

| 级别 | 数量 |
|------|------|
| 🔴 MUST-FIX | {x} |
| 🟡 STRENGTHEN | {y} |
| 🟢 PREEMPT | {z} |
| 📐 对标借鉴 | {w} (结构{a} + 模型{b} + 图表{c}) |

条目列表（按严重等级排序）：
🔴 MF-1: {标题}
...
🟡 ST-1: {标题}
...
🟢 PM-1: {标题}
...
📐 SO-S1: {标题}（结构）
📐 SO-M1: {标题}（模型）
📐 SO-F1: {标题}（图表）
...

报告已保存至 structure/3_methodology/benchmark/method_audit_report.md
```

### 4.3 进入处理流程

AskUserQuestion：

```
接下来逐条处理。选择处理方式：
(1) 从 🔴 开始逐条处理（推荐）
(2) 指定条目（输入编号如 "ST-3" 或 "MF-1, SO-2, PM-3"）
(3) 暂不处理，先看完整报告
```

用户选 (1) → 构建处理队列 `{QUEUE}` = 全部条目，按 🔴→🟡→🟢→📐（📐 内部按 SO-S→SO-M→SO-F）排序
用户选 (2) → 构建处理队列 `{QUEUE}` = 仅包含用户指定的条目（按严重等级排序）
用户选 (3) → 结束。用户可稍后重新运行 `/method-audit`（可重复运行机制会跳过已 Fixed 的条目）

---

## 步骤 5：逐条交互处理循环

**核心交互模式**：对每条质疑走完 **展示→分类→方案→确认→执行** 的闭环后才进入下一条。

```
SET progress = 0
SET total = len({QUEUE})

FOR each item IN {QUEUE}:
  progress += 1

  # ────────────────────────────────
  # 5.1 展示条目细节
  # ────────────────────────────────

  显示该条目的完整内容（从 report 中提取）：
  ```
  ══════════════════════════════════════
  ▶ [{progress}/{total}] {severity} {ID}: {标题}
  ══════════════════════════════════════

  **位置**: {位置}
  **行业基线**: {基线标注}
  **质疑**: Reviewer 可能会问："{英文措辞}"
  **分析**: {中文分析}
  **建议**: {建议概述}
  ```

  SO 条目展示格式：
  ```
  ══════════════════════════════════════
  ▶ [{progress}/{total}] 📐 {ID}: {标题}
  ══════════════════════════════════════

  **对标发现**: {发现}
  **当前状况**: {现状}
  **建议**: {调整方案}
  ```

  # ────────────────────────────────
  # 5.2 分类 + 生成处理方案
  # ────────────────────────────────

  自动判断条目的处理类型（由 Agent 判断，不需要用户选择类型）：

  **TYPE A — 改 md**：可通过在 md 文件中增补/修改文字解决。
  ```
  📝 修改方案：
    文件: {文件路径}
    位置: {具体位置描述}
    操作: {新增/修改/追加}（约 {N} 字）
    内容预览:
    > {需要补充的具体中文文字或公式，供用户审核}
  ```

  **TYPE B — 跑分析**：需要额外运行统计分析（R/Python）。
  ```
  🔬 需要补充分析：
    分析内容: {具体需要什么分析}
    数据/脚本: {检查 data/ 下是否有现成脚本/数据，列出可用资源}
    执行方式:
      - 自动: {如果能自动跑，展示 R 脚本方案}
      - 手动: {如果需要用户手动，列出具体步骤}
    分析完成后: {拿到结果后如何更新 md}
  ```

  **TYPE C — 纯论证**：需要在 md 中补充方法论论证段落。
  ```
  📝 论证补充方案：
    文件: {文件路径}
    位置: {具体位置描述}
    操作: 新增论证段落（约 {N} 字）
    内容预览:
    > {论证草稿，中文}
  ```

  注：TYPE A = 简短补充（一两句话），TYPE C = 构建论证逻辑的较长段落。
  SO 条目固定为 TYPE A（改 md 的结构/标题/组织方式）。
  **SO 条目涉及表格时**：如果 md 中已有表格素材，在处理循环中即时写入 `structure/figures_tables/tables.tex` + 更新 `index.md` 状态，遵循项目 CLAUDE.md 的"表格即时落地"规则。不得将表格制作推迟到 /pen-draft。

  # ────────────────────────────────
  # 5.3 用户确认
  # ────────────────────────────────

  **TYPE A / TYPE C** 的 AskUserQuestion：
  ```
  (1) 确认执行
  (2) 调整方案内容
  (3) 跳过此条
  (4) 停止处理，退出循环
  ```

  **TYPE B** 的 AskUserQuestion：
  ```
  (1) 自动执行（Claude 生成并运行脚本）
  (2) 手动执行（Claude 生成脚本，你自己跑，结果稍后补入 md）
  (3) 调整分析方案
  (4) 跳过此条
  (5) 停止处理，退出循环
  ```

  **通用处理逻辑**：
  - 确认执行 → 进入 5.4 执行
  - 调整 → **循环**：用户提出修改意见 → 调整方案 → 再次展示 → 直到用户确认
  - 跳过 → 在 report 中标记 `⏭️ Skipped`，进入下一条
  - 停止 → 退出循环，进入步骤 6

  # ────────────────────────────────
  # 5.4 执行修改
  # ────────────────────────────────

  **TYPE A / TYPE C**：使用 Edit 工具修改对应 md 文件。
  **TYPE B**：
    - 用户选"自动执行"：生成 R/Python 脚本 → 执行 → 等待结果 → 用 Edit 将结果写入 md
    - 用户选"手动执行"：生成脚本并保存到 `data/scripts/`，在 report 中标记 `⏳ Waiting for user analysis`，进入下一条（不阻塞循环）

  修改完成后：
  - **单条修复后一致性检查**：每次修改 `_dev.md` 后，立即检查本次修改是否导致同一文件内其他位置出现不一致（如改了符号定义但后续推导仍用旧符号、改了假设编号但命题引用未同步等）。发现不一致则当场修复，不留到后面。
  - 更新 `structure/3_methodology/benchmark/method_audit_report.md`，在该条目的 `**建议**:` 之后追加状态标记行：
    - `**状态**: ✅ Fixed ({date})`
    - `**状态**: ⏭️ Skipped`
    - `**状态**: ⏳ Waiting for user analysis`
  - 显示进度确认：
  ```
  ✓ [{progress}/{total}] {ID} done
  ```

  # ────────────────────────────────
  # 5.5 严重等级切换门
  # ────────────────────────────────

  当队列中当前级别的最后一条被处理（无论结果是 Fixed、Skipped 还是 Waiting），且下一级别还有条目时，AskUserQuestion：

  ```
  ══════════════════════════════════════
  {当前级别} 全部处理完毕（{n}/{n}）
  接下来是 {下一级别}（{m} 条）。继续？
  ══════════════════════════════════════

  (1) 继续处理
  (2) 停止，剩余条目稍后处理
  ```

  用户选 (2) → 退出循环，进入步骤 6

  注：📐 对标借鉴排在 🟢 之后，切换门在 🟢→📐 之间触发。📐 内部三个子类别（SO-S/SO-M/SO-F）之间不触发切换门。

END FOR
```

---

## 步骤 5.6：全文一致性扫描（不可跳过）

处理循环结束后、生成总结前，对所有被修改的 `_dev.md` 文件做一次**系统性全文一致性扫描**：

1. **文件内一致性**：逐个扫描每个被修改的 `_dev.md`，检查：
   - 符号定义与后续引用是否一致（如 $\alpha$ 的定义是否与所有使用处匹配）
   - 假设编号是否连续、引用是否正确
   - 命题编号是否连续、证明中引用的命题号是否正确
   - 公式编号（tag）是否连续、交叉引用是否正确
   - 修改处的前后文逻辑是否衔接

2. **文件间一致性**：跨 `_dev.md` 文件检查（同步骤 0.3 的跨文件一致性检查，但基于修改后的最新内容重新扫描）

3. **发现不一致**：直接修复（不需要再走用户确认循环），修复后在总结中列出。

---

### 步骤 5.7：技术型章节结构确认

一致性扫描完成后，为 `/method-end` 的后续凝练工作锁定成稿 md 的章节结构。

#### 5.7.1 收集结构信息

读取以下三类信息：

1. **Benchmark 结构共性模式**：从 `structure/3_methodology/benchmark/cross_comparison.md` 提取：
   - "技术型章节结构共性模式" 全文（这是结构建议的首要依据）
   - 表 3 中各对标论文的逐章 `###`/`####` 层级结构
   - SO-结构类建议（如有）
2. **Idea 故事线**：从 `idea.md` §3（方法论选择）提取故事线总览和结论群架构
3. **现有成稿 md 结构**：读取每个技术型成稿 md（`methodology.md`, `results.md`, `simulation.md`——仅存在的文件）的当前 `###`/`####` 标题

#### 5.7.2 生成结构建议

综合以上信息，为每个技术型成稿 md 生成建议的 `###`/`####` 层级结构。

**建议依据优先级**：
1. **Benchmark 结构共性模式**（首要依据）：直接引用 cross_comparison.md 中 "技术型章节结构共性模式" 的统计结论，采用 ≥50% 对标论文使用的小节划分方式作为默认建议
2. Idea.md 的故事线架构（结论群→章节映射）
3. _dev.md 的实际内容分布（确保每个 subsection 有足够素材支撑）

> **注意**：在建议输出中，每条结构调整须标注 benchmark 依据（如 "4/6 篇对标论文采用此分节方式"），使用户能判断建议的可信度。

**输出格式**（逐章展示）：

```
📐 技术型章节结构建议

═══ methodology.md ═══
现有结构:
  ### 3.1 Methodology
  ### 3.2 Problem description and assumptions
  ### 3.3 Model N: Joint liability under traditional regime
  ### 3.4 Model B: Precise attribution under blockchain

建议结构:
  ### 3.1 Methodology
  ### 3.2 Problem description and assumptions
    #### Supply chain structure and quality defect process
    #### Game sequence and information structure
    #### Assumptions
  ### 3.3 Model N: Joint liability under traditional regime
    #### Payoff functions
    #### Nash equilibrium of the subgame
    #### GC's optimal contract
  ### 3.4 Model B: Precise attribution under blockchain
    #### Payoff functions under precise attribution
    #### Equilibrium solution
    #### Unconstrained equivalence

调整说明:
- {为什么这样调整，引用 benchmark 依据}

═══ results.md ═══
...

═══ simulation.md ═══
...
```

#### 5.7.3 交互确认

AskUserQuestion 逐章确认。用户可以：
- 接受建议结构
- 修改标题措辞、增删 subsection/subsubsection
- 调整层级（`###` ↔ `####`）

**循环**：用户不满意 → 修改结构 → 再次展示 → 直到用户确认。逐章确认，不要求一次性确认全部。

#### 5.7.4 写入成稿 md

用户确认后，将结构写入对应的成稿 md 文件：
- 替换 `## 正文要点` 下的所有 `###`/`####` 标题
- 每个标题下保留 `TODO: 从 {X}_dev.md 凝练`（如原来已有 TODO）或保留已有内容（如果之前已有部分填充）
- **不修改** `## 必备元素` 和 `## 引用池` 部分

> 写入的文件将纳入 Checkpoint C3 的 git add 范围。

---

### 步骤 5.8：各 section 字数目标确认

结构确认完成后，基于 benchmark 字数基线确认各正文 section 的字数目标，写入各章节 md。

#### 5.8.1 识别正文 section 列表

根据 `{METHOD_TYPE}` 确定需要分配字数的 section：

| METHOD_TYPE | Sections |
|:------------|:---------|
| modeling | Introduction, Literature Review, Methodology, Results, Simulation, Discussion（6 个） |
| survey-sem | Introduction, Literature Review, Methodology, Results, Discussion（5 个） |
| panel-regression | Introduction, Literature Review, Methodology, Results, Discussion（5 个） |

**不含** Conclusion 和 Abstract（由 /finalize 处理，字数由期刊规范决定）。

进一步验证：扫描 `structure/` 目录，确认每个 section 对应的 md 文件存在。不存在的 section → 从列表中移除并提示用户。

#### 5.8.2 读取字数基线

从 `structure/3_methodology/benchmark/cross_comparison.md` 的 `### 章节字数基线` 提取各 section 的中位数和范围。

**无对标数据时**（降级模式 / cross_comparison.md 中无字数数据）：
使用 Claude 知识中该期刊/领域的典型字数分布作为参考，明确标注"⚠️ 非 benchmark 依据，基于 Claude 知识估算"。

#### 5.8.3 生成字数建议

为每个 section 生成目标字数建议：

- **默认值** = benchmark 中位数（取整到最近的 50）
- **调整依据**（如某项偏离中位数，须在"调整理由"列说明）：
  - 本文某 section 内容密度明显偏离 benchmark 均值（如 Results 含行为共演化分析，benchmark 中罕见）
  - 目标期刊有明确的总字数/页数限制 → 总字数需适配，各 section 等比缩放
  - 某 section 的 subsection 数量显著多于/少于 benchmark → 按比例调整

#### 5.8.4 展示并确认

```
📊 各 section 字数目标（基于 {M} 篇 benchmark 论文）

| Section | Benchmark 中位数 | Benchmark 范围 | 建议目标 | 调整理由 |
|:--------|:---------------:|:-------------:|:-------:|:---------|
| Introduction | {N} | {min}-{max} | {N} | — |
| Literature Review | {N} | {min}-{max} | {N} | — |
| Methodology | {N} | {min}-{max} | {N} | {如有} |
| Results | {N} | {min}-{max} | {N} | {如有} |
| {仅 modeling:} Simulation | {N} | {min}-{max} | {N} | {如有} |
| Discussion | {N} | {min}-{max} | {N} | {如有} |
| **正文合计** | **{N}** | | **{sum}** | |

注：不含 Conclusion（由 /finalize 处理）和 Abstract。

你可以调整各 section 的目标字数。确认后写入各章节 md。
```

AskUserQuestion 等待用户确认。**循环**：用户不满意 → 修改 → 再次展示 → 直到确认。

#### 5.8.5 写入各章节 md

用户确认后，遍历以下文件（仅存在的文件），用 Edit 修改头部的 `目标字数` 行：

| Section | 文件路径（Glob 匹配） |
|:--------|:-------------------|
| Introduction | `structure/1_introduction/introduction.md` |
| Literature Review | `structure/2_literature/literature.md` |
| Methodology | `structure/3_methodology/methodology.md` |
| Results | `structure/4_results/results.md` |
| Simulation | `structure/*simulation*/simulation.md`（仅 modeling 类型） |
| Discussion | `structure/*discussion*/discussion.md` |

替换规则：
- 匹配 `> 目标字数:` 开头的行
- 替换为 `> 目标字数: {N} words`（保留该行后面的括号说明，如 "（由 /pen-outline 分配各子节字数）"）
- 如果是叙述型章节：`> 目标字数: {N} words（由 /pen-outline 分配各子节字数）`
- 如果是技术型章节：`> 目标字数: {N} words`

> 写入的文件将纳入 Checkpoint C3 的 git add 范围。

显示确认：
```
✓ 字数目标已写入 {N} 个章节 md
  - introduction.md: {N} words
  - literature.md: {N} words
  - methodology.md: {N} words
  - results.md: {N} words
  {仅 modeling:} - simulation.md: {N} words
  - discussion.md: {N} words
```

---

## 步骤 6：处理完成总结

所有条目处理完毕（或用户主动退出循环）后，输出总结：

```
📋 方法论审计处理完成

| 级别 | 总数 | 已修复 | 跳过 | 待处理 |
|------|------|--------|------|--------|
| 🔴 MUST-FIX | {x} | {a} | {b} | {c} |
| 🟡 STRENGTHEN | {y} | {d} | {e} | {f} |
| 🟢 PREEMPT | {z} | {g} | {h} | {i} |
| 📐 对标借鉴 | {w} | {j} | {k} | {l} |

已修改文件：
- {file1}（{n} 处修改）
- {file2}（{m} 处修改）

{如有 TYPE B 待用户手动跑的条目}:
⏳ 等待用户分析：
- {ID}: {描述}，脚本已生成于 {路径}

💡 可重新运行 /method-audit 检查剩余问题

📐 技术型章节结构确认：{已确认/未执行}
{如已确认，列出各章节确认的 subsection 数量}

📊 章节字数目标：{已确认/未执行}
{如已确认，逐行列出各 section 确认的目标字数}
```

更新 `structure/3_methodology/benchmark/method_audit_report.md` 末尾的 Summary 表，反映最新处理状态。

### 📌 Checkpoint C3：Git 备份审计修复（不可跳过）

处理循环结束后，将所有被修改的文件统一备份。包含修改后的章节 md、更新后的审计报告、以及稳健性检验脚本/结果（如有 TYPE B 条目）。

```bash
git add structure/3_methodology/methodology_dev.md \
       structure/4_results/results_dev.md \
       structure/5_simulation/simulation_dev.md \
       structure/3_methodology/methodology.md \
       structure/4_results/results.md \
       structure/5_simulation/simulation.md \
       structure/1_introduction/introduction.md \
       structure/2_literature/literature.md \
       structure/*discussion*/discussion.md \
       structure/3_methodology/benchmark/method_audit_report.md \
       data/robustness/
git commit -m "Checkpoint: method-audit fixes applied"
```

> 仅 `git add` 实际被修改的文件。如果某些文件未被修改（如 simulation_dev.md 未涉及），不加入 commit。成稿 md 文件（methodology.md 等）在步骤 5.7 结构确认后可能被修改，也应纳入。叙述型章节 md（introduction.md、literature.md、discussion.md）在步骤 5.8 字数确认后可能被修改，也应纳入。

---

## 全局约束

### 输出语言
- 审计报告的分析、建议、修改内容用**中文**
- 模拟审稿人措辞（"Reviewer 可能会问"）用**英文**（因为目标期刊是英文）
- 修改方案中的补充内容用**中文**（因为 md 是中文技术规格书，后续由 sci-writer 翻译）

### 不越界
- **只审方法论层面**：假设、模型、数据、检验、证明、参数。不审 RQ-方法匹配度、贡献可支撑性、写作质量（这些是其他 skill 的职责）
- **不修改技术内容的实质**：审计可以建议"补充边界条件讨论"，但不能擅自修改公式、命题或数值结果
- **不替代人工判断**：对于需要额外跑分析（如补稳健性检验）的建议，只指出需要什么，不替用户编造结果

### 对标分析配置
- **工作目录**：`structure/3_methodology/benchmark/`
- **subagent prompt 模板**按 `{METHOD_TYPE}` 差异化（见步骤 2.4）
- **对标数据缓存**：`cross_comparison.md` 时间戳 < 7 天时可复用，避免重复跑 subagent

### 可重复运行
- 支持在修改后重新运行 `/method-audit`，此时应读取上一次的 `method_audit_report.md`，识别各条目的状态标记：
  - `✅ Fixed` → 不再重复提出（除非修改后引入了新问题）
  - `⏭️ Skipped` → 重新提出（用户上次跳过，不等于已解决）
  - `⏳ Waiting for user analysis` → 检查用户是否已补充分析结果到 md 中。已补充 → 标记为 Fixed；未补充 → 保持原状重新提出
  - 无标记（未处理到的条目）→ 重新提出
- 对标数据（cross_comparison.md）如 < 7 天则自动复用（步骤 2.0 判定）
