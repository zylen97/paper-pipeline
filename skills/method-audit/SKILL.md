---
description: "方法论审计：读取 methodology/results/simulation md 后，模拟顶刊审稿人对该论文具体设定提出针对性质疑（Method Audit）"
---

# Method Audit — 方法论审计

读取当前论文的 methodology.md + results.md（+ simulation.md），先做基线完整性检查，再模拟目标期刊审稿人对**这篇论文的具体模型/数据/假设**提出针对性方法论质疑。

**核心原则**：不是打通用清单的勾，而是**读完具体内容后才能提出的质疑**。如果一条意见换到任何一篇同方法论文都成立，那它就不够具体，应该要么删掉要么重写得更针对。

**输入** `$ARGUMENTS`：可选，指定审计范围。示例：
- `/method-audit` — 审计 methodology + results + simulation（全部）
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

### 0.3 读取技术规格书

按 `$ARGUMENTS` 和 `{METHOD_TYPE}` 读取对应文件：

| 文件 | 路径 | 条件 |
|------|------|------|
| methodology.md | `structure/3_methodology/methodology.md` | 始终读取 |
| results.md | `structure/4_results/results.md` | `$ARGUMENTS` 为空或含 "results" |
| simulation.md | `structure/5_simulation/simulation.md` | 仅 modeling 类型 + `$ARGUMENTS` 为空或含 "simulation" |

**空文件检测**：如果文件内容全部是 TODO 占位符（没有实质内容），停止并提示：

```
⚠️ {文件名} 尚未填写（全部为 TODO）。
请先完成技术规格书的填写，再运行 /method-audit。
```

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

**目的**：快速扫描必备元素是否齐全。30 秒出结果，发现缺失直接打回。

### 1.1 加载必备元素清单

从 paper-init 模板中提取对应 `{METHOD_TYPE}` 的"必备元素"列表：

**modeling**：
- [ ] methodology.md: Research method（方法选择论证 + 博弈场景/模型框架描述）
- [ ] methodology.md: Modeling process（符号表 + 假设 + 模型公式 + 求解路线图）
- [ ] results.md: Equilibrium analysis（命题 + 证明/推导 + 经济学直觉）
- [ ] results.md: Comparative analysis（参数敏感性 / 情形对比 / 关键推论）
- [ ] simulation.md: Numerical simulation（参数校准 + 取值来源论证）
- [ ] simulation.md: Simulation results（图表 + 数值验证命题）

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
  ✅ Research method — 方法选择论证完整，含对比表
  ✅ Modeling process — 符号表 18 项，假设 4 个，模型公式完整
  ⚠️ Modeling process — 求解路线图缺失（有公式但未说明求解步骤）

results.md:
  ✅ Equilibrium analysis — 5 个命题，均有证明
  ❌ Comparative analysis — 仍为 TODO

simulation.md:
  ✅ Numerical simulation — 参数校准完整
  ⚠️ Simulation results — 有 3 张图但缺经济学含义解读
```

**如果有 ❌ 项**：AskUserQuestion：

```
基线检查发现 {N} 项缺失（标记 ❌）。建议先补全再做深度审计。
- 继续深度审计（跳过缺失部分）→ 输入 "continue"
- 先去补全 → 输入 "stop"
```

---

## 步骤 2：深度方法论审计

**核心价值所在。** 基于读取的具体内容，模拟目标期刊审稿人视角。

### 2.1 审计维度

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

### 2.2 审计规则

**质量控制**：
- 每条质疑必须**指向 md 文件中的具体位置**（哪个假设/命题/参数/表格）
- 每条质疑必须包含**审稿人的具体措辞**（"Reviewer 可能会问：..."）
- 如果一条质疑**适用于任何同类论文**（换掉论文标题仍然成立），则不够具体，删除或重写
- 总数控制：🔴 不超过 5 条，🟡 不超过 8 条，🟢 不超过 5 条。宁缺毋滥

**分级标准**：
- 🔴 **MUST-FIX**：不修复大概率导致 major revision 或 reject 的硬伤。审稿人看到会写 "This is a serious concern" 的级别
- 🟡 **STRENGTHEN**：不修复不至于被拒，但修复后显著提升方法论说服力。审稿人会写 "The authors should consider..." 的级别
- 🟢 **PREEMPT**：审稿人可能提的刁钻问题。提前在论文中用一两句话化解，避免进入 R2。审稿人会写 "It would be helpful if the authors could clarify..." 的级别

---

## 步骤 3：生成审计报告

### 3.1 报告格式

将审计结果写入 `drafts/method_audit_report.md`（如 `drafts/` 不存在则创建）：

```markdown
# Method Audit Report — {PAPER_TITLE}

