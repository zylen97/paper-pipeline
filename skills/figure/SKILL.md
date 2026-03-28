---
description: "学术论文图表全流程：自动判断 TikZ/Python/R → 创建概念图或数据图 → 美化已有图 → Eagle 风格参考 → 跨图一致性检查（Figure）"
---

# Figure — 学术论文图表全流程

一个入口覆盖所有论文绘图需求：自动判断工具选择、创建新图、美化已有图、跨图一致性检查。整合 Eagle 素材库作为风格参考源。

**输入** `$ARGUMENTS`：格式灵活，示例：
- `/figure` — 交互式选择操作
- `/figure 画一个博弈结构图` — 自动判断 TikZ，进入创建流
- `/figure beautify fig3` — 美化已有的 fig3
- `/figure audit` — 跨图一致性检查
- `/figure eagle 博弈论` — 搜索 Eagle 图库

---

## Morandi 色板（全局标准，不可变更）

所有图表必须使用此色板，不允许使用 matplotlib/ggplot 默认色或其他色板。

| 名称 | 深色 | 浅色 | 用途 |
|:-----|:-----|:-----|:-----|
| Steel Blue | `#576fa0` | `#a7b9d7` | 主色系 |
| Gold | `#e3b87f` | `#fadcb4` | 辅助色/对比 |
| Rose | `#b57979` | `#dea3a2` | 强调/警示 |
| Gray | `#9f9f9f` | `#cfcece` | 背景/次要元素 |

**TikZ 定义**：
```latex
\definecolor{steelblue}{HTML}{576fa0}
\definecolor{steelbluelight}{HTML}{a7b9d7}
\definecolor{gold}{HTML}{e3b87f}
\definecolor{goldlight}{HTML}{fadcb4}
\definecolor{rose}{HTML}{b57979}
\definecolor{roselight}{HTML}{dea3a2}
\definecolor{morandigray}{HTML}{9f9f9f}
\definecolor{morandigraylight}{HTML}{cfcece}
```

**Python**：
```python
MORANDI = {
    "steel_blue": "#576fa0", "steel_blue_l": "#a7b9d7",
    "gold": "#e3b87f", "gold_l": "#fadcb4",
    "rose": "#b57979", "rose_l": "#dea3a2",
    "gray": "#9f9f9f", "gray_l": "#cfcece",
}
```

**R**：
```r
morandi <- c("#576fa0", "#e3b87f", "#b57979", "#9f9f9f",
             "#a7b9d7", "#fadcb4", "#dea3a2", "#cfcece")
```

---

## 步骤 0：上下文加载 + 路由判断

### 0.1 读取项目配置

- 读取 `CLAUDE.md` → 提取 `{PUBLISHER}`、`{TARGET_JOURNAL}`、`{METHOD_TYPE}`、`{PAPER_TITLE}`
- 扫描 `structure/figures_tables/figures/` 目录 → 列出已有图文件 → `{FIGURE_INVENTORY}`
- 读取主 tex 文件 → 找所有 `\includegraphics` 和 `\input{fig*}` → 了解图在论文中的位置

### 0.2 解析 `$ARGUMENTS`

从 `$ARGUMENTS` 中识别操作类型：

| 关键词/模式 | 路由 |
|:-----------|:-----|
| `beautify` / `美化` / `polish` + 图编号 | Route B（美化流） |
| `audit` / `检查` / `一致性` | Route D（审计） |
| `eagle` + 标签 | Eagle 搜索（独立功能） |
| 含"框架""流程""概念""结构""关系""博弈树""决策树""时序" | Route A（TikZ 创建） |
| 含"分布""回归""系数""热力图""网络图""散点""柱状""折线""数据" | Route C（Python/R 创建） |
| 空 / 无法判断 | 交互询问 |

**无法判断时** → AskUserQuestion：
```
你要做什么？
(1) 创建新图 — 概念图/框架图/流程图/博弈树（TikZ）
(2) 创建新图 — 数据图/统计图/网络图（Python/R）
(3) 美化已有的数据图
(4) 跨图一致性检查
(5) 搜索 Eagle 图库找参考
```

### 0.3 自动判断 TikZ vs Python/R（仅 create 场景）

**核心原则：有没有真实数据驱动？**

