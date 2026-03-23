---
description: "根据研究idea规划文献检索方向，生成WoS检索式与配额分配（Literature Search Planning）"
---

# Lit-Plan — 文献检索规划

根据论文的研究纲领（idea.md），规划5-7个文献检索方向，每个方向附带Web of Science检索式、章节功能标签、优先级和配额分配。

**输入** `$ARGUMENTS`：可选总预算参数（纯数字，默认360）。示例：`/lit-plan 360`、`/lit-plan 300`、`/lit-plan`。

---

## 全局约束

### 输出语言
**所有描述性文本必须使用中文**，包括但不限于：方向名称、层面描述、论文角色说明、检索式设计说明、配额分配理由。WoS检索式本身使用英文（数据库要求）。

---

## 步骤 0：解析输入与前置检查

### 0.1 解析预算
- 从 `$ARGUMENTS` 提取数字 → `{TOTAL_BUDGET}`（默认360）
- 有效范围：100-500。超出范围 → 提示用户确认

### 0.2 获取项目上下文
- 读取 `CLAUDE.md` → 提取项目编号、英文标题、一句话概括、方法、目标期刊
- 读取 `structure/0_global/idea.md` → 提取可用信息，并判断成熟度：
  - **成熟（有明确Gap/RQ）**：提取 §2 Gap/RQ、§3 方法论、§4 贡献意图 → 检索方向围绕Gap/方法论精准设计
  - **初步（有研究主题和大致方向，但Gap/RQ不明确）**：提取研究背景、方法论倾向、关键概念 → 检索方向偏探索性，覆盖面更广
- 如果 `idea.md` 不存在或内容 < 100 字 → 停止，提示用户至少提供研究主题和大致方向
- 将成熟度标记为 `{IDEA_MATURITY}` = `mature` / `exploratory`，传递给后续 `/lit-review` 使用

### 0.3 检查已有检索方案
- 检查 `structure/2_literature/literature_search_plan.md` 是否已存在
- 已存在 → 提示用户：已有检索方案，是覆盖还是增量更新？等待确认

---

## 步骤 1：设计检索方向

根据 idea.md 的内容，设计 5-7 个检索方向。

### 功能标签体系

每个方向必须标注它服务哪些功能标签（可多个）。标签与章节的固定映射：

| 标签 | 全称 | 含义 | 对应章节 |
|:-----|:-----|:-----|:---------|
| `BG` | Background | 研究背景——近3年发表且与研究主题相关（沾边即可） | Introduction §1 |
| `LR` | Literature Review | 文献综述主体——落在LR讨论主题范围内即可 | Literature Review §2 |
| `GAP-RQx` | Gap Support | 研究同一大主题但视角/维度/方法与本文RQx不同的文献。**按实际RQ数量动态生成** | Introduction §1 / Literature Review §2 |
| `METHOD-基础` | Methodology | 方法论理论来源——定义/提出本文所用方法的文献 | Methodology §3 |
| `METHOD-先例` | Methodology | 方法论应用先例——在其他领域应用过本文方法的文献 | Methodology §3 |
| `DISC-RQx` | Discussion | 与本文RQx相关的文献（宽泛纳入）。**按实际RQ数量动态生成** | Discussion §5/§6 |
| `COMP` | Competitor | 竞品论文——做了高度相似的研究 | 跨章节（决定能不能做） |

### 每个方向必须包含
1. **方向编号与名称**
2. **层面**：核心理论/理论基础/方法论/行业背景 等
3. **论文角色**：该方向文献在论文中扮演什么角色（1-2句话）
4. **功能标签**：通过以下5问清单逐一判断（可多个标签）
5. **优先级**：P1（必检）/ P2（重要）/ P3（补充）
6. **WoS检索式**：一条可直接复制粘贴的Web of Science检索式
7. **检索式设计说明**：为什么用TI/TS、为什么选这些关键词、预估文献量

### 功能标签分配规则（5问清单）

对每个方向，逐一回答以下问题来确定标签：

