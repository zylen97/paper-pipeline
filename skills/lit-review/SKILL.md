---
description: "分析RIS文献（含CNKI转换）、生成方向报告与总报告、筛选精简文献池（Literature Review & Screening Pipeline）"
---

# Lit-Review — 文献分析与筛选

对用户提供的RIS文件进行系统性分析，通过并行subAgent逐方向筛选，生成方向报告和总报告，最终精简文献池。

**输入** `$ARGUMENTS`：可选，指定处理哪些方向。示例：
- `/lit-review` — 处理所有有RIS文件的方向
- `/lit-review 1,3,5` — 只处理方向1、3、5
- `/lit-review 2` — 只处理方向2

---

## 步骤 0：前置检查与上下文加载

### 0.1 检查检索方案
- 读取 `structure/2_literature/literature_search_plan.md`
- 不存在 → 停止，提示用户先运行 `/lit-plan`
- 提取：`{TOTAL_BUDGET}`（总预算）、方向列表、每方向的配额、优先级

### 0.2b 检查并转换 CNKI 导出文件（仅需时执行）

扫描 `structure/2_literature/` 下的 `.enw` 文件：

- **无 `.enw` 文件** → 跳过此步骤
- **有 `.enw` 文件** → 调用转换脚本（支持多个输入文件一次性转换）：
  ```bash
  python3 ~/.claude/skills/lit-review/cnki_enw_to_ris.py \
    --input structure/2_literature/*.enw \
    --output structure/2_literature/cnki_combined.ris \
    --skip-newspaper
  ```
  或按方向逐个转换：
  ```bash
  python3 ~/.claude/skills/lit-review/cnki_enw_to_ris.py \
    --input structure/2_literature/direction1_cnki.enw \
    --output structure/2_literature/direction1_cnki.ris \
    --skip-newspaper
  ```
- 展示转换报告（总条数、成功转换数、年份缺失数），等待用户确认
- 转换完成后，后续步骤统一处理 `.ris` 文件，无需区分来源
- **判断依据**：是否有 `.enw` 文件存在即可，无需读取上游检索平台配置
- **注意**：`.enw` 文件的命名应与方向对应（如 `direction1_cnki.enw`），或由用户在确认时指定对应关系

### 0.2 加载研究上下文
- 读取 `CLAUDE.md` → 项目编号、标题、方法、目标期刊
- 读取 `structure/0_global/idea.md` → RQ、Gap、方法论、贡献意图
- 从 `literature_search_plan.md` 头部提取 `{IDEA_MATURITY}`（mature / exploratory）
- 将以上浓缩为 `{RESEARCH_CONTEXT}`（≤ 800字），包含：
  - 论文标题与一句话概括
  - RQ简述（如有；exploratory模式下可能没有，写"待文献分析后确定"）
  - 方法论框架（如有）
  - 核心矛盾/机制（如有）
  - 目标期刊

### 0.3 扫描RIS文件 + 生成调度计划（Python 脚本）

**本步骤由 Python 脚本自动完成**，替代主 Agent 手动 glob 计数和拆分计算。

```bash
python3 ~/.claude/skills/shared/dispatch_plan.py --mode ris \
  --input-dir structure/2_literature/ \
  --plan-file structure/2_literature/literature_search_plan.md \
  --limit 30 \
  --template-dir structure/2_literature/_batch/ \
  --directions "{$ARGUMENTS 指定的方向，如 1,3,5；不指定则省略此参数}"
```

**脚本职责**（`dispatch_plan.py --mode ris`）：
1. 扫描 `*.ris` 文件，按文件名提取方向编号
2. 计数每个 RIS 文件的 `TY  -` 行数
3. 从 plan 文件提取各方向配额
4. 按 ⌈N/30⌉ 自动拆分，生成 agent 调度表
5. 为每个 agent 在 `_batch/` 目录生成模板文件（`d*_batch*_raw.md`），内含条目格式示例
6. 自动拆分 RIS 为 chunk 文件（`_batch/_chunks/d{N}_batch{M}.ris`），并验证每个 chunk 的条目数与调度计划一致
7. stdout 输出调度表 + `VERIFY: PASS|FAIL`
8. 写入 `_dispatch_plan.json`

**主 Agent 校验**：VERIFY 必须为 PASS。将 stdout 的调度表展示给用户。

无 RIS 文件 → 脚本报错退出，主 Agent 停止并提示用户从 WoS 下载。

