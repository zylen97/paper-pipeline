# Revision Workflow — 参考规则

> 本文件供 `/rev-init` SKILL.md 引用。包含意见分类、优先级定义、聚类模式等参考规则。

---

## Comment 类型分类

| 类型 | 定义 | 判断依据 | 示例 |
|------|------|----------|------|
| **Modify** | 需修改 `manuscript.tex`（或 `supplemental-materials.tex`） | 审稿人明确要求"修改/补充/删除/重写"具体内容 | "The definition in Section 2 is unclear and should be rewritten." |
| **Explain** | 仅需在回复信中解释，无需改稿 | 审稿人提问"为什么/怎么解释"，当前文本本身无误 | "Why did you choose method X over method Y?" |
| **Supplement** | 新增内容：段落、表格、图片、参考文献、附录 | 审稿人要求"添加/补充/增加"之前没有的东西 | "Please add a sensitivity analysis for parameter α." |

> 一条意见可能同时涉及多种类型，标注**主要**类型即可。

---

## 优先级定义

| 级别 | 定义 | 典型例子 |
|------|------|----------|
| **Highest** | 全局影响——修改会传导到整个稿件 | 记号/符号审计、核心概念定义重写、全文术语统一 |
| **High** | 核心技术关切——需要大幅修改 | 方法论透明化、假设论证不足、模型验证缺失 |
| **Medium** | 展示改善——修改范围较小，提升可读性 | 图表可视化、文献补充、结果解释扩展 |
| **Low** | 微小修改——一两处即可完成 | 拼写/语法、格式微调、个别措辞建议 |

---

## 聚类主题类别

| 类别 | 覆盖范围 | 示例意见 |
|------|----------|----------|
| Conceptual Definitions | 关键术语、构念、变量定义 | "Define X more clearly" / "What exactly is Y?" |
| Notation Consistency | 符号、下标、方程格式 | "Notation in Eq. 3 vs Eq. 7 conflict" |
| Model Assumptions | 简化假设、边界条件、局限性 | "Why assume linear costs?" / "Is this realistic?" |
| Method Transparency | 推导步骤、参数选择、可复现性 | "How was α calibrated?" / "Show derivation" |
| Robustness/Sensitivity | 替代参数、边界情况、验证 | "What if β changes?" / "Sensitivity analysis needed" |
| Literature Coverage | 缺失引用、定位、对比 | "Compare with Smith (2020)" / "Cite Jones (2019)" |
| Structural Improvements | 章节顺序、行文流畅、篇幅 | "Move Section 4 before Section 3" |
| Figures/Tables | 可视化质量、标签、可读性 | "Figure 2 is hard to read" / "Add units to Table 3" |
| Practical Implications | 实践应用、管理启示 | "How would a practitioner use this?" |
| Generalizability | 适用范围、外部效度 | "Does this apply to other contexts?" |

---

## 聚类决策树

对每条意见 X：

```
X 是否与已有 Cluster 的某条意见指向同一原稿位置（同一 Section/方程/表格）？
├── 是 → X 很可能属于该 Cluster
└── 否 ↓
    X 是否与已有 Cluster 的某条意见要求同一类型的修改？
    ├── 是，且修改之间有依赖或冲突 → X 属于该 Cluster
    ├── 是，但修改完全独立 → 可能是新 Cluster
    └── 否 ↓
        X 与已有 Cluster 是否共享同一底层学术关切？
        ├── 是 → X 属于该 Cluster
        └── 否 → X 开启新 Cluster
```

### 聚类原则
1. **先通读再聚类**：必须读完所有审稿人意见后才开始分组
2. **按底层问题分组，不按表面措辞**：两条意见可能用不同的话说同一件事
3. **验证可行性**：能设计一套协调的修改同时满足 Cluster 内所有意见吗？不能则拆分
4. **允许独立**：纯拼写校对等可单独成 Cluster 或归入"杂项"
5. **矛盾意见**：两位审稿人要求互相矛盾时，放入同一 Cluster，标注"⚠️ 矛盾"

---

## 锚点选择规则

每个 Cluster 选一条意见作为**锚点**——回复最详细、最完整。

| 选择标准 | 说明 |
|---------|------|
| **最详细的** | 提供了最多具体要求的那条 |
| **最技术性的** | 指出了最底层问题的那条 |
| **覆盖面最广的** | 满足这条，其他意见自然被覆盖 |
| **平局 → 最严格的审稿人** | 满足最高标准 = 满足所有标准 |

