---
description: "对已筛选文献打功能标签（按RQ分类），生成带标签的direction reports（Literature Tagging）"
---

# Lit-Tag — 文献功能标签标注

对 `/lit-review` 产出的筛选报告中的入选文献，逐篇标注功能标签，输出带标签的完整 direction reports。

**输入** `$ARGUMENTS`：可选，指定处理哪些方向。示例：
- `/lit-tag` — 处理所有有报告的方向
- `/lit-tag 1,3,5` — 只处理方向1、3、5

**前置条件**：`/lit-review` 已完成，`structure/2_literature/` 下存在 direction reports

---

## 全局约束

### ⛔ Fail-Fast 规则（最高优先级）
本 skill 中任何步骤出现以下情况，**必须立即停止整个流程并向用户汇报**，不得自行修复、跳过或继续：
- Python 脚本输出 `VERIFY: FAIL`
- `insert_tags.py` 报 `NO_TAGS` 错误（文献缺标签）
- 标签数 ≠ 文献数（任一分级内不匹配）
- 任何脚本报错退出（exit code ≠ 0）

**汇报格式**：原样粘贴脚本 stderr/stdout 错误信息 + 说明出错步骤 + 等待用户指示。

### 模型选择
**subAgent 使用 Sonnet 模型**（传 `model: "sonnet"` 参数）。打标签是多标签分类任务，Sonnet 准确率接近 Opus，且速度更快。模板填空格式已消除格式遵从性风险。

### 输出语言
**所有描述性文本必须使用中文**，包括但不限于：依据短语、标签锚定说明、处理日志中的备注。文献的标题、期刊名、作者名保持原文。

### SubAgent负载上限
**AGENT_ITEM_LIMIT = 30**

单个subAgent处理的文献条目数不得超过30篇。超过时必须拆分。

### 槽位制并发控制
**MAX_CONCURRENT_AGENTS = 8**

同时运行的 subAgent 数**不超过 8 个**，每当 1 个 subAgent 完成（或失败重试后仍失败），立即从队列中取下一个启动，直到所有 subAgent 处理完毕。不等整批完成再启动下一批。

失败重试：subAgent 失败 → 自动重试一次 → 仍失败则报告用户。

### 质量验证（两层保障）

**第一层：数量校验**。`insert_tags.py` 自动校验每个分级内的标签数 == 文献数。不匹配 → 报错停止。

**第二层：主Agent抽检**。`insert_tags.py` 完成后，主Agent随机抽取2-3篇，核对标签是否与入选理由匹配。不匹配则报告用户。

---

## 步骤 0：前置检查与上下文加载

### 0.1 扫描 direction reports + 生成调度计划（Python 脚本）

**本步骤由 Python 脚本自动完成**，替代主 Agent 手动读报告数文献。

```bash
python3 ~/.claude/skills/shared/dispatch_plan.py --mode report \
  --input-dir structure/2_literature/ \
  --limit 30 \
  --template-dir structure/2_literature/_tags/ \
  --directions "{$ARGUMENTS 指定的方向，如 1,3,5；不指定则省略此参数}"
```

**脚本职责**：扫描 `direction*_report.md` → 计数入选文献 → 按 ⌈N/30⌉ 拆分 → 从 report 读取 tier 结构生成标签模板文件（`_tags/d*_tags.md`，含预写的 section headers 和序号占位） → 输出调度表 + `_dispatch_plan.json`。

不存在 reports → 脚本报错退出，主 Agent 停止并提示先运行 `/lit-review`。
VERIFY 必须为 PASS。

### 0.2 加载研究上下文
- 读取 `CLAUDE.md` → 项目编号、标题、方法、目标期刊
- 读取 `structure/0_global/idea.md` → 提取RQ列表、Gap描述、方法论、贡献意图
- 将以上浓缩为 `{RESEARCH_CONTEXT}`（≤ 800字）

### 0.3 检查已有标签
- 检查direction reports中是否已有"功能标签"列
- 已有 → 提示用户：是覆盖还是跳过？等待确认

### 0.4 展示处理计划
在对话中展示：

```
待打标签：
| # | 方向 | 入选文献数 | Agent数 | 状态 |
|---|------|-----------|---------|------|
| 1 | XXX  | 45篇 | 1 | 待处理 |
| 3 | YYY  | 52篇 | 2 | 待处理（拆分） |
预计调用 {N} 个并行subAgent
```

