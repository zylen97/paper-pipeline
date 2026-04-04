---
description: "从direction reports生成按标签汇总的引用池（Citation Pool），含引用场景、分级排序和引用偏好，并生成 master.bib"
---

# Lit-Pool — 引用池生成

从 `/lit-review` 产出的 direction reports 中提取所有入选文献，按功能标签汇总，生成 `citation_pool/` 目录（含 BG.md/LR.md/GAP.md/METHOD.md/DISC.md/COMP.md），为各章节写作提供结构化的引用指南。

**输入**：无参数，直接运行 `/lit-pool`

**前置条件**：`/lit-review` + `/lit-tag` 已完成（direction reports中必须含"功能标签"列）

---

## 全局约束

### ⛔ Fail-Fast 规则（最高优先级）
本 skill 中任何步骤出现以下情况，**必须立即停止整个流程并向用户汇报**，不得自行修复、跳过或继续：
- Python 脚本输出 `VERIFY: FAIL`
- 引用池文件数 ≠ 标签类别数
- `master.bib` 条目数与入选文献数不一致
- 任何脚本报错退出（exit code ≠ 0）

**汇报格式**：原样粘贴脚本 stderr/stdout 错误信息 + 说明出错步骤 + 等待用户指示。

### 模型选择
**subAgent 使用 Opus 模型**（不传 `model` 参数，继承主 Agent）。引用场景生成是写作任务，质量直接传导到下游 pen-draft，需要 Opus 的理解深度。

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
4. **中文文献处理**：文献可能为中文（来自CNKI数据库）。引用场景仍用中文撰写。citation key 必须原样复制，不可修改

## 输出格式（模板填空 + 结构分离）

> **设计原理**：Agent 只输出条目级内容（照模板格式填空），不写任何 `#` section headers。Python 脚本 `format_pool_agents.py` 按「标签」字段分组，确定性生成标准表格。

**步骤**：
1. 先读取模板文件：`structure/2_literature/_tmp_pool_agent{N}_raw.md`
2. 用 Write 工具**覆写**该文件，按模板中的格式逐条添加文献

**关键规则**：
- **不要添加任何 `#` 标题行**——标签分组由 Python 生成
- 每篇文献用 `### paperN` 开头，后跟 **7 行** `- key: value`
- **必须包含 `- 标签:` 字段**——**只写当前 agent 被分配处理的那一个标签**（如 BG / GAP-RQ1 / METHOD-先例），不要写该文献的所有标签。这是 Python 分组的唯一依据，写多个标签会导致下游脚本解析失败
- citation key 必须**原样复制**，不可修改
- 分级写中文：核心/重要/备选
- 引用场景用中文，文献信息保持英文
- 期刊名使用完整名称，不要缩写

**输出示例**：

```markdown
### paper1
- 标签: BG
- citation_key: smith2024b
- 分级: 核心
- 作者: Smith et al.
- 年份: 2024
- 引用场景: 中文引用场景描述
- 期刊: JOURNAL OF CONSTRUCTION ENGINEERING AND MANAGEMENT

### paper2
- 标签: GAP-RQ1
- citation_key: lee2023s
- 分级: 重要
- 作者: Lee et al.
- 年份: 2023
- 引用场景: 中文引用场景描述
- 期刊: RESEARCH POLICY
```
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

## 步骤 7：生成总报告 master_report.md（两步法）

**设计原理**：master_report 80% 是数据搬运（竞品表、方法先例表、标签统计），20% 是判断（Gap 真实性、可行性结论）。用 Python 处理前者，主 Agent 直接填写后者——不开 subAgent，因为主 Agent 已有完整上下文。

### 7.1 Python 生成报告骨架

```bash
python3 ~/.claude/skills/lit-pool/generate_master_report.py \
  --pool-dir structure/2_literature/citation_pool/ \
  --data-dir structure/2_literature/ \
  --idea-file structure/0_global/idea.md \
  --output structure/2_literature/master_report.md
```

