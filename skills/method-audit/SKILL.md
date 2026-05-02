---
description: "方法论审计 + 章节打磨放行：对标行业实践 → 审计方法问题 → 重组章节结构 → 字数分配 → 写作蓝图（reader journey + 跨章节过渡）→ 必备元素验收 → 阶段转换 foundation→drafting（Method Audit & Finalization）"
---

# Method Audit — 方法论审计与章节打磨放行

对标同方法的已发表论文建立行业基线，审计技术型章节 md（X.md）的方法论问题，逐条交互修复，重组章节结构，分配字数，验收必备元素，最后转换项目阶段 `foundation → drafting`。

**核心原则**：
1. **final-md-first**：审计对象是技术型章节的成稿 md（`methodology.md` / `results.md` / `simulation.md`），不再依赖 `_dev.md`。X.md 是技术型章节的唯一权威源。
2. **对标先于审计**：先看行业怎么做，再评判我们做得够不够。没有对标数据的审计是盲审。
3. **具体性**：每条质疑必须指向 md 中的具体位置，且不能"换论文仍成立"。
4. **对标借鉴是必做项**：从对标论文中学习章节结构、模型设计技巧和图表呈现方式。
5. **打磨即放行**：审计修复完成后顺势完成结构确认 + 字数分配 + **写作蓝图** + 必备元素验收 + 阶段转换，X.md 直接进入 `/technical` 可读状态。

**与 `/idea-refine` 的边界**：
- `/idea-refine` = **主编视角，多阶段迭代**审视：方法工作量 / 创新性 / 贡献 / 方法漏洞（管「想什么」+「技术实现完整性」）
- `/method-audit` = **一次性闸门**：对标 benchmark + subsection 结构 + 字数分配 + **读者认知路径** + **跨章节过渡**（管「怎么写 / 怎么摆 / 字数多少 / 读者怎么读」）

灰色地带分工：「**应不应该**用某变量/方法」→ `/idea-refine`；「**怎样定义**符号、放在哪一节、用什么图表展示」→ `/method-audit`。

**权威源优先级**（冲突时遵循）：
1. `manuscript.tex`（最终插入后）
2. `X.md`（manuscript 插入前为最高权威）
3. `idea.md`、本 skill 产出的 `method_audit_report.md`、修改计划
4. `data/` 输出、figure/table 注册表、可复现脚本
5. `_dev.md`（如存在，仅作历史归档/溯源参考，不主导任何决策）

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

### 0.3 读取技术型章节成稿 md

按 `$ARGUMENTS` 和 `{METHOD_TYPE}` 读取**技术型章节成稿 md**（`X.md`，唯一权威源）：

| 文件 | 路径 | 条件 |
|------|------|------|
| methodology.md | `structure/3_methodology/methodology.md` | 始终读取 |
| results.md | `structure/4_results/results.md` | `$ARGUMENTS` 为空或含 "results" |
| simulation.md | `structure/5_simulation/simulation.md` | 仅 modeling 类型 + `$ARGUMENTS` 为空或含 "simulation" |

> **审计对象是成稿 md（`X.md`）**——完整的技术内容（公式、命题、假设、证明骨架、引用）应直接落在这里。审计修复也回写到 X.md。审计完成后 X.md 即可进入 `/technical`（基于 `## 写作蓝图` + `## 正文要点` 直接生成 tex）。

**空文件检测**（分级豁免）：

1. **单章节模式**（`$ARGUMENTS` 指定了具体章节，如 `/method-audit results`）：如该章节 X.md 的 `## 正文要点` 区块仍全是 TODO（无实质技术内容） → 停止并提示用户先填充内容：

   ```
   ⚠️ {文件名} 的 ## 正文要点 仍为 TODO，无法审计。
   请先在 X.md 中填充正文要点（公式、假设、命题、证明骨架等），再运行 /method-audit {section}。
   ```

2. **多章节模式**（`$ARGUMENTS` 为空）：对每个 X.md 检查 `## 正文要点` 区块：
   - **至少有 1 份 X.md** 含实质内容 → 流程继续；全 TODO 的 X.md 标记为 `placeholder-pending`，跳过其内容审计（步骤 1 基线检查 / 步骤 3 深度审计），但**仍参与** 5.7（结构规划）/ 5.8-5.9（字数分配）/ 6.5（必备元素验收必然 fail，从而正确触发 7.1 阻塞阶段转换）
   - **所有 X.md 都全 TODO** → 停止：项目尚未起步，应先填充至少 methodology.md 的正文要点
   
   > 此分级豁免与 5.7.4-B 配套：5.7.4-B 创建的 placeholder 文件全是 TODO，第二次跑 method-audit 时由本规则豁免，不会 deadlock。

**兼容兜底（迁移期一次性）**：扫描每个章节目录是否仍存在旧版 `*_dev.md` 文件。若存在 → **警告但不阻塞**：

```
⚠️ 检测到遗留过程文件：{X_dev.md 路径列表}
本 skill 已切换为 final-md-first 模式，过程文件不再作为审计依据。
建议：将 _dev.md 内容（如仍有用）手工合并到 X.md 后删除文件，或保留作为历史归档。
本次审计将忽略 _dev.md 内容。
```

**跨文件一致性检查**：扫描所有 `X.md`，检查以下元素是否一致：
- 符号名称和定义（methodology.md 定义 → results.md 和 simulation.md 引用）
- 假设编号（methodology.md 定义 → results.md 引用）
- 命题编号（results.md 定义 → simulation.md 引用；discussion 在后续 `/narrative` 阶段直接写入 manuscript.tex，不在本 skill 一致性检查范围）
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

从各成稿 md（如 `methodology.md`）的 `## 必备元素` 读取**元素清单名称和要求**，然后在**同一份 X.md** 的 `## 正文要点` 区块中搜索每个元素是否有实质内容（非 TODO）。同时检查以下维度是否覆盖：

**modeling**：
- [ ] methodology.md: 方法选择论证（为什么用此方法）
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

按以下顺序检查，命中即按对应走法处理：

| 检查 | 条件 | 走法 |
|:----|:----|:----|
| A. 前置 | `structure/2_literature/citation_pool/` 不存在 | 🔴 阻断：提示先跑 `/lit-plan → /lit-review → /lit-tag → /lit-pool`，exit |
| B. 缓存 | `benchmark/cross_comparison.md` 存在且 < 7 天 | AskUserQuestion：(1) 复用（推荐，若无 per-paper 子目录则**先读 `benchmark_papers.ris` 取 citation key 列表**，再补跑 2.3.2+2.3.3，进 2.6） (2) 重新分析 → 继续 C |
| C. 引用池 | METHOD/COMP 标签全空 | AskUserQuestion：(1) 手动指定候选 → 进 2.1 (2) 跳过步骤 2，步骤 3 走降级纯知识审计 |
| D. 正常 | 以上都不命中 | 进入 2.1 |

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