### 0.4 检查已有报告
- 对每个待处理方向，检查 `directionX_*.md` 是否已存在
- 已存在 → 提示用户：是覆盖还是跳过？等待确认

### 0.5 展示处理计划
将 `dispatch_plan.py` 的 stdout 调度表展示给用户，等待确认后继续。
主 Agent 从 `_dispatch_plan.json` 读取调度信息构建 subAgent prompt。

---

## 全局约束

### ⛔ Fail-Fast 规则（最高优先级）
本 skill 中任何步骤出现以下情况，**必须立即停止整个流程并向用户汇报**，不得自行修复、跳过或继续：
- Python 脚本输出 `VERIFY: FAIL`
- Agent 输出校验不通过（日志行数 ≠ 条目数、入选+淘汰 ≠ 总数）
- Batch 文件数 ≠ 预期 subAgent 数
- Dry-run 显示 unmatched > 0
- 任何脚本报错退出（exit code ≠ 0）

**汇报格式**：原样粘贴脚本 stderr/stdout 错误信息 + 说明出错步骤 + 等待用户指示。

### 模型选择
**subAgent 使用 Sonnet 模型**（传 `model: "sonnet"` 参数）。筛选文献是分类判断任务，Sonnet 足以胜任，且速度更快。模板填空格式已消除格式遵从性风险。

### 输出语言
**所有描述性文本必须使用中文**，包括但不限于：入选理由、淘汰理由、方向小结、补检建议、Gap评估、竞品差异说明。文献的标题、期刊名、作者名保持原文（通常为英文）。SubAgent的Prompt中须明确传达此语言要求。

### SubAgent负载上限
**AGENT_ITEM_LIMIT = 30**

单个subAgent处理的文献条目数不得超过30篇。超过时必须拆分为多个subAgent并行处理。

### 槽位制并发控制
**MAX_CONCURRENT_AGENTS = 8**

同时运行的 subAgent 数**不超过 8 个**，每当 1 个 subAgent 完成（或失败重试后仍失败），立即从队列中取下一个启动，直到所有 subAgent 处理完毕。不等整批完成再启动下一批。

**失败重试**：subAgent 失败 → 自动重试一次 → 仍失败则报告用户。

### 质量验证（三层保障）

**第一层：逐篇处理日志**。subAgent输出必须附逐篇处理日志表：

| # | 第一作者 | 年份 | 有摘要 | 决策 | 关键词/短语 |

"关键词/短语"列：从摘要中提取一个关键短语证明确实读了；淘汰文献也须注明原因；无摘要则标"⚠️仅凭标题"。
主Agent校验：日志行数 = 分配条目数，入选+淘汰 = 总数。不通过 → 自动重跑该agent（最多1次）→ 仍不通过则报告用户。

**第二层：摘要锚定**。入选文献的入选理由必须包含至少一个来自摘要的具体信息（方法、发现、数据等），不可仅凭标题泛泛概括。无摘要的入选文献须标注`⚠️仅凭标题，建议人工复核`。

**第三层：主Agent抽检**。主Agent随机抽取2-3篇入选文献，回原RIS文件核对日志中的"关键词/短语"是否出现在AB字段中。不匹配则标记该batch需重跑。

---

## 步骤 1：并行调度SubAgent分析

### 1.0 读取调度计划

从步骤 0.3 生成的 `_dispatch_plan.json` 读取调度信息：
- 每个 agent 的方向编号、条目范围、条目数、配额分配
- 拆分和计数已由 Python 脚本完成，主 Agent **不做任何算术**

所有 subAgent 按**槽位制**启动（同时不超过 8 个，完成一个补一个）。

> **配额分配**：当一个方向拆分为K个agent时，该方向配额按比例分配给每个agent（方向配额/K，向上取整）。最终合并时由主Agent按方向总配额截断。

### 防重复启动规则

主Agent在补发新 agent 前，**必须**维护一个已启动 agent 的方向+批次注册表（在对话中以列表形式记录）。补发时：
1. 检查待发 batch 是否已在注册表中
2. 如果已存在 → 跳过，不重复启动
3. 每次启动后立即更新注册表

### 每个SubAgent的Prompt模板