```
图的内容由数据决定？（坐标、大小、颜色由数值映射）
├─ 是 → Python/R（Route C）
│   示例：度分布、回归系数图、热力图、网络力导向图、弦图、散点图
└─ 否（每个元素的位置由作者手动设计）→ TikZ（Route A）
    示例：研究框架图、理论模型图、博弈时序图、流程图、概念关系图
```

判断结果展示给用户确认：
```
🔍 判断结果：这张图适合用 {TikZ / Python / R}
理由：{一句话}

确认？或指定其他工具。
```

### 0.4 确定图编号

- 扫描 `structure/figures_tables/figures/` 中已有的 `fig{N}_*` 文件
- 下一个可用编号 = max(N) + 1
- 用户指定的编号优先
- 文件命名规范：`fig{N}_{description}.{tex|py|R}`（description 为 snake_case 英文，≤30 字符）

---

## 步骤 1：Eagle 参考搜索（Routes A/B/C 共享）

所有创建和美化路由都可以使用 Eagle 参考。也可通过 `/figure eagle {标签}` 独立运行。

### 1.1 询问参考来源

AskUserQuestion：
```
需要参考图吗？
(1) 从 Eagle 图库搜索（输入标签，如"博弈论"）
(2) 我直接提供参考图（粘贴路径或图片）
(3) 不需要参考，直接开始
```

用户选 (3) → 跳过此步骤，进入路由执行。

### 1.2 Eagle 标签搜索

```bash
python3 ~/.claude/skills/shared/eagle_search.py search --tags "{用户输入的标签}"
```

VERIFY: PASS → 继续。FAIL → 展示可用标签列表，让用户换标签重试或跳过。

### 1.3 展示搜索结果

```
🔍 Eagle 搜索结果（标签: "{tags}"）— 共 {N} 张

[1] {name}
    标签: {tags}
    来源: {annotation}
    尺寸: {width}×{height}

[2] ...

选择参考图（输入编号，可多选如 "1,3"），或 "skip" 跳过
```

### 1.4 读取并分析参考图

对用户选中的每张参考图：
1. 用 Read 工具查看图片（多模态视觉分析）
2. 从 Eagle metadata 提取 `palettes`（自动色板）
3. 记录视觉分析结果：
   - `{REF_LAYOUT}`：整体布局模式（网格/流程/层级/对称...）
   - `{REF_STYLE}`：视觉风格（线条粗细、框形状、间距、标注方式）
   - `{REF_PALETTE}`：色板信息

这些信息传递给后续的创建/美化步骤。

---

## Route A：TikZ 概念图创建

### 2A.1 收集图内容规格

AskUserQuestion（如 `$ARGUMENTS` 未提供足够信息）：
```
描述你要画的概念图：
- 图的目的/标题
- 包含哪些元素（概念、变量、参与者...）
- 元素之间的关系（因果、流程、层级、对比...）
- 特殊要求（子图、注释、数学符号...）
```

同时读取项目上下文：
- `structure/0_global/idea.md` → 研究框架理解
- `structure/3_methodology/methodology.md` → 模型结构（如果画模型图）
- 已有 `fig*.tex` → 风格一致性参考

### 2A.2 提议设计方案

用中文文字描述布局方案（**不写代码**）：

```
📐 Fig {N} 设计方案: {title}

布局: {描述整体结构，如"左右两列，左列为外部环境，右列为资源-策略映射"}

元素关系示意:
┌─────────┐    ──→    ┌─────────┐
│  元素 A  │          │  元素 B  │
└─────────┘    ←──    └─────────┘
       ↓
  ┌──────────┐
  │  元素 C   │
  └──────────┘

配色:
- 主体框: steelbluelight
- 强调框: goldlight
- 背景区域: morandigraylight
- 连接线: morandigray

{如有 Eagle 参考} 参考图风格借鉴: {具体说明借鉴了参考图的哪些要素}

确认方案？可以调整布局、元素、配色。
```

**循环**：用户不满意 → 修改方案 → 再次展示 → 直到用户确认。

### 2A.3 生成 standalone .tex

按照项目已有 TikZ 图的风格（从 `{FIGURE_INVENTORY}` 中已有 .tex 文件提取）生成代码。