### 2.3 检测 PDF + 自动组织 + 图表提取

#### 2.3.1 检测 PDF

Agent 用 Glob 检测 `structure/3_methodology/benchmark/*.pdf`（根目录）和 `structure/3_methodology/benchmark/*/*.pdf`（已组织的子目录），汇总所有 PDF。

**如果部分 PDF 缺失**：允许 ≥3 篇即可继续，行业基线的可信度注明样本量（如"基于 5/8 篇论文"）。

#### 2.3.2 自动组织为 per-paper 子目录

将 benchmark 目录从扁平结构重组为**每篇论文一个子目录**（以 citation key 命名）：

```
benchmark/
├── cao2017d/                    # citation key 为目录名
│   ├── Cao et al. - 2017 - ....pdf   # PDF 移入
│   ├── cao2017d_benchmark.md          # 精读报告（Step 2.4 生成）
│   ├── figures/                       # 自动提取的 figure
│   │   ├── fig1.png
│   │   └── fig2.jpeg
│   └── tables/                        # 自动提取的 table
│       ├── table1.png
│       └── table4.png
├── gui2025u/
│   ├── ...
├── _visual_index.md              # 全局图表索引（自动生成）
├── cross_comparison.md           # 横向比对表（Step 2.5 生成）
├── method_audit_report.md        # 审计报告（Step 4 生成）
└── benchmark_papers.ris          # RIS 清单（Step 2.2 生成）

# 另外在 structure/2_literature/ 下生成：
# method_landscape.md             # 方法景观文件（Step 2.5.1 生成，/finalize 保留）
```

**组织逻辑**：
1. 遍历 `benchmark/` 根目录下的 PDF 文件
2. 根据文件名中的第一作者姓氏匹配 citation key
3. 创建 `benchmark/{citation_key}/` 子目录（含 `figures/` 和 `tables/`）
4. 将 PDF 移入对应子目录
5. 如果根目录已有 `{citation_key}_benchmark.md`，也移入子目录
6. 如果 PDF 已在正确的子目录中，跳过

> **Unicode 注意**：文件名匹配时须用 `unicodedata.normalize('NFC', ...)` 处理特殊字符（如 `ç`、`ü`），避免编码不一致导致匹配失败。对 fitz.open() 传入的路径使用 `os.listdir()` 扫描到的实际文件名，不要使用硬编码字符串。

#### 2.3.3 自动提取图表（Visual Extraction）

对每个子目录中的 PDF，使用 PyMuPDF（`fitz`）自动提取 figure 和 table 为图片文件。

**跳过已提取**：如果某个子目录的 `figures/` 或 `tables/` 下已有文件，跳过该论文的提取（避免重复渲染）。仅对 figures/ 和 tables/ 均为空的子目录执行提取。

**前置条件检查**：
```python
import fitz  # PyMuPDF
```
如果 `import fitz` 失败，跳过图表提取，提示用户安装：`pip install pymupdf`

**提取逻辑**：

1. **定位 table 页**：扫描每页文本，正则匹配 `^Table\s+(\d+)[.\s]`（行首），记录 `{table_num: page_idx}`，仅保留每个 table 编号首次出现的页
2. **定位 figure 页**：正则匹配 `^Fig(?:ure)?\.?\s*(\d+)[.\s]`，同理
3. **提取 table**：统一使用页面渲染（`page.get_pixmap(matrix=fitz.Matrix(2, 2))`），保存为 `tables/table{N}.png`
4. **提取 figure**（两种策略，自动选择）：
   - **优先提取嵌入位图**：`page.get_images()` → `doc.extract_image(xref)` → 过滤掉 width < 300 或 height < 300 的装饰图（期刊 logo、CC 标志等）
   - 同一页有多个有效嵌入图时，按索引添加后缀：`fig{N}_a.{ext}`、`fig{N}_b.{ext}`
   - **Fallback 渲染整页**：如果该 figure 页没有有效嵌入图（矢量图 / LaTeX 绘制），使用 `get_pixmap(matrix=Matrix(2,2))` 渲染，保存为 `figures/fig{N}.png`

5. **生成全局图表索引** `benchmark/_visual_index.md`：

```markdown
# Benchmark Visual Index

> Auto-generated from benchmark PDFs. Figures and tables for cross-paper visual comparison.

## {citation_key}

| Type | # | Page | File | Size | Method |
|:-----|:--|:-----|:-----|:-----|:-------|
| figure | 1 | p3 | `{key}/figures/fig1.jpeg` | 1423x450 | embedded |
| table | 3 | p7 | `{key}/tables/table3.png` | 1191x1588 | rendered |
...
```

**提取完成后显示摘要**：
```
📸 图表提取完成（{M} 篇论文）
  共提取: {F} 个 figure + {T} 个 table
  索引: benchmark/_visual_index.md

  {key1}: {f1} figs + {t1} tables
  {key2}: {f2} figs + {t2} tables
  ...
```

### 2.4 并行 subagent 分析

每篇 PDF 启动一个 subagent（`run_in_background: true`，最多 8 个并行），使用标准化提取模板。

**Subagent prompt 模板**：

