---
description: "从direction reports生成按标签汇总的引用池（Citation Pool），含引用场景、分级排序和引用偏好，并生成 master.bib"
---

# Lit-Pool — 引用池生成

从 `/lit-review` 产出的 direction reports 中提取所有入选文献，按功能标签汇总，生成 `citation_pool/` 目录（含 BG.md/LR.md/GAP.md/METHOD.md/DISC.md/COMP.md），为各章节写作提供结构化的引用指南。

**输入**：无参数，直接运行 `/lit-pool`

**前置条件**：`/lit-review` + `/lit-tag` 已完成（direction reports中必须含"功能标签"列）

---

## 全局约束

### 模型选择
**subAgent 必须使用与主 Agent 相同的模型**（即继承 parent 模型）。**严禁**手动降级到 Sonnet 或 Haiku。如无特殊指定，不传 `model` 参数即可自动继承。

### 输出语言
**所有描述性文本必须使用中文**，包括但不限于：引用场景、与本研究的关键差异、标签文件header/备注。文献的标题、期刊名、作者名保持原文（通常为英文）。

### SubAgent负载上限
**AGENT_ITEM_LIMIT = 30**

单个subAgent处理的文献条目数不得超过30篇。超过时必须拆分。

### 槽位制并发控制
**MAX_CONCURRENT_AGENTS = 8**

同时运行的 subAgent 数**不超过 8 个**，每当 1 个 subAgent 完成（或失败重试后仍失败），立即从队列中取下一个启动，直到所有 subAgent 处理完毕。不等整批完成再启动下一批。

失败重试：subAgent 失败 → 自动重试一次 → 仍失败则报告用户。

---

## 步骤 0：前置检查

- 读取 `CLAUDE.md` → 提取项目编号
- 读取 `structure/0_global/idea.md` → 提取研究上下文（RQ、方法论，用于生成引用场景）
- Glob `structure/2_literature/direction*_report.md` → 确认存在
  - 不存在 → 停止，提示先运行 `/lit-review`
- 检查 `structure/2_literature/citation_pool/` 目录是否已存在
  - 已存在 → 询问用户：覆盖还是跳过？

---

## 步骤 1-2：提取 + 去重 + Citation Key + 调度计划（Python 脚本）

**本步骤由 Python 脚本一次性完成**，替代主 Agent 手动读报告、去重、生成 key、拆分 agent。

### 1.1 调用预处理脚本

```bash
python3 ~/.claude/skills/lit-pool/pool_prepare.py \
  --report-dir structure/2_literature/ \
  --output-dir structure/2_literature/ \
  --agent-limit 30
```

**脚本职责**（`pool_prepare.py`）：
1. 解析所有 `direction*_report.md` 的 markdown 表格，提取文献数据
2. 跨方向去重（key = first_author + year + title[:40]），合并标签和分级
3. 按全局规则生成 citation key（`auth.lower + year + shorttitle(1,1)`），自动处理冲突（追加 b/c 后缀）
4. 按标签分组，统计每标签文献量
5. 大标签按 ⌈N/30⌉ 拆分，小标签（≤15篇）贪心合并
6. 校验：key 格式合规、全局唯一、每篇至少 1 标签、agent 分配完整
7. 生成 `_pool_prepare.json`（含：去重后文献清单、citation key 映射表、标签分组、agent 调度计划）
8. stdout 输出摘要 + `VERIFY: PASS|FAIL`

### 1.2 主 Agent 校验

```
=== VERIFY: PASS|FAIL ===
```

- VERIFY 必须为 PASS。FAIL 时停止，展示具体错误给用户
- 将 stdout 的标签统计、key 样本、agent 调度表展示给用户确认
- 后续步骤从 `_pool_prepare.json` 读取数据构建 subAgent prompt

### 1.3 Citation key 使用规则

subAgent 必须**原样使用** `_pool_prepare.json` 中的 citation key，**严禁**自行生成、修改或追加任何后缀。主 Agent 在收到 subAgent 输出后，检查 key 是否一致。

---

## 步骤 2：读取调度计划

从 `_pool_prepare.json` 的 `agents` 字段读取调度信息。拆分和贪心合并已由 Python 脚本完成，主 Agent **不做任何算术**。

基于步骤1的调度计划，严格按 **AGENT_ITEM_LIMIT = 30** 分配subAgent任务。

### 2.1 展示调度计划

将 `_pool_prepare.json` 中的 `agents` 调度表展示给用户确认。
所有拆分和贪心合并已由 Python 脚本完成，主 Agent 直接读取使用。

---

## 步骤 3：并行启动SubAgent

按**槽位制**启动所有 subAgent（同时不超过 8 个，完成一个补一个）。

### 每个SubAgent的Prompt模板