**脚本职责**（`generate_master_report.py`）：
1. 从 `screening_summary_report.md` 提取检索总量（加总各方向检索数）
2. 从 `direction*_report.md` 提取各方向分级分布 + 跨方向去重后的全局分级计数
3. 从 `citation_pool/COMP.md` 提取竞品表格（截断120字 + 注明"详见COMP.md"）
4. 从 `citation_pool/METHOD.md` 提取方法论先例表格（核心+重要，上限20篇）
5. 从 `tag_report.md` 提取标签充足性数据 + 自动标出达标率最低的标签
6. 从 `citation_pool/BG.md` 提取近年文献列表，作为紧迫性填写的参考素材
7. 生成 `master_report.md`，判断性内容留 `<!-- JUDGE: ... -->` 占位符
8. 文献分布表分两行展示：各方向小计（含重复）+ 去重后独立文献数
9. stdout 输出统计 + `VERIFY: PASS|FAIL`（含数学校验：tier sum == total_dedup）

> **数据源约束**：脚本只依赖永久文件（direction reports / tag_report.md / screening_summary / citation_pool/），不依赖任何 `_*.json` 中间文件。清理顺序不影响结果。

### 7.2 主 Agent 填写判断（不开 subAgent）

主 Agent 读取 `master_report.md`，基于当前对话上下文（已跑完 lit-review/lit-tag/lit-pool 全流程），直接用 Edit 工具替换每个 `<!-- JUDGE: ... -->` 占位符：

| 判断项 | 填写内容 | 质量要求 |
|:-------|:---------|:---------|
| 竞品判断 | 直接竞品有/无、差异化空间、间接竞品、结论 | 列出具体论文和差异点 |
| Gap 验证 | 每个 Gap: ✅/⚠️/❌ + 文献支撑 + 理由 | 每个 Gap 至少引用 2 篇文献作为证据 |
| 方法论结论 | 有充分先例/有部分先例/首次应用 | 引用 METHOD 表格中的具体数字 |
| 紧迫性 | 高/中/低 + 行业证据 + 趋势 | **至少引用 2-3 篇 BG 文献**（骨架已提供参考列表）；列出具体政策文件名或行业事件 |
| 补检建议 | 基于标签缺口给具体建议 | **即使全达标，也检查**：(1)达标率最低的标签 (2)某个RQ的DISC是否偏少 (3)是否有论点缺乏支撑。如确实无需补检，说明理由 |
| 综合评估 | 可行性 + 核心发现 + 设计建议 | 核心发现 3-5 条；设计建议 2-3 条 |

### 7.3 质量校验

主 Agent 完成判断填写后，**必须**执行以下校验：

1. **占位符清零**：`grep -c 'JUDGE' master_report.md` 必须为 0（所有占位符已替换）
2. **表格完整性**：竞品表行数 > 0、方法论先例表行数 > 0、标签充足性表有 5 行数据
3. **判断一致性**：Gap 评估结论与 lit-review 步骤 3 的初步判断一致（如有不一致，说明原因）

校验通过后在对话中展示：
1. 可行性结论
2. 竞品预警（如有）
3. Gap 真实性评估
4. 引用池充足性（按标签）
5. 补检建议（如有）
6. **下一步建议**：用户审阅 master_report.md + method_landscape.md → 运行 `/idea-refine` 迭代优化 idea → 进入步骤④ 技术章节开发

---

## 步骤 7.5：生成方法论综述报告 method_landscape.md

**设计原理**：从 `citation_pool/METHOD.md` 的结构化引用数据中，综合文献方向报告和 idea.md 的方法设计，生成一份面向技术章节开发的方法论地图。该报告是 `/idea-refine` 和技术章节开发的关键输入。

### 7.5.1 主 Agent 综合写作（不开 subAgent）

主 Agent 读取以下文件：
1. `structure/2_literature/citation_pool/METHOD.md`（METHOD-基础 + METHOD-先例）
2. `structure/0_global/idea.md`（§3 方法论选择论证）
3. `structure/2_literature/direction*_report.md`（方法相关方向的完整报告）

