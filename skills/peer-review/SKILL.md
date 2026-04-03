---
description: "作为期刊审稿人，阅读待审稿件PDF并按用户审稿风格自动生成审稿意见写入Word文档（Peer Review Generator）"
---

# Peer Review — 审稿意见生成器

阅读当前工作目录中的待审稿件 PDF，识别期刊与研究主题，按用户一贯的审稿风格自动生成 12–15 条审稿意见（Major + Minor），写入同目录的 Word 文档。

**核心原则**：生成的意见必须严格遵循用户历史审稿风格，言之有物、具体到段落/行号，不说空话。

## 输入说明

`$ARGUMENTS` 可选。如提供，视为附加指令（如 `重点关注方法论` 或 `语气温和一些`）。

---

## Step 0: 环境检测

### 0.1 定位文件

在当前工作目录中查找：

1. **待审稿件 PDF**：Glob `*.pdf`。找到唯一 PDF → 确认；找到多个 → 列出让用户选择；找不到 → 停止。
2. **审稿意见 Word 文档**：Glob `*.docx`。通常目录中不会有现成的 Word 文件，后续步骤会自动新建。如果已有 `Zylen comment-*.docx` → 询问用户是覆盖还是跳过。

### 0.2 读取 PDF

使用 Read 工具读取 PDF 稿件。从稿件中提取以下信息：

- **目标期刊**：从 header/footer、首页元数据、投稿编号格式中识别（如 COENG = JCEM, PMJ = PMJ, MEENG = JME, JPMA = IJPM 等）
- **稿件编号**：如 COENG-19268、PMJ-26-0131
- **论文标题**
- **研究主题与方法**：简要归纳论文做了什么、用了什么方法
- **论文结构**：识别各章节标题及大致位置（页码）

向用户确认：
```
📋 稿件信息确认：
- 期刊: {journal_name}
- 稿件编号: {manuscript_id}
- 标题: {title}
- 方法: {methodology_summary}

是否正确？如需调整请告知，否则我开始生成审稿意见。
```

---

## Step 1: 深度阅读与问题识别

按论文结构顺序逐部分精读，从以下维度系统性识别问题：

### 1.1 Introduction 审查要点
- **实际问题驱动**：引言是否从实际问题（practical problem）出发？还是直接从理论/文献切入？（后者是常见缺陷）
- **研究情境嵌入**：引言是否从一开始就嵌入了研究的具体情境（如 construction project、megaproject 等）？还是情境出现过晚/缺失？
- **研究动机逻辑链**：从背景 → 问题 → 研究缺口 → 研究目的/问题，逻辑是否连贯？
- **概念引入时机**：关键概念（如理论框架、方法论）是否引入过于突兀？是否有充分的 justification？
- **标题与内容一致性**：标题强调的 DV/核心概念，在引言中是否得到充分阐述？

### 1.2 Literature Review 审查要点
- **覆盖面与时效性**：文献是否充分、是否包含近 3–5 年的关键文献？是否遗漏了该领域权威期刊的重要成果？
- **结构与逻辑**：是简单罗列（enumeration）还是有逻辑组织（综合、对比、批判）？
- **与研究缺口的衔接**：文献综述是否自然导向研究缺口的识别？
- **关键构念的完整性**：研究框架中的所有关键变量（IV、DV、Mediator、Moderator）是否都有充分的文献支撑？

### 1.3 Theoretical Framework & Hypothesis Development 审查要点
- **理论基础的充分性**：是否有 overarching theory 支撑整体框架？还是碎片化的理论拼凑？
- **假设推导的逻辑性**：每个假设是否有充分的理论推导和文献支持？是否存在逻辑跳跃？
- **构念一致性**：假设中使用的构念与文献综述、数据收集中的操作化是否一致？
- **研究情境的嵌入**：假设推导是否扎根于具体研究情境？还是泛泛的一般性论述？

### 1.4 Methodology 审查要点
- **抽样方法**：样本代表性、选择偏差、样本量充分性
- **测量工具**：量表来源与信效度、操作化与构念是否匹配
- **数据分析方法**：方法选择的合理性、步骤的完整性（如是否做了 EFA/CFA、共同方法偏差检验等）
- **控制变量**：选择是否合理、是否有冗余或遗漏
- **定性研究**：编码过程透明度、访谈协议披露、分析跳跃

### 1.5 Results 审查要点
- **结果呈现的完整性**：所有假设是否都有明确的检验结果？
- **非显著结果的处理**：不显著的假设是否有充分解释？
- **图表的信息完整性**：图表是否清晰标注了关系方向、显著性？是否有充分的文字解释？

### 1.6 Discussion & Conclusion 审查要点
- **与既有文献的对话**：讨论是否将发现与已有研究进行比较分析？
- **理论贡献的明确性**：是否清晰阐述了理论贡献？（不能只说 practical implications 而忽略 theoretical contributions，反之亦然）
- **引言-讨论一致性**：讨论中强调的内容是否与引言中建立的动机和预期相呼应？
- **局限性的诚实讨论**：是否充分讨论了研究局限？