```
你是一个 {METHOD_TYPE} 方法论审计专家。请阅读以下论文 PDF，生成结构化的方法论对标报告。

**论文**: {PDF 路径}（格式: `benchmark/{key}/{pdf_filename}`）
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
8. **各 section 字数统计**：⚠️ **Deprecated since 2026-05-02** —— step 5.8 已改为硬编码（2-section 4500 / 3-section 5000 words），不再读取 benchmark 字数估算。本项 **subagent 可跳过**（节省时间）；如保留输出仅作历史归档参考，**不要在审计决策中消费**。

   <details><summary>历史 prompt（不再调用）</summary>

   统计论文每个一级 section 的估算字数（Introduction, Literature Review,
   Methodology/Research Design, Results/Analysis, Discussion, Conclusion，
   以及 Simulation/Numerical Analysis 如存在）。
   - 统计方法：按 section 起止页计算正文面积，扣除图表、公式块、表格占位面积，
     按每页约 600-800 词（单栏）或 1000-1200 词（双栏）估算
   - 输出格式（如执行）：见原表
   注：字数为估算值（实证发现偏差 -35% 到 +119%，路线不可靠）。

   </details>

{METHOD_TYPE 差异化补充——见下方}

## B. 对标评估（每条须结合"我们论文的写作现状"做适配性判断）

### B1. 方法论对比
该文 vs 本文在模型设定、诊断检验、报告规范上的关键差异，明确指出我们的优势和短板。

### B2. 结构借鉴
基于 A6，该文的章节组织中哪些安排值得本文采纳？哪些是我们缺失的？

### B3. 模型创新
基于 A3，该文有什么独特的模型设计技巧（效应选择、变量构造、估计策略、诊断方法）？逐条评估是否适用于本文，如适用则说明如何纳入。

### B4. 图表借鉴
基于 A7 和提取的图表图片（`benchmark/{citation_key}/figures/` + `benchmark/{citation_key}/tables/`），哪些图表设计出色（说明好在哪里）？逐条分析是否适配本文数据和结果，如适配则建议如何借鉴。可直接 Read 图片文件进行视觉对比。

报告用中文写，技术术语保留英文。
写入: structure/3_methodology/benchmark/{citation_key}/{citation_key}_benchmark.md
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

**表 4：各章节字数对比** —— ⚠️ **Deprecated since 2026-05-02**：5.8 已改硬编码，本表不再生成（数据来源不可靠）。如旧版 cross_comparison.md 中存在此表，5.8 不消费其数字。

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

### 图表推荐汇总（从各报告 B4 聚合，结合视觉对标）
- {图表类型1}：{N} 篇使用 → 适配性评估
- {图表类型2}：...

> **视觉对标**：生成图表推荐汇总时，主 agent 须 Read `benchmark/{key}/tables/` 和 `benchmark/{key}/figures/` 中的核心图表图片（尤其是 SAOM/SEM 结果表、网络拓扑图、GOF 图等方法论核心图表），进行跨论文视觉对比，识别报告格式差异（如哪些报告了 exp(β)、哪些用了星号标注、表格分栏方式等），将视觉发现融入图表推荐。图片路径见 `benchmark/_visual_index.md`。

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

### 章节字数基线 —— ⚠️ **Deprecated since 2026-05-02**

5.8 改为硬编码（2-section 4500 / 3-section 5000 words），**本节不再生成**。如旧版 cross_comparison.md 含此节，5.8 不消费其数字。
```

### 📌 Checkpoint C1：Git 备份对标分析（不可跳过）

对标分析产出的 benchmark 报告和横向比对表是后续审计的基础数据，必须在进入审计前备份。

```bash
git add structure/3_methodology/benchmark/benchmark_papers.ris \
       structure/3_methodology/benchmark/*/*_benchmark.md \
       structure/3_methodology/benchmark/*/figures/ \
       structure/3_methodology/benchmark/*/tables/ \
       structure/3_methodology/benchmark/_visual_index.md \
       structure/3_methodology/benchmark/cross_comparison.md
git commit -m "Checkpoint: method-audit benchmark complete ({M} papers)"
```

> 注：显式添加 benchmark.md、figures/、tables/、benchmark_papers.ris（决策表 B 分支复用缓存时从 ris 取 citation key），**不添加 PDF**（二进制大文件不入 git）。_visual_index.md 和 cross_comparison.md 保留在 benchmark 根目录。

### 2.5.1 生成 method_landscape.md（**覆盖 lit-pool 初版**）

从 `cross_comparison.md` 和各 `{key}_benchmark.md` 中汇总，**覆盖写入** `structure/2_literature/method_landscape.md`（lit-pool 步骤 7.5 产出的文献视角初版在此被替换为 benchmark 对标视角，路径共用、不并存）：

- **方法论创新汇总**：从各 benchmark 报告的 B3（模型创新）条目提取，表格形式
- **模型设计技巧矩阵**：论文 × 技巧，从 cross_comparison.md 表1 提取
- **本文的对标定位**：差异化定位和核心改进策略

> 此文件在 `/finalize` Phase 4 清理时**保留**（位于 `2_literature/`，不是 `literature.md`，因此不删除）。

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


---

## 步骤 3：深度审计

**核心价值所在。** 基于对标数据 + Claude 方法论知识 + 论文具体内容，提出方法论问题和对标借鉴建议。

### 3.1 审计信息源（四源融合）