```
你是一个学术文献分析专家。请分析以下RIS文件中的文献，为一篇学术论文的文献综述做筛选。

## 研究背景
{RESEARCH_CONTEXT}

## 当前分析方向
- **方向编号**: {方向编号}
- **方向名称**: {方向名称}
- **层面**: {层面}
- **论文角色**: {论文角色说明}
- **配额**: {配额}篇（核心≤{x} / 重要≤{y} / 备选≤{z}）

## 分级标准
- **核心（Core）**: 必须引用。与本研究直接相关，是理论基础、方法论先例或直接竞品
- **重要（Important）**: 大概率引用。相关度高，提供重要背景或对比
- **备选（Backup）**: 可能引用。有一定相关性，可在需要时补充

## 任务
1. 读取RIS文件：{RIS文件路径}
2. 逐篇分析每条文献的标题、摘要、作者、期刊、年份
3. 判断每篇文献：
   a. 与本研究的相关度（高/中/低/无）
   b. 分级（核心/重要/备选/淘汰）
   c. 入选理由（1-2句话，说明为什么相关、在论文中扮演什么角色）
4. 淘汰相关度为"无"的文献
5. 按配额筛选：核心≤{x}篇，重要≤{y}篇，备选≤{z}篇
6. 如果高相关文献超出配额，优先保留：高被引 > 近5年 > 顶刊 > 方法论对标

## 中文文献处理
文献可能包含中文标题和摘要（来自CNKI数据库）。请按同样标准筛选：
- 入选理由仍用中文撰写
- 文献标题、作者名、期刊名保持原文（中文或英文均可）
- 无摘要的中文文献标注"⚠️仅凭标题，建议人工复核"

## 输出格式（模板填空 + 结构分离）

> **设计原理**：Agent 只输出条目级内容（照模板格式填空），不写任何 section headers、元数据或淘汰表格。Python 脚本 `format_batches.py` 从 `_dispatch_plan.json` 读取元数据，按「级别」字段分组，确定性生成标准 markdown 表格。这样 Agent 的输出零结构，格式偏移风险接近 0。

**步骤**：
1. 先读取模板文件：`structure/2_literature/_batch/d{方向编号}_batch{批次编号}_raw.md`
2. 用 Write 工具**覆写**该文件，按模板中的格式逐条添加入选文献

**关键规则**：
- **不要添加任何 `##` 标题行、`>` 元数据行或淘汰记录表格**——这些由 Python 生成
- 每篇入选文献用 `### 入选N` 开头，后跟 **6 行** `- key: value`
- **必须包含 `- 级别:` 字段**（核心/重要/备选），这是 Python 分组的依据
- 期刊名从 RIS 文件原样复制完整名称，**不要缩写**
- 年份必须是独立的 4 位数字
- 理由用中文，必须包含摘要中的具体信息；文献标题/期刊名/作者名保持英文原文
- 无入选文献则只写"无"

**输出示例**：

```markdown
### 入选1
- 级别: 核心
- 作者: Han
- 标题: An overall review of research on construction innovation
- 年份: 2023
- 期刊: ENGINEERING CONSTRUCTION AND ARCHITECTURAL MANAGEMENT
- 理由: 建筑业创新研究综述，梳理合作创新的研究脉络，为Introduction提供背景

### 入选2
- 级别: 重要
- 作者: Liu
- 标题: Evolution of innovation collaboration networks...
- 年份: 2025
- 期刊: BUILDINGS
- 理由: SAOM分析建筑业合作网络演化，方法论直接先例
```

此外，在对话中返回简要汇报（入选数、淘汰数、亮点说明），供主 Agent 校验。**不要将 markdown 保存为 direction report 文件**（方向报告由步骤 2 的 Python 脚本统一生成）。

### SubAgent的RIS读取策略

由于拆分后每个subAgent最多处理30条RIS条目（AGENT_ITEM_LIMIT），直接一次性读取全部分配的条目即可。

> 当方向被拆分时，主Agent在 `dispatch_plan.py` 阶段已预拆分 RIS 为 chunk 文件（`_batch/_chunks/d{N}_batch{M}.ris`），subAgent 直接读取对应 chunk 即可。

---

### 📌 Checkpoint 1：Git 备份 agent 输出（不可跳过）

所有 subAgent 完成后、运行任何 Python 脚本之前，**必须**先备份 agent 输出：

```bash
git add structure/2_literature/_batch/*_raw.md
git commit -m "Checkpoint: lit-review agent outputs (raw batch files)"
```

> **为什么**：62个 agent 的筛选结果是全流程最贵的数据（重跑需数小时）。后续 `dispatch_plan.py` 重跑会覆盖这些文件，如无备份将不可恢复。

---

## 步骤 2：汇总与跨方向分析（Python 脚本）