### 1.7 Minor / Presentation Issues
- **术语一致性**：同一概念是否全文统一？
- **缩写使用**：是否首次使用时给出全称？
- **语法与表达**：是否有明显的语法错误或表述不清？
- **格式规范**：表格字体/格式是否统一？引用格式是否规范？
- **引文规范**：关键论断是否有引用支撑？数据来源是否标注？

---

## Step 2: 生成审稿意见

### 2.1 意见数量与分类

生成 **12–15 条**审稿意见，按以下比例分配：
- **Major comments**：8–10 条（涉及逻辑、理论、方法论、贡献等根本性问题）。每条 **40–70 words**，精准点出问题所在（引用具体页码/表格/图号）、为什么有问题、改进方向。可以适当解释，但必须简洁。禁止泛泛而谈（如"introduction needs improvement"），必须说清楚**哪里**有问题。
- **Minor comments**：4–5 条（术语、格式、表述、引文等细节问题）。每条 **2–3 句话**即可，点到为止。

### 2.2 意见排列顺序

严格按照论文正文发展顺序排列：
1. Introduction 相关
2. Literature Review 相关
3. Theoretical Framework / Hypothesis 相关
4. Methodology 相关
5. Results 相关
6. Discussion / Conclusion 相关
7. 全文性问题（格式、术语、语言等）

### 2.3 写作风格规范（基于用户历史审稿风格）

#### 开头段（Overview Paragraph）

必须包含一个概括性开头段，结构如下：

```
Comments to Authors:

This manuscript presents an analysis of [研究主题简述], employing [方法简述].
[1-2句肯定论文选题的价值/相关性]. However, [several areas / a lot of areas]
require [attention / substantial attention] to strengthen the manuscript's
[具体需要加强的方面, 如 theoretical foundation, methodological rigor,
practical contributions].
```

**关键要素**：
- 先客观概述论文做了什么
- 再简短肯定选题的价值（1-2 句）
- 最后用 "However" 转折，指出需要改进的方向（概括层面）

#### 各条意见的写作要求

1. **具体性**：每条意见必须指向论文的具体位置（段落、行号、表格编号、图号）。不说"某些地方需要改进"这样的空话。
2. **建设性**：指出问题的同时给出改进方向或具体建议。
3. **学理性**：对于理论/方法论问题，应展现审稿人的学术判断力（如指出文献遗漏、构念混淆、方法选择不当等）。
4. **情境敏感**：如果论文投稿到建设管理/项目管理期刊，注意检查论文是否充分嵌入了该领域的具体情境。
5. **语气**：Professional, constructive but firm。不过度客气，也不攻击性批评。直接指出问题，给出理由。

#### 结尾

**必须**以以下任一方式结尾（统一风格）：

- `After all, hope the authors all the best!`
- `I wish the authors all the best in refining their work.`
- `After all, I hope the authors all the best.`

#### 语言

- 审稿意见**一律用英文**撰写
- 与用户的交互对话用中文

### 2.4 特殊情况处理

- **所有假设都显著**：质疑是否存在研究设计偏差或分析过程问题
- **引言缺乏 practical problem**：这是用户最常指出的问题之一，必须重点关注
- **文献综述只是 enumeration**：明确指出需要逻辑组织和批判性分析
- **Discussion 与 Introduction 脱节**：检查引言承诺的理论贡献是否在讨论中兑现
- **构念操作化与理论描述不一致**：这是严重问题，必须指出

---

## Step 3: 写入 Word 文档

### 3.1 文档格式

使用 `python-docx` 写入 Word 文档：

```python
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

doc = Document()

# 设置默认字体
style = doc.styles['Normal']
font = style.font
font.name = 'Times New Roman'
font.size = Pt(12)

# 标题
doc.add_paragraph('Comments to Authors:', style='Normal')
# 设为加粗
# ...

# 概括段
doc.add_paragraph(overview_paragraph)

# 各条意见（编号列表）
for i, comment in enumerate(comments, 1):
    doc.add_paragraph(f'{i}. {comment}')

# 结尾
doc.add_paragraph('')
doc.add_paragraph('After all, hope the authors all the best!')

doc.save(output_path)
```

### 3.2 文件命名

默认新建文件，命名规则：`Zylen comment-{稿件编号}.docx`

稿件编号从 PDF 中提取（如 `PMJ-26-0131`、`COENG-19268`）。

示例：`Zylen comment-PMJ-26-0131.docx`

### 3.3 输出确认

写入完成后，向用户展示：

```
✅ 审稿意见已生成并写入：{文件路径}

📊 意见概览：
- Major comments: {N} 条
- Minor comments: {M} 条
- 总计: {N+M} 条

📝 意见摘要：
1. [第1条简述]
2. [第2条简述]
...

如需调整某条意见的语气/内容/增删，请直接告诉我。
```

### 3.4 审稿决定建议（Decision Recommendation）

Word 文档生成完毕后，在对话框中（**不写入 Word**）向用户给出审稿决定建议，格式如下：

```
🔖 Decision 建议：{Accept / Minor Revision / Major Revision / Reject}
理由：{2–3 句话概括判断依据}
```