```
你是学术文献分析专家。请对以下文献生成引用场景和排序。

## 研究上下文
{RESEARCH_CONTEXT}（来自步骤0加载的idea.md摘要）

## 你的任务
处理以下标签的文献：{标签列表}
文献数量：{N}篇

## 文献清单
{主Agent传入的文献列表，含：作者、年份、标题、期刊、功能标签、分级、入选理由}

## 对每篇文献执行：
1. **使用 citation key**：必须**原样复制**主Agent传入的 citation key，不可自行生成、修改或追加任何后缀。正确示例：`akcomak2023w`。错误示例：`akcomak2023w2023a`（多了重复的年份+字母）
2. **排序**：每个标签组内，按分级（核心→重要→备选）+ 年份降序
3. **生成引用场景**：基于入选理由 + 研究上下文，改写为写作视角
   - 入选理由 = "为什么留下这篇"（筛选视角）
   - 引用场景 = "这篇可以支撑什么论点"（写作视角）

## 输出格式（只输出 key-value 块，不写表格）

> **设计原理**：LLM 不擅长精确 markdown 表格。Agent 只需输出 key-value 块，Python 脚本 `format_pool_agents.py` 自动转换为标准表格。

**用 Write 工具写入** `structure/2_literature/_tmp_pool_agent{N}_raw.md`（注意 `_raw` 后缀）。

每个标签用 `# 标签名` 作为 section 标题，每篇文献用 `### paperN` 开头：

```markdown
# BG

### paper1
- citation_key: smith2024b
- 分级: 核心
- 作者: Smith et al.
- 年份: 2024
- 引用场景: 中文引用场景描述
- 期刊: Journal Name

### paper2
- citation_key: lee2023s
- 分级: 重要
- 作者: Lee et al.
- 年份: 2023
- 引用场景: 中文引用场景描述
- 期刊: Another Journal
```

**格式约束**：
- Section 标题格式：`# 标签名`（如 `# BG`、`# GAP-RQ1`），不加副标题或篇数
- 每篇文献 6 行 key-value（citation_key/分级/作者/年份/引用场景/期刊），每行一个字段
- citation key 必须原样复制，不可修改
- 分级写中文：核心/重要/备选
- 引用场景用中文，文献信息保持英文
- **不要写 markdown 表格**
```

---

## 步骤 3.5：格式标准化（Python 脚本）

将 Agent 输出的 key-value 块（`*_raw.md`）转换为 `pool_merge.py` 所需的标准表格格式。

```bash
python3 ~/.claude/skills/lit-pool/format_pool_agents.py \
  --input-dir structure/2_literature/ \
  --prepare-json structure/2_literature/_pool_prepare.json
```

**脚本职责**（`format_pool_agents.py`）：
1. 读取所有 `_tmp_pool_agent*_raw.md` 文件
2. 解析 key-value 块（citation_key/分级/作者/年份/引用场景/期刊）
3. 转换为标准 6 列 markdown 表格
4. 校验 citation key 存在于 `_pool_prepare.json` 中
5. 输出标准化的 `_tmp_pool_agent*.md`（去掉 `_raw` 后缀）
6. stdout 输出 `VERIFY: PASS|FAIL`

**主 Agent 校验**：VERIFY 必须为 PASS。

---

## 步骤 4：合并组装 `citation_pool/` 目录（Python 脚本）

所有 subAgent 完成后，**由 Python 脚本自动合并**，替代主 Agent 的 bash 拼接。

### 4.1 调用合并脚本

```bash
python3 ~/.claude/skills/lit-pool/pool_merge.py \
  --tmp-dir structure/2_literature/ \
  --output-dir structure/2_literature/citation_pool/ \
  --prepare-json structure/2_literature/_pool_prepare.json \
  --clean-tmp
```

**脚本职责**（`pool_merge.py`）：
1. 解析所有 `_tmp_pool_agent*.md` 临时文件
2. 按标签自动识别表格行，分组到对应文件
3. 组装 BG.md / LR.md / GAP.md / METHOD.md / DISC.md / COMP.md
4. 自动生成标准 header（篇数、日期、服务章节、引用偏好）
5. GAP/DISC 按 RQ 分子 section，METHOD 按基础/先例分子 section
6. 清理临时文件
7. 与 `_pool_prepare.json` 交叉校验标签覆盖
8. stdout 输出摘要 + `VERIFY: PASS|FAIL`

### 4.2 主 Agent 校验

VERIFY 必须为 PASS。将输出文件列表和行数展示给用户。

---

## 步骤 5：更新各章节md的引用池（Python 脚本）

**由 Python 脚本自动完成**，替代主 Agent 逐文件手动编辑。

```bash
# 先预览
python3 ~/.claude/skills/lit-pool/update_citation_refs.py \
  --structure-dir structure/ \
  --pool-dir structure/2_literature/citation_pool/ \
  --dry-run