所有subAgent完成后，主Agent执行以下操作。**本步骤的合并、去重、报告生成全部由 Python 脚本完成，不使用 Agent/LLM**，以避免上下文溢出导致的静默数据丢失。

### 2.1 验证批次文件完整性
```bash
ls structure/2_literature/_batch/d*_batch*_raw.md | wc -l
```
输出的文件数必须等于 subAgent 总数。不一致 → 停止，报告哪些 batch 缺失。

### 2.2 格式标准化（Python 脚本）

将 Agent 输出的 key-value 块格式（`*_raw.md`）转换为 `merge_screening.py` 所需的标准 markdown 表格格式（`*.md`）。

```bash
python3 ~/.claude/skills/lit-review/format_batches.py \
  --batch-dir structure/2_literature/_batch/
```

**脚本职责**（`format_batches.py`）：
1. 读取所有 `d*_batch*_raw.md` 文件
2. 解析 key-value 块（`- 作者:` / `- 标题:` / `- 年份:` / `- 期刊:` / `- 理由:`）
3. 转换为标准 6 列 markdown 表格
4. 校验：每篇文献必须有 5 个字段完整、年份为 4 位数字
5. 输出标准化的 `d*_batch*.md`（去掉 `_raw` 后缀）
6. stdout 输出每个文件的解析结果 + `VERIFY: PASS|FAIL`

**主 Agent 校验**：VERIFY 必须为 PASS。FAIL 时展示具体错误给用户。

### 2.3 调用合并脚本
```bash
python3 ~/.claude/skills/lit-review/merge_screening.py \
  --batch-dir structure/2_literature/_batch/ \
  --plan-file structure/2_literature/literature_search_plan.md \
  --output-dir structure/2_literature/ \
  --budget {TOTAL_BUDGET}
```

**脚本职责**（`merge_screening.py`）：
1. 读取 `_batch/*.md`（或旧版 `*.json`），按 `direction` 分组
2. 同方向合并 `selected` 数组，去重（key = `first_author + year + title[:40]`）
3. 按方向配额截断（从 plan 文件提取配额）：core ≤ 25%, important ≤ 40%, backup ≤ 35%
4. 跨方向去重统计
5. 生成 7 个 `direction{N}_*_report.md`（含 markdown 表格）
6. 生成 `screening_summary_report.md`
7. 生成 `_screening_merged.json`（全局结构化数据，供步骤 5 使用）
8. stdout 输出校验摘要

> **双轨模式下的独立截断**：当 `structure/2_literature/_quota_result.json` 存在且 `dual_mode: true` 时，脚本自动启用中英文独立截断——通过检测文献标题/作者中的中文字符区分来源，WoS 和 CNKI 文献在同方向内按各自的配额上限独立截断后再合并。这确保中英文文献各自遵守数量约束，互不挤占。纯 WoS 模式下此机制不生效。

### 2.4 主Agent校验脚本输出
脚本 stdout 格式：
```
=== MERGE SUMMARY ===
Batch files parsed: {X}/{Y}
D1: {n} selected (core={a}, important={b}, backup={c})
...
Cross-direction duplicates: {n}
Final unique: {n}
Budget: {n}/{TOTAL_BUDGET} → PASS|FAIL
=== END SUMMARY ===
```

校验规则：
- `Batch files parsed: X/Y` → X 必须等于 Y，否则停止
- `Final unique` + `Cross-direction duplicates` 的数学关系必须自洽
- `Budget` 为 PASS 才继续；FAIL 时脚本自动按优先级削减（P2/P3 备选 → P1 备选 → 重要）

> **为什么用 Python 而非 Agent**：汇总任务是纯数据聚合（读 JSON → 去重 → 写报告），不需要 LLM 推理。Agent 方案在 subAgent 数量 > 20 时会因上下文溢出静默丢失数据，且无法自动校验完整性。Python 脚本无此限制，且输出精确计数供主 Agent 验证。

### 2.5 强制抽检（不可跳过）

主Agent **必须**执行以下操作，不得以"时间紧"或"数据量大"为由跳过：

1. 从入选文献中随机抽取 3 篇（每篇来自不同方向）
2. 对每篇：
   a. 在对应 RIS chunk 文件中用 Grep 搜索该文献的 TI 字段
   b. 读取该条目的 AB（摘要）字段
   c. 核对 batch raw 文件中该文献的"理由"是否包含摘要中的具体信息
3. 3篇全部通过 → 继续；任一篇不通过 → 报告并标记该 batch 需重跑

### 2.6 自动完整性校验（不可跳过）