```
审计依据 = 对标数据（步骤 2 的 cross_comparison.md + 行业基线）
         + 视觉对标（benchmark/{key}/figures/ + tables/ 中的提取图表）
         + Claude 方法论知识（理论最佳实践、常见审稿意见）
         + 论文具体内容（methodology.md + results.md + simulation.md 的 ## 正文要点）
         + 数据分析证据（data/results/*.txt 数值结果 + data/notes/*.md 分析笔记 + data/robustness/ 稳健性记录）

**`data/notes/` 在审计中的角色**：维度 C（参数与数据）和维度 D（结果可靠性）必须 Glob 读 `data/notes/*.md`。这些笔记记录了"为什么用这个 spec、试了什么没成、有什么 anomaly"——是审计假设合理性、稳健性覆盖度、命题预测对照的关键证据来源。无 `data/notes/` 时不阻塞审计，但报告中标注"基于 X.md 自报"。
```

**视觉对标使用场景**：
- **维度 D（结果可靠性）+ 维度 F（方法论表述）**：Read 对标论文的结果表图片（如 `benchmark/cao2017d/tables/table4.png`），对比报告格式（显著性标注方式、效应量呈现、模型嵌套展示、注释规范等），识别本文的格式短板
- **SO-图表借鉴**：Read 对标论文的 figure 图片，评估网络拓扑图、GOF 图、框架图等的设计质量和适配性
- **图片路径索引**：`benchmark/_visual_index.md`

**降级模式**（跳过了步骤 2 时）：仅基于 Claude 知识 + 论文内容，不附带行业基线标注和视觉对标。

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

**SO-图表**：图表设计借鉴（来源：各报告 B4 → 行业基线图表推荐汇总 + `_visual_index.md`）

```
### SO-F1: {一句话标题}

**来源论文**: {citation_key}（{期刊}, {年份}）
**图表描述**: {该图/表的内容和呈现方式}
**参考图片**: `benchmark/{citation_key}/figures/{filename}` 或 `benchmark/{citation_key}/tables/{filename}`
**适配分析**: {为什么适配本文数据，建议如何借鉴}
```

> 借鉴建议中附上图片路径，用户和 Claude 均可直接 Read 查看原图做视觉对比。

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
  {仅 SO-F:} **参考图片**: `benchmark/{key}/figures/{filename}` 或 `benchmark/{key}/tables/{filename}`
  **建议**: {调整方案}
  ```

  > SO-F 条目展示时，主 agent 须 Read 参考图片，向用户展示视觉参考后再讨论借鉴方案。

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
  **SO 条目涉及表格时**：如果 md 中已有表格素材，在处理循环中即时写入 `structure/figures_tables/tables.tex` + 更新 `index.md` 状态，遵循项目 CLAUDE.md 的"表格即时落地"规则。不得将表格制作推迟到 `/technical`。

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
  - **单条修复后一致性检查**：每次修改 X.md 后，立即检查本次修改是否导致同一文件内其他位置出现不一致（如改了符号定义但后续推导仍用旧符号、改了假设编号但命题引用未同步等）。发现不一致则当场修复，不留到后面。
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

处理循环结束后、生成总结前，对所有被修改的技术型章节 X.md 文件做一次**系统性全文一致性扫描**：

1. **文件内一致性**：逐个扫描每个被修改的 X.md，检查：
   - 符号定义与后续引用是否一致（如 $\alpha$ 的定义是否与所有使用处匹配）
   - 假设编号是否连续、引用是否正确
   - 命题编号是否连续、证明中引用的命题号是否正确
   - 公式编号（tag）是否连续、交叉引用是否正确
   - 修改处的前后文逻辑是否衔接

2. **文件间一致性**：跨 X.md 文件检查（同步骤 0.3 的跨文件一致性检查，但基于修改后的最新内容重新扫描）

3. **发现不一致**：直接修复（不需要再走用户确认循环），修复后在总结中列出。

---

### 步骤 5.7：技术型章节结构确认

一致性扫描完成后，基于审计发现和 benchmark 共性模式，重组成稿 md 的章节结构（reader-centered 顺序），为 `/technical` 锁定可读结构。

#### 5.7.1 收集结构信息（硬约束：benchmark 一手实测 + 三章一体）

读取以下四类信息：

1. **Benchmark 一手实测结构**（硬约束，**首要依据**）：

   **优先路径（默认）**：从每篇论文的 per-paper 报告 `structure/3_methodology/benchmark/{citation_key}/{citation_key}_benchmark.md` 的 **A6（章节结构）** 字段直接读取——该字段已由步骤 2.4 的 subagent 一手提取，覆盖：§3 / §4 / §5 完整层级、subsection 数 + subsubsection 深度、假设位置、命题/定理位置、特殊章节安排（框架图 / 算法块 / 独立 simulation 节等）。**不需要重复跑 subagent**。

   **Fallback 路径**（仅在以下情形之一时启动并行 subagent 一手补提取）：
   - 某篇论文 per-paper 报告缺失（步骤 2.0 决策表 B 分支：复用 cross_comparison.md 缓存但 per-paper 子目录不存在）
   - per-paper 报告存在但 A6 字段不完整 / 缺失结构层级数据
   - cross_comparison.md 时间戳早于 2025-10（旧版 prompt 未含 A6 章节结构提取项）
   
   Fallback subagent 配置：`subagent_type=general-purpose, run_in_background=true`，**禁止**传 `isolation: worktree` 参数；prompt 仅提取 §3/§4/§5 的 `###`/`####` 实测标题、subsection 数 + 深度、假设/命题位置、特殊章节安排，跳过 Introduction / LR / Discussion / Conclusion。

   两条路径汇总后，主 agent 整理为**实测对照矩阵**（论文 × 章节 × 节数 × subsubsection 深度），作为 5.7.2 的首要依据。

2. **Benchmark 横向比对表**（辅助交叉验证）：从 `structure/3_methodology/benchmark/cross_comparison.md` 表 3 "章节结构详细比对" + "技术型章节结构共性模式" 段落读取聚合数据，与 step 1 实测对照矩阵交叉验证。如二者出现冲突，以 step 1（per-paper 一手数据）为准。

3. **Idea 故事线**：从 `idea.md` §3（方法论选择）提取故事线总览和结论群架构。

4. **现有成稿 md 结构 + 缺失文件 placeholder（三章一体硬约束）**：读取所有技术型 md 的当前 `###`/`####` 标题。**如某 md 按 METHOD_TYPE 应有但不存在**（如 modeling 类应有 `results.md` / `simulation.md` 但目录下不存在），**不得跳过其结构规划**——必须在 5.7.4 阶段创建 placeholder 骨架文件。三章一体规划是硬约束，**不允许只做 methodology 单章而留 results / simulation 给下轮**——这会让 §3 的 subsection 划分出现"该挪到 §4 的内容留在 §3""§4 该有的接口没在 §3 留"等错位。

   **唯一例外**：用户在 `/method-audit` 调用时明确指定单章节模式（如 `/method-audit methodology`），此时 5.7.1 第 4 项可跳过缺失文件规划，但需在 5.7.3 + 5.7.4 显式标注 "single-section override，跨章节 reader logic 暂未锁定，下一轮补做"。

#### 5.7.2 生成结构建议

综合以上信息，为每个技术型成稿 md 生成建议的 `###`/`####` 层级结构。

**建议依据优先级（硬约束）**：

1. **Benchmark 一手实测结构（首要硬约束）**：建议结构的每个 `###`/`####` 必须能映射到 5.7.1 step 1 提取的实测对照矩阵中**至少一篇** benchmark 论文的对应小节。**不允许出现 "benchmark 中没有任何论文这么分" 的小节划分**，除非该小节是当前论文独有方法学创新（且必须在调整说明中显式标注 "X-original (no benchmark precedent)"）。

2. **节数硬上限（硬约束）**：建议 subsection 数 ≤ benchmark median + 1。例：benchmark §3 节数 median = 3 → 建议 §3 ≤ 4 节。超过即视为违规，须合并/降级。

3. **Idea 故事线**（次要依据）：与 idea.md §3 故事线对齐，确保贡献 / RQ / 章节映射一致。

4. **X.md 实际内容分布**：每个 subsection 必须有足够素材支撑，避免空节。

5. **Reader-centered 原则**：优先 mimic ≥50% benchmark 论文的开篇模式。如 ≥50% benchmark 用 "framework / preliminaries / scope / problem description" 作为 §X.1 → 建议结构必须有对应的开篇节。

6. **跨章节 reader logic 一体（硬约束）**：§3 → §4 → §5（如适用）必须形成连续故事线。每个章节末尾的素材必须能接到下一章节开头。在 5.7.2 输出中显式列出 "§3 末尾 → §4 开头" 等衔接关系。

> **强制可视化**：建议输出**必须**包含三栏对照表——`benchmark 共性模式（来自一手矩阵）` | `当前 X.md 结构` | `建议结构 + benchmark 来源映射`。每条结构调整必须标注 benchmark 依据（"X/M 篇对标论文采用此分节方式 + 具体论文名 + 对应 §X.Y"），使用户能判断建议的可信度。

**输出格式**（强制三章并列展示 + benchmark 实测对照）：

```
📐 技术型章节结构建议（基于 {M} 篇 benchmark 一手实测）

═══ Step 1: Benchmark 实测对照矩阵（来自 5.7.1 并行 subagent）═══

| 论文 | §3 节数 | §3.x 深度 | §4 节数 | §5 节数（独立 sim） | 模式 | 框架图 |
|:-----|:-:|:-:|:-:|:-:|:-----|:-:|
| {key1} | {n} | {depth} | {n} | {n or —} | {pattern} | {y/n} |
| ...   | ... | ... | ... | ... | ... | ... |

**Median**: §3 = {N_M}，§4 = {N_R}，§5 = {N_S}（如适用）
**Range**: §3 = {min}-{max}
**节数硬上限**: §3 ≤ {N_M+1}，§4 ≤ {N_R+1}

═══ Step 2: methodology.md 结构对照与建议 ═══

| Benchmark 共性模式（≥50% 论文）| 当前 X.md | 建议结构 + benchmark 来源映射 |
|:-----|:-----|:-----|
| {N}/{M} 用 "framework/preliminaries" 开篇 | {当前现状} | **§3.1 ...**（仿 {key1} §3.1 + {key2} §X.Y）|
| {N}/{M} 把 model setup 与 utility 同节 | {当前现状} | **§3.2 ...**（仿 {key3} §3.2 三级）|
| ...  | ...  | ... |

节数对比: benchmark median {N_M} | 当前 {N_curr} | 建议 {N_new} ≤ {N_M+1} ✓

═══ Step 3: results.md 结构对照与建议（即使 md 不存在也必须规划）═══

（同样格式，三栏对照——若 results.md 不存在，"当前 X.md" 列标 "❌ 不存在，须 5.7.4 创建 placeholder"）

═══ Step 4: simulation.md 结构对照与建议（如 METHOD_TYPE 适用）═══

（同样格式）

═══ Step 5: 跨章节 reader logic 衔接 ═══

§3.{last} → §4.1: "{衔接句指南，明示 §3 末尾产出如何被 §4 开头消费}"
§4.{last} → §5.1: "{衔接句指南，如适用}"
§4 / §5 → §6 Discussion: "{衔接句指南，按 RQ 分组消费 §4 finding}"
```

#### 5.7.3 交互确认

**强制三章一体确认（硬约束）**：AskUserQuestion **必须**一次性展示 §3 + §4 + §5（如 METHOD_TYPE 适用）三章建议结构 + 跨章节 reader logic 衔接，让用户做整体判断。**不允许只确认 methodology 而把 results / simulation 留到下一轮**——这会导致 §3 末尾接不上 §4 开头的接口错位。

用户可以：
- 接受整套建议结构（§3 + §4 + §5 一体确认）
- 修改任意章节的标题措辞、增删 subsection/subsubsection
- 调整层级（`###` ↔ `####`）
- 跨章节挪动内容（§3.X 内容挪到 §4.Y 等）

**循环**：用户不满意 → 修改结构 → 再次展示三章对照 + benchmark 节数对比 + 跨章节衔接 → 直到用户确认整套结构。

**唯一例外**：5.7.1 第 4 项标注的 single-section override 模式下，仅确认指定章节即可，但需提示用户 "跨章节 reader logic 暂未锁定，下一轮补做"。

#### 5.7.4 写入成稿 md

用户确认后，按新结构重组对应的成稿 md 文件：

**A. 已有 md 重组**：
- 替换 `## 正文要点` 下的所有 `###`/`####` 标题
- **保留所有已有实质内容**：将原 X.md 中已填的正文要点按语义映射到新标题下（不丢内容）
- 标题变更但内容仍可对应时 → 内容跟随新标题
- 标题被合并/拆分时 → 内容按用户在 5.7.3 给的指示分配
- 新增的 subsection 标题下放 `TODO: 待用户填充内容`
- **不修改** `## 必备元素` 和 `## 引用池` 部分

**B. 缺失文件 placeholder 强制创建（硬约束）**：

如 5.7.1 第 4 项判定 `results.md` / `simulation.md` 按 METHOD_TYPE 应存在但当前不存在（且未走 single-section override 模式），**必须**为每个缺失文件创建 placeholder 骨架。

**写入模板**（硬编码，不依赖外部 paper-init/templates 路径——该路径不保证存在）：

```markdown
<!-- placeholder created by /method-audit step 5.7.4-B; awaiting user fill. step 0.3 will skip empty-content detection on this file. -->

> 目标字数: {N} words  （5.8 已锁定时填具体值；否则 TBD）

## 必备元素

{按 METHOD_TYPE 从 step 1.1 复制对应清单}

## 正文要点

**目标总字数: {N} words**  （同头部）

| Subsection | 目标字数 | 写作说明 |
|:-----------|:-------:|:--------|
| {5.7.3 确认的标题1} | TBD | TBD |
| {5.7.3 确认的标题2} | TBD | TBD |
| ... | ... | ... |

> 字数分配表的 TBD 由 5.9 跑完后回填；当前为 placeholder 状态。

### {5.7.3 确认的标题1}
TODO: 待用户填充内容

### {5.7.3 确认的标题2}
TODO: 待用户填充内容

## 写作蓝图

TODO: 待 /method-audit step 5.7+ 写入

## 引用池

TODO: 待 /lit-pool 后期或手工填充
```

**区块顺序硬约束**：`## 必备元素 → ## 正文要点 → ## 写作蓝图 → ## 引用池`，与 5.7+ 位置约束一致。

**与 step 0.3 + step 7.1 的交互**（预期行为，非 bug）：
- placeholder 文件全是 TODO → 由 step 0.3 多章节模式分级豁免（标记 `placeholder-pending`，跳过内容审计但参与结构 / 字数 / 蓝图规划）
- 步骤 6.5 必备元素验收会自然 fail（placeholder 无实质内容） → 步骤 7.1 第 1 / 3 条阻塞阶段转换 → **正确保持 foundation 阶段**，等待用户后续填充 results 内容
- 用户填充 results.md 实质内容后，再次跑 `/method-audit` → placeholder 标记自动失效，进入正常审计流程，此时才会触发 7.2 阶段转换

> 写入的文件将纳入 Checkpoint C3 的 git add 范围。
> **不丢内容原则**：审计修复的目的是审稿质量，不是清空 X.md。如映射出现冲突或歧义，标记 🔴 Issue 记入报告，不自动覆盖。

---

### 步骤 5.7+：写作蓝图（Reader Journey + Cross-chapter Bridge）

> **目的**：5.7 确定了「什么放在哪」（结构），5.7+ 确定「读者怎么读」（认知路径）和「章节怎么衔接」（过渡）。这是 `/technical` 写作时的核心 prompt 输入——决定生成的段落是否符合读者预期。
>
> **下游契约**：`/technical` 必读此区块作为 sci-writer prompt 的核心输入。蓝图字段与生成段落的内容选择和措辞**强对齐**——读者预期由此决定。

#### 5.7+.1 收集 reader journey 输入

主 agent 综合以下信息为每个技术型章节构建 reader journey：

- **5.7.4 已确认的结构**（subsection 列表 + 顺序）
- **idea.md §3**（方法论选择故事线）
- **X.md 的 `## 正文要点`**（各 subsection 实际内容摘要）
- **benchmark per-paper 报告 A6**（对标论文的章节衔接模式）
- **benchmark cross_comparison.md 的"技术型章节结构共性模式"**

#### 5.7+.2 生成蓝图建议

为每个技术型章节（Methodology / Results / Simulation）生成蓝图，包含三个层级：

**A. 章节级 Reader Journey**：用 1-2 句话概述本章读者认知路径

示例：
> Methodology: 从问题陈述 → 假设设定 → 模型构建 → 命题推导，读者从"为什么需要这个模型"逐步过渡到"模型如何运作"。

**B. Subsection 级蓝图**（每个 subsection 五字段）：

- **Reader Entry Point**：读者此时已知什么（来自前文哪个概念/结论）
- **Content Journey**：本 subsection 交付什么单一观点（一句话）
- **Exit Point**：读者离开时应记得什么（后文会用什么概念接住）
- **Why This Order**：为什么放在这个位置（vs 其他位置的差异）
- **Visual Anchor**：是否需要配图/表？什么时机出现最自然？（无则填 "—"）

**C. 跨章节过渡方案**：列出本章与前后章节的衔接句指南

示例：
- methodology → results: "{模型名} 的假设（见 §3.2）直接导出均衡解中的三个命题，体现 XX 机制"
- results → simulation: "{参数集合} 对应实际情境的 YY，仿真基准 {baseline} 验证命题 1-3"

#### 5.7+.3 交互确认

逐章展示完整蓝图（一章一组）→ AskUserQuestion 让用户确认。

用户可以：
- 修改某 subsection 的 Entry/Journey/Exit 措辞
- 改变 cross-chapter 过渡句指南
- 增删 Visual Anchor
- 调整 subsection 顺序（虽然 5.7 已确认，但 5.7+ 可基于 reader journey 反向调整）

**循环**：不满意 → 修改 → 再展示 → 直到确认。

如果用户在 5.7+ 调整了 subsection 顺序，自动触发 5.7.4 重新写入结构（一次循环回放：5.7.4 → 5.7+），完成后继续 5.7+.4 写入蓝图。

#### 5.7+.4 写入 X.md `## 写作蓝图` 区块

用户确认后，在每个技术型 X.md 中**紧接 `## 正文要点` 之后** 插入新区块（如已存在则覆盖）：

```markdown
## 写作蓝图

### 整体 Reader Journey
{1-2 句概述本章读者认知路径}

### Subsection 级蓝图

#### {subsection title 1}
- **Reader Entry Point**: {读者此时已知什么}
- **Content Journey**: {本节单一观点}
- **Exit Point**: {读者离开时记住什么}
- **Why This Order**: {为什么这个位置}
- **Visual Anchor**: {图表锚点 或 —}

#### {subsection title 2}
- ...

### 跨章节过渡
- {prev section} → {current section}: "{过渡句指南}"
- {current section} → {next section}: "{过渡句指南}"
```

> 写入的文件将纳入 Checkpoint C3 的 git add 范围。
> **位置约束**：`## 写作蓝图` 紧接 `## 正文要点` 之后。X.md 区块顺序（与 paper-init 模板一致）：
> `## 必备元素` → `## 正文要点` → `## 写作蓝图` → `## 引用池` → [仅 modeling/simulation：`## 脚本与图表`]
>
> **写入规则**：
> - 若 X.md 中**没有**或**仍是 paper-init 默认 TODO 占位**的 `## 写作蓝图` → 直接写入 / 覆盖
> - 若已有真实蓝图内容（上次审计写入或用户手改） → AskUserQuestion: (1) 覆盖（推荐，本次是新版蓝图）/ (2) 跳过保留旧蓝图

---

### 步骤 5.8：技术型章节字数硬编码分配

> **设计原则**：放弃基于 benchmark PDF 字数估算的方案——经实证（zy12 项目，2026-05-02）发现 PDF page-density 估算在 5 篇对标论文中偏差 -35% 到 +119%，且 basic vs strict-prose word count 双指标不一致，估算路线**不可靠**。
>
> 改为**硬编码总字数**：技术型章节合并字数仅按"技术型章节数量"二分。配比由用户在 5.8.3 选择，无 benchmark 依赖。

#### 5.8.1 识别技术型章节集合

扫描 `structure/` 目录，按文件实际存在情况判断技术型章节数：

| 模式 | 条件 | 技术型章节集合 |
|:--|:--|:--|
| **2-section 模式** | `methodology.md` + `results.md` 存在；`simulation.md` 不存在或合并入 `results.md`（CLAUDE.md `## 项目阶段` 标注） | Methodology + Results |
| **3-section 模式** | `methodology.md` + `results.md` + `simulation.md` 都存在且都有实质内容 | Methodology + Results + Simulation |

**判定逻辑**：
- 用 Glob 检测三个文件是否存在
- 用 Grep 检测 CLAUDE.md `## 项目阶段` 是否含 "simulation 合并入 results" 等措辞
- 不确定时 AskUserQuestion 让用户明确

#### 5.8.2 应用硬编码总字数

| 模式 | 技术型章节合计字数（hard-coded） |
|:--|:-:|
| 2-section（Methodology + Results） | **4500 words** |
| 3-section（Methodology + Results + Simulation） | **5000 words** |

**字数定义**：strict prose word count（自然语言段落字数；不含 equation 内容、algorithm 伪码、figure/table caption 文字、reference 引用计数）—— 与 LaTeX `texcount` 主流默认行为一致。

**不再读取**：`cross_comparison.md` 的章节字数基线（已废弃；其数字基于不可靠的 PDF page-density 估算）。

#### 5.8.3 生成默认配比 + 用户调整

**默认配比**（基于"methodology 含公理化/模型设定，密度高于 results"的一般经验）：

| 模式 | Methodology | Results | Simulation |
|:--|:-:|:-:|:-:|
| 2-section（4500 总） | **2700 (60%)** | **1800 (40%)** | — |
| 3-section（5000 总） | **2000 (40%)** | **1500 (30%)** | **1500 (30%)** |

**允许调整**：用户可在 5.8.4 调整配比，但**总字数必须保持 4500 / 5000 不变**（此为硬约束）。如要改总字数：用户必须明确说明"超出硬编码范围"，并在 method_audit_report.md 备注理由。

#### 5.8.4 展示并确认

```
📊 技术型章节字数分配（硬编码 {N}-section 模式，总 {4500/5000} words）

| Section | 默认建议 | 占比 | 调整理由 |
|:--------|:-------:|:--:|:---------|
| Methodology | 2700 | 60% | — |
| Results | 1800 | 40% | — |
| {仅 3-section:} Simulation | — | — | — |
| **合计** | **4500** | 100% | （硬编码上限）|

附注：叙述型章节由 /narrative 写入 manuscript.tex，遵循硬约束：
  Introduction 1000-1200 / Literature Review 1500 / Discussion 1800-2500
（method-audit 不写入叙述型章节字数。）

你可以调整 Methodology / Results / Simulation 的配比，但合计须保持 {4500/5000} 不变。
```

AskUserQuestion 等待用户确认。**循环**：用户不满意 → 修改配比 → 再次展示 → 直到确认。

#### 5.8.5 写入各章节 md

> **职责边界**：5.8 写入仅限技术型章节（Methodology / Results / Simulation）。叙述型章节由 `/narrative` 直接读 manuscript.tex 写 tex，method-audit 不越位。

用户确认后，遍历以下文件（仅存在的文件），用 Edit 修改头部的 `目标字数` 行：

| Section | 文件路径 |
|:--------|:---------|
| Methodology | `structure/3_methodology/methodology.md` |
| Results | `structure/4_results/results.md` |
| Simulation | `structure/*simulation*/simulation.md`（仅 3-section 模式）|

替换规则：
- 匹配 `> 目标字数:` 或 `> 字数目标:` 开头的行
- 替换为 `> 目标字数: {N} words`

> 写入的文件将纳入 Checkpoint C3 的 git add 范围。

显示确认：
```
✓ 字数目标已写入技术型章节 md
  - methodology.md: {N} words
  - results.md: {N} words
  {仅 3-section:} - simulation.md: {N} words
  - 技术型合计: {4500/5000} words（硬编码）