| # | 问题 | 如果"是" → 标签 | 说明 |
|:-:|:-----|:---------------|:-----|
| 1 | 这个方向的文献会在Literature Review中被专门讨论（占一个subsection或一段narrative）？ | **LR** | 不是默认标——纯工具型方法方向（如SEM、回归）不标LR |
| 2 | 这个方向是关于行业/应用领域的？ | **BG** | 需同时满足：方向内有近3年文献 |
| 3 | 这个方向是关于方法本身的理论来源？ | **METHOD-基础** | 如"Biform Game理论"、"Shapley值定义" |
| 4 | 这个方向是关于方法在其他领域的应用？ | **METHOD-先例** | 如"Biform Game在供应链中的应用" |
| 5 | 这个方向的检索主题跟RQx有重叠？（逐个RQ判断） | **GAP-RQx + DISC-RQx** | 重叠则同时标GAP和DISC |

> **LR与METHOD的区分**：如果方法本身是一个理论框架（如博弈论、信号博弈），需要在LR中梳理其理论脉络 → 标LR+METHOD。如果方法只是计算工具（如SEM、DEA）→ 只标METHOD，不标LR。
> **COMP**：不分配给特定方向，所有方向自然扫描。

### 检索式设计原则
- **一个方向仅一条检索式**，复制粘贴即用
- 优先用 `TS`（主题），仅当核心概念必定出现在标题时才用 `TI`（标题）
- 使用 `OR` 覆盖同义词/拼写变体，使用 `AND` 交叉限定
- 预估检索量：50-500篇为理想范围。< 50 → 放宽条件；> 500 → 收紧条件
- 合并逻辑相近的子方向（属于同一学术社群的文献）以减少方向总数

### 建筑工程领域术语规范（Construction/AEC domain）
当研究涉及建筑工程管理领域时，检索式中**禁止**单独使用 `"construction"` 或 `"building*"`，因为这两个词歧义极大（如 "construction of a model"、"building a framework"），会捞到大量无关文献，增加不必要的筛选工作。

**必须使用以下限定短语替代：**

| 禁用 | 替代为（OR 连接） |
|:-----|:-----------------|
| `"construction"` | `"construction industry"` OR `"construction project*"` OR `"construction sector"` OR `"construction firm*"` OR `"construction company"` |
| `"building*"` | `"built environment"` OR `"building sector"` OR `"building industry"` |

**补充推荐词（视情况加入）：**
- `"AEC"`（Architecture, Engineering and Construction）
- `"civil engineering"`
- `"infrastructure project*"`

**例外**：当 "construction" 与其他限定词组成固定短语时（如 `"modular construction"`、`"off-site construction"`、`"prefabricated construction"`），语义已经明确，无需替换。

### 方向覆盖性检查
设计完成后自检：以下每个标签至少被1个方向覆盖

| 标签 | 至少覆盖 | 理想覆盖 | 说明 |
|:-----|:---------|:---------|:-----|
| `BG` | 1个方向 | 1-2个 | |
| `LR` | 2个方向 | 3-5个 | 大部分方向服务LR，但纯工具型方法方向可能不服务 |
| `GAP-RQ1/2/3` | 1个方向 | 2-3个 | |
| `METHOD-基础/先例` | 1个方向 | 1-2个 | 如方法是理论框架则同时服务LR |
| `DISC-RQ1/2/3` | 1个方向 | 1-2个 | |
| `COMP` | 不单设方向 | 各方向自然扫描 | |

如有标签未被覆盖 → 增加方向或调整现有方向的功能标签。

---

## 步骤 2：分配配额（Python 脚本）

**本步骤由 Python 脚本自动完成，不使用 LLM 心算**，以避免算术错误。

### 2.1 准备输入 JSON

主 Agent 将步骤 1 设计的方向数据写入临时 JSON 文件 `structure/2_literature/_directions.json`：

```json
{
  "directions": [
    {
      "id": 1,
      "name": "方向名称",
      "tags": ["BG", "LR", "GAP-RQ1", "DISC-RQ1"],
      "priority": "P1"
    }
  ]
}
```

### 2.2 调用配额计算脚本

```bash
python3 ~/.claude/skills/lit-plan/quota_calc.py \
  --directions structure/2_literature/_directions.json \
  --budget {TOTAL_BUDGET}
```