**判断标准**：
- **Accept**：选题好、方法严谨、贡献清晰、仅有极少量 minor 问题
- **Minor Revision**：核心框架和方法论成立，但有若干需要修补的问题（文献补充、表述优化、小范围方法补充等），不涉及重新设计研究
- **Major Revision**：存在较多根本性问题（理论框架薄弱、方法论缺陷、贡献不清等），但研究选题有价值、数据可用，经大幅修改后有潜力
- **Reject**：研究设计存在不可修复的致命缺陷，或选题/贡献与期刊不匹配，修改无法挽救

决定建议仅供用户参考，用户可自行调整后填入期刊系统。

---

## Step 4: 交互修改（可选）

用户可能要求：
- **调整某条意见**：修改措辞、补充论据、调整语气
- **增加意见**：针对某个新发现的问题追加
- **删除意见**：去掉某条不够有力的意见
- **调整整体语气**：更严厉 / 更温和
- **生成 Confidential Comments to Editor**：简短评价稿件质量、建议决定（accept / minor revision / major revision / reject）

每次修改后重新写入 Word 文档。

---

## 附录：用户审稿风格特征总结

以下是从用户 20+ 份历史审稿意见中提炼的风格特征，生成审稿意见时**必须严格遵循**：

### A. 结构模式

| 元素 | 风格特征 |
|------|----------|
| 开头段 | 概述论文 → 肯定选题 → "However" 转折 → 指出改进方向 |
| 意见编号 | 阿拉伯数字编号（1, 2, 3...），子问题用字母（a, b, c）或按章节分组 `(1) Introduction` `(2) Methodology` |
| 意见顺序 | 严格按正文发展顺序 |
| 结尾 | "After all, hope the authors all the best!" |
| 意见数量 | 12–15 条 |

### B. 常见开头段模板

**模板 1（定量研究）**：
> This manuscript presents an analysis of [主题], employing [方法] through [具体技术]. The study addresses [价值/相关性]. However, [several/a lot of] areas require [attention/substantial attention] to strengthen the manuscript's [具体方面].

**模板 2（定性研究）**：
> This manuscript presents [an exploration/an investigation] of [主题]. Through [方法], the research [简述发现]. However, several areas require substantial attention to strengthen the manuscript's [logic, methodological rigor and contributions to {期刊名}].

**模板 3（混合/特殊方法）**：
> This manuscript offers [a valuable/an interesting] [exploration/investigation] of [主题] by [方法]. The study [肯定句]. However, there are several areas where the manuscript could be strengthened to enhance its [impact and relevance / rigor and practical relevance].

### C. 高频批评模式（按出现频率排序）

1. **引言缺乏 practical problem 驱动**（出现率 ~80%）
   - "The introduction contains excessive background information without efficiently transitioning to the specific practical problem"
   - "Beginning directly with theoretical frameworks rather than a clearly articulated practical problem diminishes the paper's relevance"

2. **研究情境嵌入不足**（出现率 ~70%，尤其对 JCEM/JME 投稿）
   - "The first three paragraphs contain no terminology related to construction or projects, despite this being the primary research context"
   - "The construction project context is inappropriately introduced near the end of the introduction as merely a research setting"

3. **文献综述缺乏批判性/逻辑性**（出现率 ~60%）
   - "The literature review section fails to adequately address [DV/关键构念]"
   - "The current version of the literature review is only a simple enumeration of previous studies"
   - "The authors present the literature in a descriptive, sequential manner without explicating how these studies relate to [核心主题]"

4. **理论框架碎片化**（出现率 ~50%）
   - "The manuscript lacks an overarching theoretical framework to support the hypothesis development process"
   - "Multiple theories invoked post-hoc without a coherent ex-ante framework"

5. **讨论与引言脱节**（出现率 ~50%）
   - "The discussion section fails to address the theoretical implications emphasized in the introduction"
   - "The articulation of research contributions is not sufficiently prominent"

6. **抽样/方法论问题**（出现率 ~40%）
   - 质疑单一来源、单一项目、非概率抽样的合理性
   - 要求披露访谈协议、编码过程

7. **构念不一致**（出现率 ~30%）
   - 假设中的构念 vs 数据收集中的操作化不匹配
   - 术语在全文中不统一

### D. 语气标尺

| 问题严重程度 | 典型措辞 |
|------------|---------|
| 致命缺陷 | "This represents a significant/major deficiency" / "This is a critical deficiency" / "a concerning disconnect/misalignment" |
| 重要问题 | "requires stronger justification" / "should be substantially devoted to" / "is inadequate/insufficient" |
| 中等问题 | "could benefit from" / "would be beneficial" / "I suggest the authors" |
| 小问题 | "Please proofread" / "should be standardized" / "consider inserting" |

### E. 文献推荐习惯

- 用户偶尔会推荐与研究主题相关的文献（尤其是本研究组的成果）
- 推荐格式：完整 APA 引用 + DOI
- 常推荐的方向：greenwashing in construction、project governance、collaborative innovation、sustainability in AEC
- **注意**：只有在确实了解该领域文献的情况下才推荐，不确定则不推荐，避免编造引用