合并脚本完成后、进入步骤 3 之前，主 Agent **必须**运行以下 Python 校验脚本，对全部产出物做端到端一致性检查：

```python
python3 -c "
import json, os, glob

base = 'structure/2_literature'
batch_dir = f'{base}/_batch'
plan_quotas = {}  # 必须从 _dispatch_plan.json 提取实际值
with open(f'{base}/_dispatch_plan.json') as f:
    dp = json.load(f)
    for d in dp['directions']:
        plan_quotas[int(d['id'])] = d['quota']
expected_directions = len(plan_quotas)

# 1. Artifact existence
raw_files = sorted(glob.glob(f'{batch_dir}/d*_batch*_raw.md'))
fmt_files = sorted(glob.glob(f'{batch_dir}/d*_batch[0-9]*.md'))
fmt_files = [f for f in fmt_files if '_raw' not in f]
reports = sorted(glob.glob(f'{base}/direction*_report.md'))
merged_json = f'{base}/_screening_merged.json'
summary = f'{base}/screening_summary_report.md'

errors = []
print('=== ARTIFACT CHECK ===')
print(f'Raw batch files:       {len(raw_files)}')
print(f'Formatted batch files: {len(fmt_files)}')
print(f'Direction reports:     {len(reports)}')
print(f'Merged JSON:           {\"YES\" if os.path.exists(merged_json) else \"MISSING\"}')
print(f'Summary report:        {\"YES\" if os.path.exists(summary) else \"MISSING\"}')

if len(raw_files) != len(fmt_files):
    errors.append(f'Raw ({len(raw_files)}) != Formatted ({len(fmt_files)})')
if len(reports) != expected_directions:
    errors.append(f'Direction reports: {len(reports)}, expected {expected_directions}')
if not os.path.exists(merged_json):
    errors.append('Merged JSON missing')

# 2. Per-direction quota compliance
if os.path.exists(merged_json):
    with open(merged_json) as f:
        data = json.load(f)
    dirs = data['directions']
    print()
    print('=== QUOTA COMPLIANCE ===')
    print(f'{\"Dir\":>4} {\"Quota\":>6} {\"Selected\":>8} {\"Core\":>5} {\"Imp\":>5} {\"Bak\":>5} {\"Status\":>8}')
    total = 0
    for k in sorted(dirs.keys(), key=int):
        v = dirs[k]
        core = sum(1 for p in v if p.get('tier','') == 'core')
        imp = sum(1 for p in v if p.get('tier','') == 'important')
        bak = sum(1 for p in v if p.get('tier','') == 'backup')
        q = plan_quotas[int(k)]
        status = 'OK' if len(v) <= q else 'OVER'
        if status == 'OVER':
            errors.append(f'D{k}: {len(v)} > quota {q}')
        print(f'D{k:>3} {q:>6} {len(v):>8} {core:>5} {imp:>5} {bak:>5} {status:>8}')
        total += len(v)

    unique = data.get('unique_count', 0)
    dupes = data.get('cross_direction_duplicates', 0)
    print()
    print(f'Total (pre-dedup):  {total}')
    print(f'Cross-dir dupes:    {dupes}')
    print(f'Final unique:       {unique}')

    # 3. Math consistency
    if total - dupes != unique:
        errors.append(f'Math: {total} - {dupes} != {unique}')

print()
if errors:
    print('=== VERIFY: FAIL ===')
    for e in errors:
        print(f'  ERROR: {e}')
else:
    print('=== VERIFY: PASS ===')
"
```

**校验内容**：
1. **产出物完整性**：raw batch 数 = formatted batch 数、direction report 数 = 实际方向数、merged JSON、summary report 全部存在
2. **配额合规**：每个方向入选数 ≤ 该方向配额，按 core/important/backup 分层展示
3. **数学一致性**：`total - cross_dupes == unique_count`

**注意**：脚本已从 `_dispatch_plan.json` 自动读取配额和方向数，无需手动替换。确保运行此脚本时 `_dispatch_plan.json` 尚未被清理。

主 Agent 校验：VERIFY 必须为 PASS。FAIL 时原样粘贴错误信息给用户，不得自行继续。

---

## 步骤 3：方向汇总与竞品预警

所有subAgent完成且步骤2汇总完毕后，主Agent在**对话中直接展示**以下内容（不生成独立文件）：

### 3.1 竞品预警
- 从所有direction reports的"潜在竞品"字段中提取竞品论文
- 如发现竞品，立即展示：