写入 `structure/2_literature/method_landscape.md`，结构如下：

```markdown
# 方法论综述报告

> **生成日期**: {YYYY-MM-DD}
> **数据来源**: citation_pool/METHOD.md ({N}篇) + direction reports
> **定位**: 为技术章节开发和 /idea-refine 提供方法论基础

## 1. 建模策略综述
{综述相关研究采用的建模方法、模型类型、求解策略，按频率/主流程度排列}

## 2. 变量选取共性与差异
{核心变量、控制变量、调节/中介变量的通行做法，标注本研究的选取与主流的异同}

## 3. 数据与样本通行做法
{数据来源、样本规模、采样策略的行业惯例}

## 4. 方法创新空间
{哪些方法路径已被充分探索（做烂了），哪些还有创新机会，结合本研究情境的具体建议}

## 5. 与本研究方法设计的对照
{逐条对比 idea.md §3 的方法选择与文献中的主流做法，标出差异点和可借鉴点}
```

### 7.5.2 质量要求

- 每个章节必须引用具体文献（citation key），不得泛泛而谈
- §4 创新空间必须结合本研究的具体情境，不是通用建议
- §5 对照必须逐条对应 idea.md §3 的内容
- 总字数 1000-2000 字（中文）
- 如包含中文文献（CNKI来源），在引用时注明"（国内学者）"以区分国内外研究脉络

---

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
- `/method-end` 和 `/pen-outline` 在确认要点写入章节 md 时，从 master.bib 提取新增 citation key 条目追加到项目 bib
- `/pen-draft` 仅做 bib 验证（检查 key 是否存在），不负责同步

> **中文文献 BibTeX 提示**：CNKI 来源文献的 BibTeX 条目自动包含 `language = {chinese}` 字段。LaTeX 编译需使用 xelatex/lualatex + UTF-8 编码以正确渲染中文。

---

## 步骤 9：清理 pipeline 中间文件

文献工作流（lit-plan → lit-review → lit-tag → lit-pool）全部完成后，清理所有中间文件。

```bash
# 按约定：所有以 _ 开头的文件/目录均为 pipeline 中间产物
rm -rf structure/2_literature/_batch/              # lit-review batch 文件
rm -rf structure/2_literature/_tags/               # lit-tag 标签列表
rm -rf structure/2_literature/_tmp_agent_inputs/   # lit-pool agent 输入文件（目录形式）
rm -f  structure/2_literature/_tmp_agent_input_*.txt   # lit-pool agent 输入文件（散文件形式）
rm -f  structure/2_literature/_tmp_pool_agent*_raw.md  # lit-pool agent 原始输出
rm -f  structure/2_literature/_tmp_pool_agent*.md       # lit-pool agent 标准化输出
rm -f  structure/2_literature/_*.json              # _dispatch_plan.json, _screening_merged.json,
                                                   # _tag_aggregate.json, _pool_prepare.json 等
```

> **命名约定**：pipeline 中所有中间文件/目录以 `_` 前缀命名，永久产出不以 `_` 开头。这样清理时用通配符 `_*` 即可，不需要逐个枚举文件名。
>
> **永久保留的文件**：direction reports（文献+标签）、screening_summary_report.md（筛选统计）、tag_report.md（标签统计）、citation_pool/（引用池）、master.bib（BibTeX）、method_landscape.md（方法论综述）、literature_search_plan.md（检索方案）。

### 📌 Checkpoint 3：Git 备份文献管线最终交付物（不可跳过）

清理完成后，**必须**备份整个文献管线的最终产出：

```bash
git add structure/2_literature/citation_pool/ \
       structure/2_literature/master.bib \
       structure/2_literature/master_report.md \
       structure/2_literature/method_landscape.md \
       structure/2_literature/screening_summary_report.md
git commit -m "Checkpoint: lit-pool complete (citation pool + master.bib + method_landscape)"
```

> **为什么**：这是 lit-plan → lit-review → lit-tag → lit-pool 四步管线的最终交付物，直接喂给下游 pen-draft 写作。

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
