---
description: "从direction reports生成按标签汇总的引用池（Citation Pool），含引用场景、分级排序和引用偏好"
---

# Lit-Pool — 引用池生成

从 `/lit-review` 产出的 direction reports 中提取所有入选文献，按功能标签汇总，生成 `citation_pool.md`，为各章节写作提供结构化的引用指南。

**输入**：无参数，直接运行 `/lit-pool`

**前置条件**：`/lit-review` + `/lit-tag` 已完成（direction reports中必须含"功能标签"列）

---

## 全局约束：SubAgent负载上限

**AGENT_ITEM_LIMIT = 50**

单个subAgent处理的文献条目数不得超过50篇。超过时必须拆分为多个subAgent并行处理。此约束适用于步骤3中所有引用池生成任务。

---

## 步骤 0：前置检查

- 读取 `CLAUDE.md` → 提取项目编号
- 读取 `structure/0_global/idea.md` → 提取研究上下文（RQ、方法论，用于生成引用场景）
- Glob `structure/2_literature/direction*_report.md` → 确认存在
  - 不存在 → 停止，提示先运行 `/lit-review`
- 检查 `structure/2_literature/citation_pool.md` 是否已存在
  - 已存在 → 询问用户：覆盖还是跳过？

---

## 步骤 1：提取文献 + 预估标签文献量（主Agent执行）

### 1.1 提取文献

逐个读取所有 direction reports，从每篇入选文献（核心+重要+备选）提取：

| 字段 | 来源 |
|:-----|:-----|
| 作者 | 表格"作者"列 |
| 年份 | 表格"年份"列 |
| 标题 | 表格"标题"列 |
| 期刊 | 表格"期刊"列 |
| 功能标签 | 表格"功能标签"列（可多个，如 LR+METHOD） |
| 分级 | 所在区块标题（核心/重要/备选） |
| 入选理由 | 表格"入选理由"列 |
| 来源方向 | 该 direction report 的方向编号和名称 |

**跨方向去重**：
- 以（第一作者姓氏, 年份, 标题前30字符）为去重键
- 同一文献出现在多个方向 → 合并功能标签，保留最高分级，合并入选理由

### 1.2 预估每个标签的文献量

去重后，统计每个标签组的文献数量 N_tag（一篇文献有多个标签时，在每个标签下各计一次）。

在对话中展示统计结果：

```
| 标签 | 去重后文献数 N_tag |
|:-----|:------------------:|
| BG   | {n} |
| LR   | {n} |
| GAP-RQ1 | {n} |
| GAP-RQ2 | {n} |
| GAP-RQ3 | {n} |
| METHOD-基础 | {n} |
| METHOD-先例 | {n} |
| DISC-RQ1 | {n} |
| DISC-RQ2 | {n} |
| DISC-RQ3 | {n} |
| COMP | {n} |
```

---

## 步骤 2：动态拆分Agent任务（主Agent执行）

基于步骤1的文献量统计，使用以下算法分配subAgent任务：

**THRESHOLD = AGENT_ITEM_LIMIT = 50**

```
for each tag:
    if N_tag == 0:
        跳过
    elif N_tag ≤ 30:
        标记为"可合并"
    elif N_tag ≤ THRESHOLD:
        分配1个独立agent，处理该标签全部文献
    elif N_tag ≤ 2 × THRESHOLD:
        按方向来源对半拆分为2个agent
    else:
        按方向来源拆分为3个agent

将所有"可合并"标签按 N_tag 降序依次贪心装入，使每个agent处理总量 ≤ THRESHOLD
```

**展示拆分计划**（在对话中展示，等待用户确认）：

```
Agent任务分配：
| Agent# | 处理标签 | 文献数 | 备注 |
|:------:|:---------|:------:|:-----|
| 1 | LR (D1+D2+D3) | 48 | 拆分1/3 |
| 2 | LR (D4+D5) | 45 | 拆分2/3 |
| 3 | LR (D6) | 42 | 拆分3/3 |
| 4 | METHOD | 45 | 独立 |
| 5 | GAP | 40 | 独立 |
| 6 | DISC | 35 | 独立 |
| 7 | BG+COMP | 22 | 合并 |
共 7 个并行subAgent
```

---

## 步骤 3：并行启动SubAgent

**所有agent在同一条消息中同时并行启动**。

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
1. **生成citation key**：AuthorYear格式（如 Parker2018），同作者同年加a/b
2. **排序**：每个标签组内，按分级（核心→重要→备选）+ 年份降序
3. **生成引用场景**：基于入选理由 + 研究上下文，改写为写作视角
   - 入选理由 = "为什么留下这篇"（筛选视角）
   - 引用场景 = "这篇可以支撑什么论点"（写作视角）

## 输出格式
对你负责的每个标签，输出Markdown表格，保存为 `structure/2_literature/_tmp_pool_agent{N}.md`
```

---

## 步骤 4：合并组装 `citation_pool.md`（主Agent执行）

所有subAgent完成后：

### 4.1 读取临时文件
- 读取所有 `structure/2_literature/_tmp_pool_agent*.md`

### 4.2 合并同标签内容
- 同一标签被拆分到多个agent时（如LR拆为3个agent），将表格合并
- 合并后重新按分级+年份排序
- 检查去重（防御性检查）

### 4.3 组装最终文件
输出 `structure/2_literature/citation_pool.md`，格式如下（见下方模板）。

### 4.4 清理临时文件
- 删除所有 `structure/2_literature/_tmp_pool_agent*.md`

---

### citation_pool.md 输出格式模板

```markdown
# Citation Pool — {项目编号}

> **生成日期**: {YYYY-MM-DD}
> **文献总量**: 去重后{N}篇
> **来源**: direction reports (×{M}个方向)