| # | 作者 | 标题 | 年份 | 来源方向 | 与本研究的相似度 | 关键差异 |
|:--|:-----|:-----|:----:|:---------|:---------------:|:---------|

- 给出初步判断：直接竞品有/无，差异化空间
- 如无竞品：明确告知"未发现直接竞品，创新性风险低"

### 3.2 初步Gap判断
- 基于各方向分析，简要评估idea.md中预设Gap的真实性
- 格式：`Gap X: ✅真实 / ⚠️需关注 / ❌已被填补` + 一句理由

### 3.3 方法论先例摘要
- 列出发现的方法论先例论文（如有），1行/篇

> **注**：完整的6问评估报告（master_report.md）将在 `/lit-pool` 最后一步生成，届时标签和引用池数据齐全。

---

## 步骤 4：对话汇报与用户确认

在对话中向用户展示：

1. **竞品预警**（步骤3.1的结果）
2. **初步Gap判断**（步骤3.2的结果）
3. **文献分布统计**（各方向的数量分布）
4. **方法论先例**（步骤3.3的结果）
5. **下一步建议**：运行 `/lit-tag` 为入选文献打功能标签

等待用户批准后 → 执行步骤 5

---

## 步骤 5：清理RIS文件（Python 脚本 + git 备份）

用户批准后，使用 Python 脚本清理 RIS 文件。**清理前必须先 git 备份原始 RIS 文件**，确保可恢复。

### 5.1 Git 备份原始 RIS
```bash
git add structure/2_literature/*.ris
git commit -m "Backup: original RIS files before screening cleanup"
```
> 如果 RIS 文件已被 git 跟踪且无修改，此步跳过。

### 5.2 Dry-run 预览
```bash
python3 ~/.claude/skills/lit-review/clean_ris.py \
  --merged-json structure/2_literature/_screening_merged.json \
  --ris-dir structure/2_literature/ \
  --dry-run
```

**脚本职责**（`clean_ris.py`）：
1. 从 `_screening_merged.json` 提取各方向入选文献标题
2. 对每个 RIS 文件：`utf-8-sig` 编码读取 → `TY  -` 分割条目 → `TI  -` 字段匹配
3. 匹配策略：精确标题 → normalize(去标点+小写)前缀比较 → `AU  -` + `PY  -` 辅助
4. `--dry-run` 模式只输出统计，不写文件
5. 保留数为 0 的方向**不覆写**（安全检查）

### 5.3 主Agent校验 dry-run 输出
脚本 stdout 格式：
```
=== CLEAN PREVIEW ===
D1: 283 → 49 (matched 49/49, unmatched 0)
D2: 220 → 47 (matched 47/47, unmatched 0)
...
Total: 1899 → 285
Unmatched: 0
=== END PREVIEW ===
```

校验规则：
- `Unmatched` 必须为 0。> 0 时暂停，列出未匹配文献让用户决定
- 将 dry-run 结果展示给用户确认

### 5.4 正式执行
用户确认后，去掉 `--dry-run` 重新运行：
```bash
python3 ~/.claude/skills/lit-review/clean_ris.py \
  --merged-json structure/2_literature/_screening_merged.json \
  --ris-dir structure/2_literature/
```

> **恢复方法**：如清理有误，可 `git checkout -- structure/2_literature/*.ris` 恢复原始文件。

---

## 边界条件处理

| 情况 | 处理 |
|:-----|:-----|
| literature_search_plan.md 不存在 | 停止，提示先运行 `/lit-plan` |
| 某方向无对应RIS文件 | 跳过该方向，在对话中提示 |
| RIS文件为空或格式异常 | 跳过，报告错误 |
| 某方向入选文献数 < 10 | 警告引用池可能不足，建议补检 |
| 某方向发现直接竞品 | 在对话中**立即预警**，不等到总报告 |
| subAgent超时或失败 | 报告失败方向，继续处理其他方向 |
| 已有方向报告 | 按步骤0.4处理（覆盖/跳过） |
| 去重后超预算 | 步骤2脚本自动按优先级削减 |
| idea.md 不存在 | 停止，提示先完善 idea |
| batch 文件解析失败 | 报告具体文件名和错误信息，停止合并 |
| batch 文件数 ≠ 预期 subAgent 数 | 停止，报告缺失的 batch 文件 |
| dry-run 显示 unmatched > 0 | 暂停，列出未匹配文献，让用户决定是否继续 |
| RIS 文件未被 git 跟踪 | 先 `git add` + `git commit` 备份，再清理 |