```

---

### 步骤 5.9：Subsection 字数分配表 + 写作说明

各章节总字数确定后，进一步把字数分配到 subsection 级，并为每个 subsection 生成一句话写作说明，写入 X.md 的 `## 正文要点` 区块——这是 `/technical` 的直接输入（与 `## 写作蓝图` 区块配合使用）。

#### 5.9.1 自动分配各 subsection 字数

对每个技术型 X.md：

- **基础分配** = 章节总字数 × (该 subsection 正文要点行数 / 全部 subsection 正文要点总行数)
- **密度调整**：
  - 含大量编号公式的 subsection：权重 ×1.1
  - 纯方法概述类 subsection：不调整
  - 含命题+证明骨架的 subsection：每个命题约需 80-120 词
  - 含比较静态/敏感性分析的 subsection：每个参数约 50-80 词
- 取整到最近的 50

#### 5.9.2 生成写作说明

为每个 subsection 生成一句话风格指导，作为 `/technical` 调用 sci-writer 时的写作策略提示：

- **方法论概述类**："Justify method choice with brief comparison; concise"
- **模型设定类**："Define all notation precisely; each assumption needs one-sentence justification"
- **模型求解类**："Present payoff functions → equilibrium derivation → key results; every equation needs economic interpretation"
- **命题分析类**："State proposition → proof sketch → economic intuition; highlight mechanism"
- **仿真类**："Parameter table → figure interpretation → managerial insight; link back to propositions"
- **稳健性类**："Brief description of robustness check → key result → consistency with main finding"