**脚本职责**（`quota_calc.py`）：
1. 按标签 Pool 目标（BG=50, LR=150, GAP=75, METHOD=60, DISC=65）计算 tag_share
2. 对每个方向求 raw_demand = Σ tag_share
3. 等比缩放到总预算，四舍五入
4. 保底每方向 ≥ 20 篇，重新缩放其余方向
5. 计算内部分层（核心 ≤25%, 重要 ≤40%, 备选 ≤35%）
6. 标签覆盖检查
7. stdout 输出完整计算表 + 校验结果
8. 写入 `_quota_result.json`

### 2.3 主 Agent 校验脚本输出

脚本 stdout 末尾格式：
```
=== VERIFY: PASS|FAIL ===
```

校验规则：
- VERIFY 必须为 PASS。FAIL 时停止，展示具体错误给用户
- 将脚本输出的配额计算表展示给用户确认
- 后续步骤从 `_quota_result.json` 读取配额数据填入输出文件

### 2.4 清理临时文件
配额写入 `literature_search_plan.md` 后，删除 `_directions.json` 和 `_quota_result.json`

---

## 步骤 3：列出经典文献

列出**不可能通过WoS检索式覆盖、但必须手动补入**的经典文献：
- 专著（WoS不收录书籍）
- 行业报告（McKinsey、Gartner等）
- 工作论文/预印本
- 该领域的奠基性文献（可能年代久远不在检索范围内）

格式：

| 文献 | 论文中的角色 | 功能标签 |
|:-----|:------------|:---------|
| Author (Year). *Title* | 角色说明 | BG/LR/... |

---

## 步骤 4：生成输出

### 输出文件：`structure/2_literature/literature_search_plan.md`

模板结构：

```markdown
# {项目编号} 文献检索方案

> **日期**: {YYYY-MM-DD}
> **检索平台**: Web of Science (WOS) Core Collection
> **总预算**: {TOTAL_BUDGET}篇
> **目标期刊**: {从CLAUDE.md提取}
> **Idea成熟度**: {IDEA_MATURITY}（mature / exploratory）
> **规则**: 每个方向**仅一条检索式**，复制粘贴即用

---

## 方向1：{方向名称}
> **层面**: {核心理论/理论基础/方法论/行业背景}
> **论文角色**: {该方向文献的角色说明}
> **功能标签**: {通过5问清单判断，如 LR + GAP-RQ1 + DISC-RQ1}
> **优先级**: **{P1/P2/P3}**
> **配额**: {N}篇（核心≤{x} / 重要≤{y} / 备选≤{z}）

\```
{WoS检索式}
\```
> {检索式设计说明}

---

{重复方向2-N...}

---

## 检索汇总

| # | 方向 | 功能标签 | 优先级 | 配额 |
|:--|:-----|:---------|:------:|:----:|
| 1 | {方向名} | {标签} | P1 | {N}篇 |
| ... | ... | ... | ... | ... |
| | **合计** | | | **{TOTAL_BUDGET}篇** |

**建议检索顺序**: {按优先级和依赖关系排序}

---

## 标签覆盖检查

| 标签 | 覆盖方向 | 状态 |
|:-----|:---------|:----:|
| BG | 方向X, 方向Y | ✅ |
| LR | 方向X, 方向Z | ✅ |
| GAP-RQ1/2/3 | 方向X, 方向Y | ✅ |
| METHOD-基础/先例 | 方向W | ✅ |
| DISC-RQ1/2/3 | 方向Z | ✅ |
| COMP | 各方向自然扫描 | ✅ |

---

## 需手动补入的经典文献

| 文献 | 论文中的角色 | 功能标签 |
|:-----|:------------|:---------|
| ... | ... | ... |
```

### 对话输出
生成文件后，在对话中简要展示：
1. 方向汇总表
2. 配额分配
3. 标签覆盖检查结果
4. 建议的检索顺序
5. 提醒用户：去WoS检索后将RIS文件放入 `structure/2_literature/`，然后调用 `/lit-review`

---

## 边界条件处理

| 情况 | 处理 |
|:-----|:-----|
| idea.md 不存在或 < 100 字 | 停止，提示至少提供研究主题和大致方向 |
| 方向数 < 5 | 警告覆盖可能不足，询问是否补充 |
| 方向数 > 7 | 建议合并相近方向 |
| 某标签未被覆盖 | 强制提示，建议增加方向 |
| 已存在 literature_search_plan.md | 询问覆盖/增量 |