等待用户确认后继续。

---

## 步骤 1：并行调度SubAgent打标签

### 1.0 读取调度计划

从步骤 0.1 生成的 `_dispatch_plan.json` 读取调度信息（拆分和计数已由 Python 脚本完成，主 Agent **不做任何算术**）。

所有 subAgent 按**槽位制**启动（同时不超过 8 个，完成一个补一个）。

### 每个SubAgent的Prompt模板

```
你是一个学术文献分类专家。请对以下已筛选的文献标注功能标签。

## 研究背景
{RESEARCH_CONTEXT}

## 研究问题（从idea.md动态提取，数量不固定，通常2-3个）
{逐条列出idea.md中的所有RQ，如：}
- **RQ1**: {RQ1内容}
- **RQ2**: {RQ2内容}
- **RQ3**: {RQ3内容，如有}

## 当前分析方向
- **方向编号**: {方向编号}
- **方向名称**: {方向名称}
- **论文角色**: {论文角色说明}

## 功能标签定义
| 标签 | 含义 |
|:-----|:-----|
| BG | 研究背景——**严格限制投稿年前3年内发表**（如2026年投稿则仅限2024-2026）且与研究主题相关（沾边即可）。高引经典不标BG应标LR，无例外。BG与LR不互斥 |
| LR | 文献综述主体——落在Literature Review讨论的主题范围内即可纳入，构建理论脉络、梳理研究演进 |
| GAP-RQx | Gap支撑——研究同一大主题但视角/维度/方法与本文RQx不同的文献（宽泛纳入）。与LR不互斥。**按实际RQ数量动态生成**（如有2个RQ则为GAP-RQ1、GAP-RQ2） |
| METHOD-基础 | 方法论理论来源——定义/提出本文所用方法的文献（引用句式："was first proposed by..."） |
| METHOD-先例 | 方法论应用先例——在其他领域应用过本文方法的文献（引用句式："has been applied to..."） |
| DISC-RQx | Discussion对标——与本文RQx相关的文献（宽泛纳入，后续人工精筛）。**按实际RQ数量动态生成** |
| COMP | 竞品论文——与本研究高度相似，需差异化分析 |

> **GAP vs DISC**：GAP关注"别人怎么研究这个大问题"（构建Gap论证：同主题不同视角），
> DISC关注"我的结果可以跟谁对话"（解读结果）。同一文献可同时标GAP-RQx和DISC-RQx。
> **COMP与DISC的区别**：COMP关注"问题重叠"（影响能不能做），DISC关注"主题相关"（影响怎么讨论）。
> 同一文献可同时标COMP和DISC-RQx。

## 任务
1. 读取该方向的筛选报告（direction report）
2. 对每篇入选文献，基于其标题、期刊、入选理由，标注功能标签（可多个）
3. 每篇文献至少标注1个标签
4. 文献可能为中文（来自CNKI数据库），按同样标签定义标注。中文标题不影响标签判断。注意：CNKI来源文献的年份可能从URL推断，如无法确认发表年份在投稿年前3年内，不标BG

## 输出（模板填空，只输出标签）

> **设计原理**：Agent 只负责判断标签，表格插列由 Python 脚本（`insert_tags.py`）完成。模板文件由 `dispatch_plan.py --mode report` 预生成，section headers 和序号已固定，Agent 只需在 `→` 后填写标签。

**步骤**：
1. 先读取模板文件：`structure/2_literature/_tags/d{方向编号}_tags.md`
2. 用 Write 工具**覆写**该文件，在每行 `→` 后填写标签

**模板示例**（section headers 和序号已由 Python 预写）：

```markdown
## 核心文献（Core）
1 → LR+GAP-RQ1+DISC-RQ1
2 → LR+METHOD-先例+COMP
3 → BG+LR

## 重要文献（Important）
1 → LR+DISC-RQ2
2 → METHOD-基础
3 → LR+GAP-RQ2

## 备选文献（Backup）
1 → LR
2 → LR+DISC-RQ3
```

**格式约束**：
- **不要修改 `##` 标题行和序号**——只在 `→` 后填写标签
- 多个标签用 `+` 分隔，禁止用 `|`、`;` 或其他分隔符
- 每篇至少1个标签，不可留空
- 标签名称严格匹配定义表（区分大小写），不可自创标签
- **不要修改 direction report 文件**——标签插入由 Python 脚本完成