#### 5.9.3 展示并确认（⚠️ 交互点）

逐章展示完整字数分配方案：

```
📊 {chapter} 字数分配（章节总字数 = {N} words）

| Subsection | 正文要点行数 | 目标字数 | 写作说明 |
|:-----------|:-----------:|:-------:|:--------|
| ### 3.1 ... | 6 | 200 | {风格指导} |
| ### 3.2 ... | 45 | 550 | {风格指导} |
| ### 3.3 ... | 38 | 500 | {风格指导} |
| ### 3.4 ... | 52 | 750 | {风格指导} |
| 合计 | — | {N} | — |

你可以修改总字数、单个 subsection 字数或写作说明。确认后写入 X.md。
```

**AskUserQuestion**：
```
(1) 确认，按上表写入
(2) 调整（说明要改哪里：总字数、某 subsection 字数、写作说明等）
```

用户选 (2) → 调整 → 重新展示 → 再次确认（循环到确认）。
用户选 (1) → 进入 5.9.4 写入。

#### 5.9.4 写入 X.md `## 正文要点` 区块

用户确认后，在 X.md `## 正文要点` 标题下、第一个 `###` 之前，插入字数分配表：

```markdown
## 正文要点

**目标总字数: {N} words**

| Subsection | 目标字数 | 写作说明 |
|:-----------|:-------:|:--------|
| {title1} | {n1} | {说明1} |
| {title2} | {n2} | {说明2} |
| ... | ... | ... |

### {title1}
{已有正文要点内容}
...
```