> Generated: {date}
> Method: {METHOD_DETAIL}
> Target journal: {TARGET_JOURNAL}
> Audited files: methodology.md, results.md[, simulation.md]

---

## Baseline Check

{步骤 1 的基线结果，原样搬入}

---

## 🔴 MUST-FIX

### MF-1: {一句话标题}

**位置**: methodology.md → {具体章节/假设/公式编号}

**质疑**: Reviewer 可能会问："{模拟审稿人的具体措辞，用英文}"

**分析**: {为什么这是一个问题，用中文解释。指出具体的逻辑漏洞/遗漏/风险}

**建议**: {具体的应对方案——在 md 的哪里补什么内容}

---

### MF-2: ...

---

## 🟡 STRENGTHEN

### ST-1: {一句话标题}

**位置**: ...
**质疑**: ...
**分析**: ...
**建议**: ...

---

## 🟢 PREEMPT

### PM-1: {一句话标题}

**位置**: ...
**质疑**: ...
**建议**: {一两句话的化解措辞，可直接插入论文}

---

## Summary

| 级别 | 数量 | 涉及维度 |
|------|------|---------|
| 🔴 MUST-FIX | {n} | {A/B/C/D/E/F} |
| 🟡 STRENGTHEN | {n} | {A/B/C/D/E/F} |
| 🟢 PREEMPT | {n} | {A/B/C/D/E/F} |
```

### 3.2 展示报告

将报告完整展示给用户。AskUserQuestion：

```
📋 方法论审计完成（🔴{x} 🟡{y} 🟢{z}）

报告已保存至 drafts/method_audit_report.md

请选择要处理的条目：
- 处理指定条目：输入编号（如 "MF-1, ST-2, PM-3"）
- 全部处理：输入 "all"
- 只处理红色：输入 "red"
- 暂不处理：输入 "done"
```

---

## 步骤 4：生成修改方案并执行

### 4.1 生成修改方案

对用户选择的每条质疑，生成**具体的 md 层面修改方案**：

```
📝 修改方案（共 {N} 条）：

MF-1: {标题}
  文件: methodology.md
  位置: Assumption 3 之后
  操作: 新增一段（约 80 字）
  内容:
  > 需要补充的具体文字或公式（中文，供用户审核）

ST-2: {标题}
  文件: results.md
  位置: Proposition 2 的证明之后
  操作: 新增"边界条件讨论"小节
  内容:
  > 具体补充内容

PM-3: {标题}
  文件: methodology.md
  位置: "Research method" 段末
  操作: 追加一句话
  内容:
  > 具体措辞
```

AskUserQuestion：确认修改方案，或调整某条的内容。

### 4.2 执行修改

用户确认后，使用 Edit 工具逐条修改对应的 md 文件。

修改完成后，更新 `drafts/method_audit_report.md`，在已处理的条目后追加 `✅ Fixed ({date})`。

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

### 可重复运行
- 支持在修改后重新运行 `/method-audit`，此时应识别已修复的条目（读取上一次的 `method_audit_report.md`），只报告剩余问题和新发现的问题
- 上一次报告中标记 `✅ Fixed` 的条目不再重复提出，除非修改后引入了新问题