**强制规范**：
- `\documentclass[tikz, border=8pt]{standalone}`
- `\usepackage{newtxtext,newtxmath}`
- `\usetikzlibrary{arrows.meta, shapes.geometric, fit, positioning, calc}`（按需增减）
- 箭头样式：`Stealth`
- Morandi 色板 `\definecolor`（见上方定义）
- 默认填充：`steelbluelight`（主体）、`goldlight`（辅助）、`morandigraylight`（背景区域）
- 线宽：`thick`（0.8pt 默认）、强调可用 `very thick`
- 文本：`\small` 或正常大小，`align=center`

写入 `structure/figures_tables/figures/fig{N}_{description}.tex`。

### 2A.4 编译验证

```bash
cd {project_root}/structure/figures_tables/figures && latexmk -pdf fig{N}_{description}.tex 2>&1 | tail -20
```

- 编译成功 → 继续
- 编译失败 → 解析错误信息，修复代码，重试（最多 3 次）
- 3 次仍失败 → 展示错误给用户，等待指示

### 2A.5 展示结果

用 Read 工具展示生成的 PDF 给用户。

```
✅ TikZ 图生成成功

📄 源文件: structure/figures_tables/figures/fig{N}_{description}.tex
📊 PDF: structure/figures_tables/figures/fig{N}_{description}.pdf

[展示 PDF 预览]

需要修改吗？指出具体调整（位置、大小、颜色、文字...）
```

**循环**：用户提出修改 → Edit .tex → 重新编译 → 再次展示 → 直到用户确认。

---

## Route B：Python/R 数据图美化

### 2B.1 定位目标图

- 根据用户指定的图编号/路径，定位：
  - 输出图片（PDF/PNG）→ 用 Read 工具查看
  - 源脚本（.py / .R）→ 读取代码
- 如果只有 PDF 没有源脚本 → AskUserQuestion 询问源脚本路径或数据文件路径
- 也检查 `data/scripts/`、`scripts/`、`code/` 目录下的脚本

### 2B.2 八维度诊断

读取图片（视觉分析）+ 读取源代码（代码分析），对照 8 个维度评估：

```
📋 Fig {N} 诊断报告

| # | 维度 | 状态 | 问题 | 建议 |
|:-:|:-----|:----:|:-----|:-----|
| 1 | 配色 | 🔴 | 使用 matplotlib 默认色 | 切换 Morandi 色板 |
| 2 | 字体 | 🟡 | sans-serif，与正文不一致 | 设置 Times New Roman |
| 3 | 标注 | ✅ | 轴标签完整 | — |
| 4 | 布局 | 🟡 | 图例位置遮挡数据 | 移至底部水平排列 |
| 5 | 子图 | ⬜ | 单图，不适用 | — |
| 6 | 分辨率 | 🔴 | PNG 72dpi | 改为 PDF 300dpi |
| 7 | 尺寸 | 🟡 | 宽高比不适合单栏 | 调整为 7"×5" |
| 8 | 细节 | 🟡 | 刻度标签过密 | 减少刻度数量 |
```

**状态定义**：
- 🔴 必须修复（严重影响出版质量）
- 🟡 建议修复（提升美观度）
- ✅ 无问题
- ⬜ 不适用

### 2B.3 与 Eagle 参考图对比（如有）

如果步骤 1 中选了 Eagle 参考图：

```
📊 与参考图对比

参考图: {name}（{annotation}）

| 方面 | 当前图 | 参考图 | 建议调整 |
|:-----|:-------|:-------|:---------|
| 配色 | 默认蓝橙 | 低饱和 Morandi | 切换色板 |
| 布局 | 单面板 | 左右双面板 | 考虑拆分为 (a)(b) |
| 字号 | 偏小 | 10pt 正文 | 放大标签字号 |
```

### 2B.4 提议美化方案

```
🎨 美化方案（共 {N} 处调整）

优先级高:
1. [配色] 全局配色切换为 Morandi 色板
2. [分辨率] 输出格式改为 PDF 300dpi

优先级中:
3. [字体] 设置 Times New Roman / serif
4. [布局] 图例移至右下角

优先级低:
5. [细节] 减少 X 轴刻度密度

确认？可以增删调整。
```

AskUserQuestion，循环直到确认。