**⚠️ 关键警告：Write 工具写入内容时，绝对不要包含行号前缀！**
Read 工具的输出格式为 `行号→内容`（如 `1→## 核心文献（Core）`），其中 `行号→` 是显示用的前缀，**不是文件的实际内容**。用 Write 工具覆写时，只写实际内容，不要把 `1→`、`2→` 等行号前缀写进去。

**正确写法**（Write 工具的 content 参数）：
```
## 核心文献（Core）
1 → LR+GAP-RQ1
2 → LR+METHOD-先例
```

**错误写法**（混入了 Read 的行号前缀）：
```
3→## 核心文献（Core）
4→1 → LR+GAP-RQ1
5→2 → LR+METHOD-先例
```

**语言要求**：标签列表无需中文说明，只需在 `→` 后填标签即可。
```

---

## 步骤 2：标签插入 + 聚合统计（Python 脚本）

所有 subAgent 完成后，先由 Python 脚本将标签插入 direction reports，再做聚合统计。

### 2.1 标签插入（Python 脚本）

```bash
python3 ~/.claude/skills/lit-tag/insert_tags.py \
  --tags-dir structure/2_literature/_tags/ \
  --report-dir structure/2_literature/
```

**脚本职责**（`insert_tags.py`）：
1. 读取所有 `_tags/d*_tags.md` 文件，解析 `序号: 标签` 列表
2. 读取对应的 direction report（6 列表格）
3. 校验：标签数 == 文献数（每个分级内分别校验）
4. 在"入选理由"列前插入"功能标签"列，生成 7 列表格
5. 覆写回 direction report
6. stdout 输出每个方向的处理结果 + `VERIFY: PASS|FAIL`

**主 Agent 校验**：VERIFY 必须为 PASS。FAIL 时展示错误给用户。

### 2.2 调用标签聚合脚本

```bash
python3 ~/.claude/skills/lit-tag/tag_aggregate.py \
  --report-dir structure/2_literature/
```

**脚本职责**（`tag_aggregate.py`）：
1. 解析所有 `direction*_report.md` 的 markdown 表格
2. 提取每篇文献的功能标签和分级
3. 计算全局标签分布（标签 × 分级交叉表）
4. 计算达标率（实际/Pool目标，BG=50, LR=150, GAP=75, METHOD=60, DISC=65）
5. 判断均衡性（≥80% ✅, 50-80% ⚠️, <50% ❌）
6. 计算各方向的标签贡献表
7. 生成 `tag_report.md` 和 `_tag_aggregate.json`
8. stdout 输出统计摘要 + `VERIFY: PASS|FAIL`

### 2.3 主 Agent 校验脚本输出

```
=== VERIFY: PASS|FAIL ===
```

校验规则：
- VERIFY 必须为 PASS。FAIL 时停止，展示具体错误给用户
- 特别注意：如有 `NO_TAGS` 错误（文献缺标签），说明 subAgent 打标签有遗漏，需重跑对应 agent
- 将 stdout 的统计数据展示给用户

---

## 步骤 3：对话汇报

在对话中展示：
1. 全局标签统计表
2. 均衡性预警结果
3. 如有⚠️或❌标签，建议具体补检方向
4. 下一步建议：运行 `/lit-pool` 生成引用池

### 📌 Checkpoint 2：Git 备份 tagged reports（不可跳过）

步骤3汇报完毕、用户确认后，**必须**备份：

```bash
git add structure/2_literature/direction*_report.md \
       structure/2_literature/tag_report.md \
       structure/2_literature/_tag_aggregate.json \
       structure/2_literature/_screening_merged.json \
       structure/2_literature/_tags/ \
       structure/2_literature/*.ris
git commit -m "Checkpoint: lit-tag complete (tagged reports + cleaned RIS)"
```

> **为什么**：tagged direction reports 是 `/lit-pool` 的输入，也是人工复核的基准。此备份覆盖 lit-review + lit-tag 两个 skill 的全部产出。

---

## 边界条件处理

| 情况 | 处理 |
|:-----|:-----|
| direction reports 不存在 | 停止，提示先运行 `/lit-review` |
| 某方向report中无入选文献 | 跳过该方向 |
| 已有"功能标签"列 | 询问覆盖/跳过 |
| subAgent超时或失败 | 报告失败方向，继续处理其他方向 |
| 某文献无法判断标签 | 标注为"LR"（最宽泛的默认标签） |