# 确认后正式执行
python3 ~/.claude/skills/lit-pool/update_citation_refs.py \
  --structure-dir structure/ \
  --pool-dir structure/2_literature/citation_pool/
```

**脚本职责**（`update_citation_refs.py`）：
- introduction.md → BG[主] + GAP[主] + LR[次]
- literature.md → LR[主] + GAP[主] + METHOD[次] + DISC[次]
- methodology.md → METHOD[主]
- discussion.md → DISC[主] + COMP[主] + LR[次]

自动查找章节文件、插入/更新引用池区块、校验引用池文件存在性。
stdout 输出 `VERIFY: PASS|FAIL`。

---

## 步骤 6：对话汇报

在对话中展示：
1. 各标签文献数量分布表
2. 核心/重要/备选的总体比例
3. `citation_pool/` 目录路径
4. 提醒用户审阅，确认引用场景是否准确
5. 提示：正在生成完整评估报告（master_report.md）...

---

## 步骤 7：生成总报告 master_report.md

所有引用池文件生成完毕后，主Agent基于以下数据源生成 `structure/2_literature/master_report.md`：
- direction reports（各方向筛选结果）
- tag_report.md（标签统计与均衡性，由 `/lit-tag` 生成）
- citation_pool/ 目录（各标签引用池）
- idea.md（RQ、Gap、方法论）

回答以下 **6个硬问题**：

```markdown
# 文献总报告 — {项目编号}

> **日期**: {YYYY-MM-DD}
> **分析方向数**: {N}
> **文献总量**: 检索{X}篇 → 去重后入选{Y}篇（核心{a} + 重要{b} + 备选{c}）

---

## 一、创新性判断：有没有人做过？

### 竞品论文清单
| # | 作者 | 标题 | 年份 | 来源方向 | 与本研究的相似度 | 关键差异 |
|:--|:-----|:-----|:----:|:---------|:---------------:|:---------|

### 判断
- **直接竞品**: {有/无}。{如有，说明差异化空间}
- **间接竞品**: {列出方法相似但问题不同、或问题相似但方法不同的论文}
- **结论**: {能做/需调整/风险高}

---

## 二、Research Gap 分析

根据 idea.md 的成熟度，自动选择模式：

### 模式A：验证模式（idea.md 中已有明确 Gap/RQ）

逐个Gap评估：

| Gap | 描述 | 文献支撑 | 是否已被填补 | 评估 |
|:----|:-----|:---------|:------------|:-----|
| G1 | ... | {哪些文献证明这个Gap存在} | {有无文献已解决} | ✅真实 / ⚠️部分填补 / ❌已解决 |
| G2 | ... | ... | ... | ... |

### 模式B：发现模式（idea.md 仅有初步idea，Gap/RQ尚不明确）

基于各方向文献分析，识别潜在Gap：

| 潜在Gap | 文献证据 | 来源方向 | 可发展为RQ的方向 | 置信度 |
|:--------|:---------|:---------|:----------------|:------:|
| {现有文献缺少什么} | {哪些文献暗示了这个缺口} | 方向X | {建议的RQ方向} | 高/中/低 |

> 发现模式下，总报告额外输出一节 **"Gap → RQ 建议"**，帮助用户从文献中提炼出可行的研究问题。用户确认后可回写 idea.md。

---

## 三、方法论先例：本研究方法有无应用先例？

| 先例论文 | 方法 | 应用领域 | 与本研究的方法论距离 |
|:---------|:-----|:---------|:--------------------|

- **结论**: {方法论有充分先例 / 有部分先例需论证 / 首次应用需重点论证}

---

## 四、紧迫性与实践需求

- **行业实践证据**: {列出支撑研究紧迫性的文献/事件}
- **政策/行业趋势**: {列出相关趋势}
- **结论**: {紧迫性高/中/低}

---

## 五、引用池充足性

### 按分级

| 分级 | 数量 | 充足性 | 补检建议 |
|:-----|:----:|:------:|:---------|
| 核心 | {n} | ✅足够 / ⚠️偏少 | ... |
| 重要 | {n} | ... | ... |
| 备选 | {n} | ... | ... |

### 按标签

> 基于 tag_report.md 和 citation_pool/ 的实际标签数据。

| 标签 | Pool目标 | 实际入选 | 达标率 | 状态 |
|:-----|:-------:|:-------:|:-----:|:----:|
| BG | 50 | {n} | {%} | ✅/⚠️/❌ |
| LR | 150 | {n} | {%} | ... |
| GAP-RQx | 75 | {n} | {%} | ... |
| METHOD | 60 | {n} | {%} | ... |
| DISC-RQx | 65 | {n} | {%} | ... |