> **格式约定**：技术型章节使用 3 列（Subsection | 目标字数 | 写作说明）。叙述型章节由 `/narrative` 直接处理（不写 md、直接 tex），不在 X.md 中维护字数分配表。`/technical` 仅解析技术型 X.md 的 3 列格式。

> **覆盖优先（避免重复表）**：写入前先扫描 `## 正文要点` 与第一个 `###` 之间的内容：
> - 若已存在 `**目标总字数:` 行 + 3 列字数分配表（来自 5.7.4-B placeholder 的 TBD 占位表，或上一轮 method-audit 写入） → 用 Edit 用本次确认数据**整体覆盖**该区段（含总字数行 + 表格）
> - 若不存在 → 按当前插入逻辑写入
> 严禁出现两个并列的字数分配表（会让 /technical 解析失败）

> **双写一致性**：5.8.5 已写入头部 `> 目标字数: {N} words`，5.9.4 在此处写 `## 正文要点` 区块的 `**目标总字数: {N} words**`，二者必须一致。若不一致：
> - `/technical` 检测到不一致 → 按头部值为准并报警
> - **自动修复**：method-audit 完成 5.9.4 写入后，立即用 Edit 工具校验头部和区块的字数行数值匹配。如不一致（理论上不应发生，仅作 safety net），用 Edit 覆盖区块内的总字数行至与头部一致并提示用户。

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

---

## 步骤 6.5：必备元素 checklist 验收（放行前自动校验）

放行前对每个技术型 X.md 的 `## 正文要点` 进行**结构性必备元素验收**，确保 `/technical` 能拿到完整素材（结合 `## 写作蓝图` 区块）。

### 6.5.1 验收清单