---

## 执行顺序策略

1. **全局影响优先**：记号审计、关键定义先做
2. **尊重依赖链**：C5 依赖 C2+C4 → 先完成 C2、C4
3. **批处理相关 Cluster**：无依赖的相邻 Cluster 可合并处理
4. **Cluster 内锚点优先**：先处理锚点 Comment，再处理卫星
5. **穿插简单任务**：在重 Cluster 之间安排轻任务保持节奏

典型顺序：C(notation) → C(definitions) → C(methods) → C(results/discussion) → C(figures) → C(typos) → final audit

---

## 非标准审稿格式处理

| 情况 | 处理方式 |
|------|----------|
| 没有 Associate Editor | 删除 AE section |
| 审稿人编号不连续（如 #2, #3, #5） | 保留原始编号，不重编 |
| 审稿人未分 Major/Minor | 使用连续编号 RN-1, RN-2, ...；在分类工作区标注类型和优先级 |
| Q&A 区域含实质性反馈 | 提取为独立 Comment，标注来源 "(from Q&A)" |
| 审稿人怀疑 AI 使用 | Highest 优先级合规问题；用户必须确认回复策略；不可由 AI 自行起草 |
| 一条评论含多个独立问题 | 拆分为独立 Comments |

---

## 状态符号

| 符号 | 含义 |
|------|------|
| ⬜ | 未开始 |
| 🔶 | 进行中 / 等待用户操作 |
| ✅ | 已完成 |
| ✅📝 | 已完成，经用户审阅修正 |
| 🔄 | 交叉一致性修复已应用 |

---

## AI 使用披露处理流程

当审稿人质疑 AI 工具使用（如 "formulaic text"、"AI hallucination"）时：

1. **标记为 Highest 优先级合规问题**，独立成 Cluster 或归入最高优先级 Cluster
2. **用户亲自确认回复策略**（铁律：不可由 AI 自行起草）
3. **查找期刊 AI 政策**：在期刊官网搜索 AI/LLM policy，引用官方 URL
4. **正面回应**：无论是否使用了 AI，都必须正面回应，不回避
5. **稿件内标注**：如期刊要求，在 Acknowledgments 中披露 AI 工具的使用范围和用途

> 用户确认策略后，按正常 `/rev-respond` 流程执行。

---

## 预提交检查清单

所有 Cluster 完成后、提交前逐项核对：

### 完整性
- [ ] 所有回复已填：`grep -c "TO BE FILLED" response-letter.tex` 返回 0
- [ ] 无 `[TBD]` 残留：`grep -n "TBD" response-letter.tex`
- [ ] 无 `(ref)` 标记残留：`grep -n "(ref)" manuscript.tex`

### 编译
- [ ] `manuscript.tex` 编译无错误
- [ ] `response-letter.tex` 编译无错误
- [ ] `supplemental-materials.tex` 编译无错误（如有）
- [ ] Tracked-changes PDF 已生成并审阅：`bash tools/make-diff.sh`

### 准确性
- [ ] 每个 `\manuscriptquote{}` 与当前 `manuscript.tex` 文本一致
- [ ] 所有 `\lineref{}` 行号与当前稿件一致
- [ ] 图表编号在回复信中正确
- [ ] 参考文献完整（PDF 中无 "?" 标记）

### 写作风格（抽查 5 段回复）
- [ ] 无超过 25 词的句子
- [ ] 被动语态已改为主动
- [ ] 无堆叠修饰语：`grep -i "significantly\|comprehensively\|thoroughly\|extremely\|highly\|greatly" response-letter.tex`
- [ ] 无中式英语搭配：`grep -i "improve the level\|play.*role\|provide reference\|with the development\|more and more\|carry out" response-letter.tex`
- [ ] em dash 每页不超 2 处：`grep "---" response-letter.tex`

### 格式
- [ ] 期刊格式要求已满足（间距、大写规则、摘要长度等）
- [ ] 所有图片满足分辨率要求（≥300 dpi）
- [ ] Data Availability Statement 存在（如期刊要求）

### 归档与交付
- [ ] Git 已提交并 tag（如 `v1.1-revision`）
- [ ] 交付物：response-letter.pdf + manuscript.pdf + manuscript-track-changes.pdf + supplemental-materials.pdf（如有）