---

## 六、补检建议

| 建议编号 | 补检方向 | 原因 | 建议检索式 | 预估文献量 |
|:---------|:---------|:-----|:----------|:----------|

---

## 综合评估

### 本研究可行性: {✅可行 / ⚠️可行但需调整 / ❌风险过高}

### 核心发现
1. {发现1}
2. {发现2}
3. ...

### 对研究设计的建议
1. {建议1：如调整RQ措辞、补充某个理论视角等}
2. {建议2}
3. ...

### 文献分布可视化

| 方向 | ████████ 核心 | ████ 重要 | ██ 备选 | 合计 |
|:-----|:-------------|:---------|:--------|:----:|
| 方向1 | {n} | {n} | {n} | {n} |
| ... | ... | ... | ... | ... |
| **总计** | {n} | {n} | {n} | **{N}** |
```

### 对话汇报
生成完毕后在对话中展示：
1. 可行性结论
2. 竞品预警（如有）
3. Gap真实性评估
4. 引用池充足性（按标签）
5. 补检建议（如有）
6. **下一步建议**：用户审阅 master_report.md → 确认/调整 idea.md → 进入步骤③ idea定稿 → 步骤④ 填充各章节md

## 步骤 8：生成 master.bib（Python 脚本）

**由 Python 脚本自动完成 RIS → BibTeX 转换**，替代主 Agent 手动格式转换。

### 8.1 调用转换脚本

```bash
python3 ~/.claude/skills/lit-pool/ris2bib.py \
  --ris-dir structure/2_literature/ \
  --prepare-json structure/2_literature/_pool_prepare.json \
  --output structure/2_literature/citation_pool/master.bib
```

**脚本职责**（`ris2bib.py`）：
1. 从 `_pool_prepare.json` 读取 citation key 映射表
2. 解析 `*.ris` 文件（`utf-8-sig` 编码处理 BOM）
3. 按 first_author+year 匹配，用标题区分同名
4. 转换字段：TY→@article/@inproceedings, AU→author, TI→title, T2→journal, PY→year, VL→volume, IS→number, SP/EP→pages, DO→doi
5. 处理多作者（" and " 连接）、特殊字符转义
6. 未匹配文献生成 stub 条目（标注 TODO）
7. 校验：括号平衡、必填字段、回读验证
8. stdout 输出匹配率 + `VERIFY: PASS|FAIL`

### 8.2 主 Agent 校验

VERIFY 必须为 PASS。如有未匹配文献（stub），展示列表提醒用户后续手动补充。

**注意**：
- master.bib 是完整文献库（~200-300 条），项目 bib 文件只包含正文实际引用的条目
- `/pen-draft` 在写完每个 section 后，从 master.bib 中提取用到的条目追加到项目 bib

---

## 步骤 9：清理 pipeline 中间文件

文献工作流（lit-plan → lit-review → lit-tag → lit-pool）全部完成后，清理所有中间文件。

```bash
# 按约定：所有以 _ 开头的文件/目录均为 pipeline 中间产物
rm -rf structure/2_literature/_batch/              # lit-review batch 文件
rm -rf structure/2_literature/_tags/               # lit-tag 标签列表
rm -rf structure/2_literature/_tmp_agent_inputs/   # lit-pool agent 输入文件
rm -f  structure/2_literature/_tmp_pool_agent*_raw.md  # lit-pool agent 原始输出
rm -f  structure/2_literature/_tmp_pool_agent*.md       # lit-pool agent 标准化输出
rm -f  structure/2_literature/_*.json              # _dispatch_plan.json, _screening_merged.json,
                                                   # _tag_aggregate.json, _pool_prepare.json 等
```

> **命名约定**：pipeline 中所有中间文件/目录以 `_` 前缀命名，永久产出不以 `_` 开头。这样清理时用通配符 `_*` 即可，不需要逐个枚举文件名。
>
> **永久保留的文件**：direction reports（文献+标签）、screening_summary_report.md（筛选统计）、tag_report.md（标签统计）、citation_pool/（引用池）、master.bib（BibTeX）、literature_search_plan.md（检索方案）。

---

## 边界条件处理

| 情况 | 处理 |
|:-----|:-----|
| direction reports 不存在 | 停止，提示先运行 `/lit-review` |
| 某标签下文献数为0 | 在对话中警告，建议补检 |
| citation_pool/ 目录已存在 | 询问覆盖/跳过 |
| 某章节md不存在 | 跳过该章节的引用池更新 |
| direction report 格式异常 | 报告错误，继续处理其他 reports |
| tag_report.md 不存在 | 警告标签统计缺失，建议先运行 `/lit-tag` |