### 2B.5 修改源脚本

根据确认的美化方案，修改 Python/R 脚本。关键注入模板：

**Python (matplotlib)**：
```python
import matplotlib.pyplot as plt
MORANDI = {"steel_blue": "#576fa0", "gold": "#e3b87f", "rose": "#b57979",
           "gray": "#9f9f9f", "steel_blue_l": "#a7b9d7", "gold_l": "#fadcb4",
           "rose_l": "#dea3a2", "gray_l": "#cfcece"}
plt.rcParams.update({
    "font.family": "serif", "font.serif": ["Times New Roman"],
    "font.size": 10, "axes.labelsize": 10, "xtick.labelsize": 9,
    "ytick.labelsize": 9, "legend.fontsize": 9, "figure.dpi": 300,
})
# 输出
plt.savefig("structure/figures_tables/figures/fig{N}_{desc}.pdf", bbox_inches="tight", dpi=300)
```

**R (ggplot2)**：
```r
morandi <- c("#576fa0", "#e3b87f", "#b57979", "#9f9f9f",
             "#a7b9d7", "#fadcb4", "#dea3a2", "#cfcece")
theme_morandi <- theme_minimal(base_family = "Times New Roman") +
  theme(text = element_text(family = "Times New Roman"),
        plot.title = element_text(size = 12, face = "bold"),
        axis.title = element_text(size = 10),
        axis.text = element_text(size = 9),
        legend.text = element_text(size = 9),
        panel.grid.minor = element_blank())
ggsave("structure/figures_tables/figures/fig{N}_{desc}.pdf", width = 7, height = 5, dpi = 300)
```

### 2B.6 运行脚本 + 验证

```bash
cd {project_root} && python3 structure/figures_tables/figures/fig{N}_{desc}.py 2>&1 | tail -20
# 或
cd {project_root} && Rscript structure/figures_tables/figures/fig{N}_{desc}.R 2>&1 | tail -20
```

- 输出 PDF 存在 → 用 Read 工具展示给用户
- 运行失败 → 展示错误信息，修复后重试

**循环**：用户提出修改 → 修改脚本 → 重新运行 → 再次展示 → 直到用户确认。

---

## Route C：Python/R 数据图创建

### 2C.1 收集图规格

AskUserQuestion：
```
描述你要创建的数据图：
- 图类型（散点图/柱状图/热力图/网络图/系数图/弦图/...）
- 数据来源（data/ 下的文件？脚本生成？手动输入？）
- X/Y 轴变量
- 分组/面板变量（如有）
- 特殊要求（误差线、置信区间、子图拼接...）
```

同时扫描项目的 `data/` 目录了解可用数据文件。

### 2C.2 推荐语言 + 设计方案

**语言推荐逻辑**：
- 网络图、弦图 → R（igraph / circlize 生态更强）
- 复杂 ggplot 风格统计图 → R
- 机器学习可视化、地理空间图 → Python
- 简单柱状/折线/散点 → 如项目已有 R 脚本则 R，否则 Python
- 用户指定 → 覆盖推荐

```
📊 Fig {N} 设计方案: {title}

类型: {coefficient plot with 95% CI}
数据: {data/model_results.csv}
语言: R（推荐理由：项目已有 R 脚本，ggplot2 生态适合此类图）
布局: {单面板 / 双面板 (a)(b)}
配色: Morandi 色板
  - 系列1: steel_blue #576fa0
  - 系列2: gold #e3b87f
  - 显著性: rose #b57979

确认？可以调整。
```

AskUserQuestion，循环直到确认。

### 2C.3 生成脚本

生成完整的 Python/R 脚本，预配置：
- Morandi 色板
- Times New Roman 字体
- PDF 300 DPI 输出
- 合理的 figsize（单栏 7"×5" / 双栏 14"×5"）
- 完整的坐标轴标签和图例

写入 `structure/figures_tables/figures/fig{N}_{description}.{py|R}`。

### 2C.4 运行 + 验证

同 Route B 的步骤 2B.6。

---

## Route D：跨图一致性审计

### 2D.1 扫描所有图源文件

```bash
python3 ~/.claude/skills/shared/figure_audit.py inventory --figures-dir structure/figures_tables/figures/
```