对每个 X.md 的每个 `###` subsection，检查（按方法类型适配）：

**modeling**：
- [ ] 每一个会出现在正文中的编号公式（含 `$$...$$` 或 `\begin{equation}`）
- [ ] 每一个命题/引理的完整陈述（编号 + 条件 + 结论）
- [ ] 每一个证明的思路骨架（完整证明用 `> **Proof (→ Supplementary):**` 标记）
- [ ] 每一个假设的文字表述 + 合理性论证（含 `\citep{}`/`\citet{}` 引用）
- [ ] 每一个经济直觉/含义解读
- [ ] 每一个模型间的对比说明
- [ ] 表格和图表标注（"此处引用 Table X / Fig. X"）

**survey-sem / panel-regression**：
- [ ] DV/IV/中介/调节/控制变量的定义
- [ ] 信效度/相关系数/VIF 等基础统计的呈现方式
- [ ] 假设检验的具体描述（路径系数 + 显著性 + 效应量）
- [ ] 稳健性检验的列表
- [ ] 表格和图表标注

### 6.5.2 收集问题

遍历所有技术型 X.md，对每个 `###` subsection 应用清单。问题分类：

- 🔴 **缺项**：清单中应有但 X.md 中找不到 → `issues_log` 标 BLOCK
- ⚠️ **(ref) 待补**：内容中含 `(ref)` 占位，未替换为实际 citation key
- ⚠️ **bib 未匹配**：X.md 中出现的 citation key 在项目 bib 中不存在
- ⚠️ **TODO 残留**：subsection 仍含 `TODO` / `TBD` / `???`

### 6.5.3 展示验收结果

```
📋 必备元素验收（{N} 个 subsection）

| 章节 | Subsection | 缺项 | (ref)待补 | bib未匹配 | TODO残留 | 状态 |
|------|-----------|:---:|:--------:|:---------:|:--------:|:----:|
| methodology.md | ### 3.2 | 0 | 0 | 0 | 0 | ✅ |
| methodology.md | ### 3.3 | 1 | 2 | 0 | 0 | 🔴 |
| ...

🔴 缺项详情:
- methodology.md → ### 3.3：缺"经济直觉/含义解读"

⚠️ (ref) 待补:
- methodology.md → ### 3.2：句号前的 (ref) 需补引用类型 [BG/METHOD]

⚠️ bib 未匹配:
- {key} — 不在项目 bib 中，请从 master.bib 补全

⚠️ TODO 残留:
- {file}:{section}
```

### 6.5.4 处理验收结果

- 🔴 缺项 ≥1 → 验收失败：跳过步骤 7（阶段转换），提示用户去 X.md 中补全
- (ref)、bib、TODO 仅 ⚠️：不阻塞放行，但会列入步骤 7 的提醒清单

---

## 步骤 7：阶段转换 foundation → drafting（自动）

按 `{METHOD_TYPE}` 查表确定"所有技术型章节"集合：

| METHOD_TYPE | 技术型章节集合 |
|:-----------|:---------------|
| `modeling` | `methodology.md` + `results.md` + `simulation.md` |
| `survey-sem` | `methodology.md` + `results.md` |
| `panel-regression` | `methodology.md` + `results.md` |

### 7.1 前置校验（严格，不通过则不转换）

1. 遍历该 METHOD_TYPE 下所有 X.md：任一 X.md 仍含 `% TODO` / `[TODO]` / `[TBD]` / `???` 占位符 → ❌ 不转换
2. 遍历 X.md：`## 正文要点` 区块的字数分配表均已写入（步骤 5.9.4 完成） → 缺失则 ❌ 不转换
3. issues_log 中有 🔴 实质问题（缺项、符号冲突、命题遗漏） → ❌ 不转换
4. `method_audit_report.md` 中有 🔴 MUST-FIX 未标记 ✅ Fixed → ❌ 不转换
5. 仅当 `$ARGUMENTS` 为空（多章节模式，覆盖全部技术型章节）时执行 7.2；单章节模式（指定 section）→ 跳过阶段转换
6. **写作蓝图完整性检查**（仅多章节模式触发；步骤 5.7+ 产物校验）：遍历该 METHOD_TYPE 下所有 X.md，每份必须满足：
   - 存在 `## 写作蓝图` 区块且**非 paper-init 默认 TODO 占位**
   - 含 `### 整体 Reader Journey` + 每个 subsection 的 5 字段（Entry / Journey / Exit / Order / Anchor） + `### 跨章节过渡`，且字段非空
   - 任一不满足 → ❌ 不转换，提示："X.md 的写作蓝图未完整填充——`/technical` 启动时会 BLOCK。请运行 /method-audit step 5.7+。"

### 7.2 写入项目 CLAUDE.md

前置校验全部通过、且为多章节模式时：

```
🎯 前置校验全部通过，自动转换项目阶段：foundation → drafting
- 已更新 CLAUDE.md: 状态: drafting, 更新时间: {TODAY}
```

在项目 CLAUDE.md 中更新 `## 项目阶段`：
- `状态: drafting`
- `更新时间: {TODAY}`

### 7.3 校验未通过时的提示

```
⏸  前置校验未通过，保持 foundation 阶段。
阻塞原因:
- {原因1}
- {原因2}

用户解决后可再次运行 /method-audit（已 Fixed 条目会自动跳过）。
```

> **单章节模式不触发阶段转换**——用户可能只是补充某一章，不代表全部完成。

---

### 📌 Checkpoint C3：Git 备份审计修复（不可跳过）

处理循环结束后，将所有被修改的文件统一备份。包含修改后的章节 md、更新后的审计报告、以及稳健性检验脚本/结果（如有 TYPE B 条目）。

```bash
git add structure/3_methodology/methodology.md \
       structure/4_results/results.md \
       structure/*simulation*/simulation.md \
       structure/3_methodology/benchmark/method_audit_report.md \
       CLAUDE.md \
       data/robustness/
git commit -m "Checkpoint: method-audit fixes applied"
```

> CLAUDE.md 在步骤 7.2 转阶段时被更新（如阶段转换发生），一并备份。

> 仅 git add 实际存在且被修改的文件（非 modeling 类型项目无 simulation 相关文件，glob 自动跳过）。**叙述型章节（introduction/literature/discussion）不在本 skill 修改范围**，不纳入此 checkpoint。

---

## 全局约束

### 输出语言
- 审计报告的分析、建议、修改内容用**中文**
- 模拟审稿人措辞（"Reviewer 可能会问"）用**英文**（因为目标期刊是英文）
- 修改方案中的补充内容用**中文**（因为 X.md 是中文技术规格书，后续由 `/technical` 调用 sci-writer 生成英文 tex）

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