---

## BG — Background（{n}篇）
> **引用偏好**: 优先近5年高质量期刊，体现掌握最新动态
> **服务章节**: Introduction [主]

| 分级 | 作者 | 年份 | citation key | 引用场景 | 期刊 |
|:----:|:-----|:----:|:------------|:---------|:-----|
| 核心 | ... | ... | ... | ... | ... |
| 重要 | ... | ... | ... | ... | ... |
| 备选 | ... | ... | ... | ... | ... |

---

## LR — Literature Review（{n}篇）
> **引用偏好**: 优先近5年核心文献，展示理论前沿
> **服务章节**: Literature Review [主], Introduction [次]

| 分级 | 作者 | 年份 | citation key | 引用场景 | 期刊 |
|:----:|:-----|:----:|:------------|:---------|:-----|
| ... |

---

## GAP — Gap Support（{n}篇）
> **服务章节**: Introduction [主], Literature Review [主]

### GAP-RQ1（{n}篇）：{RQ1简述}
| 分级 | 作者 | 年份 | citation key | 引用场景 | 期刊 |
|:----:|:-----|:----:|:------------|:---------|:-----|
| ... |

### GAP-RQ2（{n}篇）：{RQ2简述}
| 分级 | 作者 | 年份 | citation key | 引用场景 | 期刊 |
|:----:|:-----|:----:|:------------|:---------|:-----|
| ... |

### GAP-RQ3（{n}篇）：{RQ3简述}
| 分级 | 作者 | 年份 | citation key | 引用场景 | 期刊 |
|:----:|:-----|:----:|:------------|:---------|:-----|
| ... |

---

## METHOD — Methodology（{n}篇）
> **服务章节**: Methodology [主], Literature Review [次]

### METHOD-基础：方法论理论来源（{n}篇）
> 经典奠基文献优先，年份可较早

| 分级 | 作者 | 年份 | citation key | 引用场景 | 期刊 |
|:----:|:-----|:----:|:------------|:---------|:-----|
| ... |

### METHOD-先例：方法论应用先例（{n}篇）
> 展示方法在其他领域的应用，优先近5年

| 分级 | 作者 | 年份 | citation key | 引用场景 | 期刊 |
|:----:|:-----|:----:|:------------|:---------|:-----|
| ... |

---

## DISC — Discussion（{n}篇）
> **服务章节**: Discussion [主]

### DISC-RQ1（{n}篇）：{RQ1简述}
| 分级 | 作者 | 年份 | citation key | 引用场景 | 期刊 |
|:----:|:-----|:----:|:------------|:---------|:-----|
| ... |

### DISC-RQ2（{n}篇）：{RQ2简述}
| 分级 | 作者 | 年份 | citation key | 引用场景 | 期刊 |
|:----:|:-----|:----:|:------------|:---------|:-----|
| ... |

### DISC-RQ3（{n}篇）：{RQ3简述}
| 分级 | 作者 | 年份 | citation key | 引用场景 | 期刊 |
|:----:|:-----|:----:|:------------|:---------|:-----|
| ... |

---

## COMP — Competitor（{n}篇）
> **引用偏好**: 必须详细分析差异化空间
> **服务章节**: 跨章节（决定能不能做）

| 分级 | 作者 | 年份 | citation key | 引用场景 | 与本研究的关键差异 | 期刊 |
|:----:|:-----|:----:|:------------|:---------|:------------------|:-----|
| ... |
```

---

## 步骤 5：更新各章节md的引用池

自动读取各章节md，将引用池区块更新为指向 `citation_pool.md`：

**introduction.md**：
```
## 引用池
- **[主] BG标签文献** → 见 `2_literature/citation_pool.md` §BG
- **[主] GAP-RQ1/RQ2/RQ3** → 见 `2_literature/citation_pool.md` §GAP
- **[次] LR标签文献** → 见 `2_literature/citation_pool.md` §LR
```

**literature.md**：
```
## 引用池
- **[主] LR标签文献** → 见 `2_literature/citation_pool.md` §LR
- **[主] GAP-RQ1/RQ2/RQ3** → 见 `2_literature/citation_pool.md` §GAP
- **[次] METHOD-基础 / METHOD-先例** → 见 `2_literature/citation_pool.md` §METHOD
- **[次] DISC-RQ1/RQ2/RQ3** → 见 `2_literature/citation_pool.md` §DISC
```

**methodology.md**：
```
## 引用池
- **[主] METHOD-基础** → 见 `2_literature/citation_pool.md` §METHOD-基础
- **[主] METHOD-先例** → 见 `2_literature/citation_pool.md` §METHOD-先例
```

**discussion.md**：
```
## 引用池
- **[主] DISC-RQ1** → 见 `2_literature/citation_pool.md` §DISC-RQ1
- **[主] DISC-RQ2** → 见 `2_literature/citation_pool.md` §DISC-RQ2
- **[主] DISC-RQ3** → 见 `2_literature/citation_pool.md` §DISC-RQ3
- **[次] LR标签文献** → 见 `2_literature/citation_pool.md` §LR
```

---

## 步骤 6：对话汇报

在对话中展示：
1. 各标签文献数量分布表
2. 核心/重要/备选的总体比例
3. citation_pool.md 的文件路径
4. 提醒用户审阅，确认引用场景是否准确

---

## 边界条件处理

| 情况 | 处理 |
|:-----|:-----|
| direction reports 不存在 | 停止，提示先运行 `/lit-review` |
| 某标签下文献数为0 | 在对话中警告，建议补检 |
| citation_pool.md 已存在 | 询问覆盖/跳过 |
| 某章节md不存在 | 跳过该章节的引用池更新 |
| direction report 格式异常 | 报告错误，继续处理其他 reports |