脚本提取每个图的：颜色定义、字体设置、输出格式、DPI、尺寸。
输出 `_figure_audit.json` + stdout 汇总表。

VERIFY: PASS = 全部一致。FAIL = 有不一致项。

### 2D.2 主 Agent 语义分析

在脚本机械检查基础上，主 Agent 补充语义级检查：
- 配色方案是否全局统一（不只是"用了 hex 色"，还要看"用的是同一套色板吗"）
- 标签风格一致性（(a)(b)(c) vs A/B/C vs 无标签）
- 坐标轴标注风格（Title Case vs sentence case vs ALL CAPS）
- 图例风格（框内 vs 框外，位置是否统一）

### 2D.3 展示审计报告

```
📋 跨图一致性审计 — {PAPER_TITLE}

共 {N} 张图（TikZ: {x}, Python: {y}, R: {z}）

| 维度 | 状态 | 详情 |
|:-----|:----:|:-----|
| 配色一致性 | 🟡 | fig1-fig4 Morandi，fig5 使用 R 默认色 |
| 字体一致性 | ✅ | 全部 Times New Roman / newtxtext |
| 输出格式 | 🔴 | fig3 为 PNG，其余 PDF |
| 尺寸一致性 | ✅ | 全部 7"×5" |
| 标签风格 | ✅ | 全部 (a)(b)(c) 标签 |
| TikZ 风格 | ✅ | 全部 Stealth 箭头 + Morandi 填充 |

修复建议:
1. fig5: 切换为 Morandi 色板（修改 R 脚本第 15 行）
2. fig3: 输出格式改为 PDF（修改 savefig 参数）
```

AskUserQuestion：
```
是否立即修复？
(1) 全部修复
(2) 选择性修复（输入编号，如 "1"）
(3) 暂不修复
```

选 (1) 或 (2) → 按 Route B 的美化流程逐个修复。

---

## 步骤 Final：完成提示

```
✅ Figure 操作完成

{Route A: 📐 创建了 TikZ 概念图}
{Route B: 🎨 美化了数据图}
{Route C: 📊 创建了数据图}
{Route D: 📋 完成了跨图一致性检查}

📂 文件:
- 源文件: structure/figures_tables/figures/fig{N}_{description}.{tex|py|R}
- 输出: structure/figures_tables/figures/fig{N}_{description}.pdf

📋 index.md 已更新（编号 Fig. {N}）

🔗 在 manuscript.tex 中引用:
\begin{figure}[!htbp]
\centering
\includegraphics[width=\textwidth]{structure/figures_tables/figures/fig{N}_{description}.pdf}
\caption{TODO}
\label{fig:TODO}
\end{figure}

💡 提示:
- 运行 /figure audit 检查所有图的一致性
- 投稿前 /pre-submit 也会检查图表规范
```

---

## 全局约束

### 交互模式
- 所有设计方案都走"中文提议 → 用户确认 → 执行"闭环
- 用户可随时输入 "stop" 中断流程

### 文件规范
- TikZ: standalone 文档，单独编译为 PDF
- Python/R: 独立脚本，输出 PDF 到 `structure/figures_tables/figures/`
- 命名: `fig{N}_{snake_case_description}.{tex|py|R}`
- **每次创建/修改图后，必须同步更新 `structure/figures_tables/index.md` 的 Figures 表格**

### 不越界
- 不修改 manuscript.tex（只提供引用代码供用户手动插入）
- 不修改已有图的数据内容（只改视觉呈现）
- 不替代用户的学术判断（图的内容选择由用户决定）

### Eagle 集成
- 库路径: `/Users/zylen/Library/CloudStorage/Dropbox/Apps/Eagle/research.library/`
- 搜索工具: `~/.claude/skills/shared/eagle_search.py`
- Eagle 搜索是可选的，不强制要求
- 建议用户持续向 Eagle 中添加好图并打标签，丰富参考库

### 跨 Skill 关系
- `/pre-submit` 会检查图表规范（分辨率、格式、引用完整性）
- `/paper-init` 创建 `structure/figures_tables/figures/` 目录和 `index.md` 注册表
- `/figure audit` 是 `/pre-submit` 图表检查的前置增强版
- 图表注册表 `structure/figures_tables/index.md` 是图表元数据的唯一索引
