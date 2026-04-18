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
| Gray | `#7c7c7c` (dark) / `#b5b5b5` (mid) | `#cfcece` (light) | 结构/次要元素（三档灰） |

> **Gray 三档**：TikZ 结构色（层容器虚线边、结构箭头、文本）用 `#7c7c7c`（深，实战中 `#9f9f9f` 太淡看不清）；I/O 盒/日志带等背景块用 `#b5b5b5` 的 !45~!55；浅色辅助区域用 `#cfcece`。

**TikZ 定义**：
```latex
\definecolor{steelblue}{HTML}{576fa0}
\definecolor{steelbluelight}{HTML}{a7b9d7}
\definecolor{gold}{HTML}{e3b87f}
\definecolor{goldlight}{HTML}{fadcb4}
\definecolor{rose}{HTML}{b57979}
\definecolor{roselight}{HTML}{dea3a2}
\definecolor{morandigray}{HTML}{7c7c7c}       % 结构色（深）
\definecolor{morandigraymid}{HTML}{b5b5b5}    % I/O 盒 / 日志带（中）
\definecolor{morandigraylight}{HTML}{cfcece}  % 辅助区域（浅）
```

**Python**：
```python
MORANDI = {
    "steel_blue": "#576fa0", "steel_blue_light": "#a7b9d7",
    "gold": "#e3b87f", "gold_light": "#fadcb4",
    "rose": "#b57979", "rose_light": "#dea3a2",
    "gray": "#7c7c7c", "gray_mid": "#b5b5b5", "gray_light": "#cfcece",
}
```

**R**：
```r
morandi <- c("#576fa0", "#e3b87f", "#b57979", "#7c7c7c",
             "#a7b9d7", "#fadcb4", "#dea3a2", "#b5b5b5", "#cfcece")
```

---

## 步骤 0：上下文加载 + 路由判断

### 0.1 读取项目配置 + 项目类型探测（决定 `{FIGURES_DIR}`）

- 读取 `CLAUDE.md` → 提取 `{PUBLISHER}`、`{TARGET_JOURNAL}`、`{METHOD_TYPE}`、`{PAPER_TITLE}`
- **项目类型探测**（决定图目录 `{FIGURES_DIR}`）：
  - IF `$PWD` 包含 `dissertations/` → `{FIGURES_DIR}=structure/figures_tables/figures/`（学位论文也用同一结构，但主 tex 位置不同，见下）
  - IF `structure/figures_tables/figures/` 存在 → `{FIGURES_DIR}=structure/figures_tables/figures/`（`/finalize` 前的小论文）
  - IF `figures/` 在项目根目录存在 且 `structure/` 不存在 → `{FIGURES_DIR}=figures/`（`/finalize` 后的小论文，脚手架已清理）
  - 其他（新项目）→ 默认 `{FIGURES_DIR}=structure/figures_tables/figures/`
- **LaTeX 路径契约**：建议主 tex 文件 preamble 添加 `\graphicspath{{structure/figures_tables/figures/}{figures_tables/figures/}{figures/}}`（paper-init 的 manuscript.tex.tmpl 应含此行），这样 `\includegraphics{fig1_foo.pdf}` 使用纯文件名即可，不受 `/finalize` 前后目录迁移影响。
- 扫描 `{FIGURES_DIR}` 目录 → 列出已有图文件 → `{FIGURE_INVENTORY}`
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

- 扫描 `{FIGURES_DIR}` 中已有的 `fig{N}_*` 文件
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
- `\documentclass[tikz, border=10pt]{standalone}`
- `\usepackage{newtxtext,newtxmath}`
- `\usetikzlibrary{arrows.meta, positioning, calc}`（基础三件套）；若需背景层用 `backgrounds`；若画 shape 用 `shapes.geometric`；**不要用 `fit`**（见 2A.3.1 C1，fit 会导致多层容器偏心）
- 箭头样式：`Stealth`
- Morandi 色板 `\definecolor`（见上方定义，含三档灰 `morandigray`/`morandigraymid`/`morandigraylight`）
- 默认填充：`steelbluelight!50`（主体）、`goldlight!55`（辅助）、`morandigraymid!55`（I/O 盒）；**fill 饱和度 `!45` 起步**，低于此盒子在 PDF 里会"消失"（见 2A.3.1 B.1）
- 线宽：`thick`（0.8pt 默认）、强调可用 `very thick`
- 文本：`\small` 或正常大小；**多行文本禁止依赖 `\\`**（有时静默失效），用 2A.3.1 C3 的"空容器 + 独立子节点"模式

写入 `{FIGURES_DIR}fig{N}_{description}.tex`。

#### 2A.3.1 分层流程图（Layered architecture diagram）完整手册

> 本节是**画架构图/流程图/分层图的唯一参考**。按 A-G 七个模块顺序阅读：A 原则 → B 色彩 → C 元素 → D 坐标 → E 路径 → F 场景 → G 陷阱速查。新手从 F 场景配方开始抄；进阶看 C 元素手册按需组合；出 bug 看 G 速查。

---

##### A. 三条设计原则（永远不变）

1. **自顶向下阅读**：层编号 1→N 从上到下；输入盒在顶、输出盒在底；主信息流向下
2. **三色点睛 + 其余全灰**：整图最多 3 种语义色，结构性元素（容器、流程、I/O、日志、普通箭头）一律 `morandigray`
3. **主/反差异**：主流程 = 实线 + 结构灰；反馈/回流 = 虚线 + 语义色。靠线型和颜色双重区分

---

##### B. 色彩体系

**色板**（见 SKILL.md 顶部 Morandi 定义）：
```latex
\definecolor{steelblue}{HTML}{576fa0}       \definecolor{steelbluelight}{HTML}{a7b9d7}
\definecolor{gold}{HTML}{e3b87f}            \definecolor{goldlight}{HTML}{fadcb4}
\definecolor{rose}{HTML}{b57979}            \definecolor{roselight}{HTML}{dea3a2}
\definecolor{morandigray}{HTML}{7c7c7c}     \definecolor{morandigraymid}{HTML}{b5b5b5}
\definecolor{morandigraylight}{HTML}{cfcece}
```

**语义分配示例**（需结合论文主题选定）：
| 色 | 典型语义 | 示例 |
|:---|:---------|:-----|
| Steel blue | 知识/检索/显性/默认主体 | RAG / explicit_RAG / Stage-1 知识类 |
| Gold | 执行/计算/隐性/工具调用 | FC / tacit_FC / Stage-2 评估 |
| Rose | 人工/干预/反馈/警示 | Human review / Override / Key principle callout |
| Gray(morandigray) | 结构/流程/日志/辅助 | 容器、主流程箭头、DTT 带、I/O 盒 |

**配对硬规则**：
- **B.1 Fill ≥ !50 饱和度**：低于 !45 的填充在 PDF 里几乎看不见，盒子"消失"。常用 `!50-!60`
- **B.2 Fill XOR Draw**：盒子要么填彩色（边默认无/灰），要么只描彩边（填白）；不要同时 `fill=彩色 + draw=同色`（双装饰污染）
- **B.3 稳定模式 = 灰边 + 彩填**：`draw=morandigray + fill=accent!50` 是**唯一**能保证任何色都能渲染的组合
- **B.4 xcolor 冲突警告**：`draw=steelblue, fill=white` 经常**边框画不出**（xcolor 有同名预定义色可能占用解析），换用 B.3 方案或改用灰边

---

##### C. 元素手册（逐个元素的稳定模式）

###### C1. 层容器（Layer container）

```latex
layerbox/.style={draw=morandigray, thick, fill=none,
    rounded corners=8pt, dash pattern=on 3pt off 2pt},
\node[layerbox, minimum width=15.6cm, minimum height=3.3cm] (L1) at (7.5, 5.5) {};
```

硬规则：
- 圆角 `rounded corners=8pt` 必须（无圆角生硬）
- dash pattern 必须显式写 `on 3pt off 2pt`（默认 `dashed` 在圆角处 dash 不规律，看起来像斜线）
- `fill=none` 必须（填色 + 虚线双重装饰污染）
- **用显式坐标放置**：`at (center_x, y)` + `minimum width/height` 指定。**绝不用 `fit`**（fit 按内容 bounding box 算，不同层边界不同会算出偏心，上下层对不齐）
- 多层容器同宽（同 `minimum width`） + 同中心 x（统一 `center_x`）

###### C2. 层标签（Layer label）

```latex
layerlabel/.style={font=\footnotesize\bfseries, text=morandigray},
\node[layerlabel, anchor=south west] at ($(L1.north west)+(0.1,0.08)$)
    {Layer 1: Dual knowledge base};
```

- 放容器**外部顶部**（`anchor=south west` + 向上 0.08cm 偏移），避免被虚线边框切过
- 不放容器内部（除非容器有填色能遮挡虚线）
- **如果容器顶部外侧还要走 backtrack/overflow 弧线** → label 会和弧线 label 抢位置 → 把 layer label 换到右上角：`anchor=south east @ container.north east`

###### C3. 内容盒 —— 空容器 + 独立子节点模式（C3 是本手册最重要的 recipe）

**禁止**单节点内 `\\` 多行，因为 `\\` 在不同 style 下会静默失效（症状："Chunking117 chunks" 同一行）。

**稳定模式**：盒子是**空容器**，内部每个元素用**独立节点**，相对 `(B.north)` 用 `yshift` 定位。

```latex
% style 定义
stageblue/.style={draw=morandigray, fill=steelbluelight!50,
    rounded corners=4pt, thick,
    minimum width=2.9cm, minimum height=2.6cm},
title/.style={font=\small\bfseries, anchor=center},
sub/.style  ={font=\scriptsize, anchor=center},
body/.style ={font=\scriptsize, text=black!75, align=left,
    anchor=north west, text width=2.4cm},  % text width 比 minimum width 小 0.4-0.5cm

% 使用（假设 B 的宽度为 2.9cm，半宽 1.45cm）
\node[stageblue] (B) at (x, y) {};                              % 空容器
\node[title] at ($(B.north)+(0, -0.30)$) {Stage 1};             % 距顶 0.30cm
\node[sub]   at ($(B.north)+(0, -0.62)$) {Identification};      % 距顶 0.62cm（与 title 间隔 0.32cm）
\draw[steelblue!40, thick]                                       % 分隔线：跨盒内部 2/3 宽
    ($(B.north)+(-1.20, -0.85)$) -- ($(B.north)+(1.20, -0.85)$);
\node[body] at ($(B.north)+(-1.15, -0.97)$) {%                  % body 从分隔线下 0.12cm 开始
    RAG: cases, contracts\\[1pt]
    FC: ---\\[1pt]
    Out: type, precedents};
```

**在 body 节点里**，`\\[Npt]` 行间距还算稳定（因为有 `align=left` + 显式 `text width`），但避免超过 3 行；超过 3 行建议拆多个 body 节点。

**盒内元素垂直预算**（高度 2.6cm 的盒子）：
| 元素 | 垂直占用 |
|:-----|:---------|
| title (距顶 0.3) | 0.3 cm 偏移 |
| sub (距顶 0.62) | 0.3 cm 偏移 |
| 分隔线 (距顶 0.85) | 0.2 cm |
| body (从 0.97 起 + 4 行 + 行距) | ~1.3 cm |
| 底部留白 | ≥ 0.3 cm |
| **总** | ~2.6 cm ✓ |

如果 body 内容更多 → 增加 `minimum height` 到 3.0+ cm。

###### C4. I/O 盒（输入 / 输出 / 数据带）

```latex
iobox/.style={draw=none, fill=morandigraymid!55, rounded corners=3pt,
    minimum width=2.6cm, minimum height=0.8cm, align=center,
    font=\small\bfseries, text=black!85},
\node[iobox] (cr) at (center_x, top_y)    {CR Input};
\node[iobox] (ar) at (center_x, bottom_y) {AR Output};
```

- 固定灰色无边框，和彩色盒子视觉区分
- 位置：图顶（输入）和图底（输出），在层容器**外部**
- I/O 和层容器之间用短垂直箭头（0.5-1.0cm 长）连接

###### C5. 主流程箭头（实线灰）

```latex
arrow/.style={->, thick, morandigray},
\draw[arrow] (A.east) -- (B.west);                         % 水平
\draw[arrow] (center_x, y_from) -- (center_x, y_to);       % 垂直（显式坐标，不用 anchor）
```

- 水平：用 `.east -- .west`
- **垂直：必须用显式坐标** `(center_x, y1) -- (center_x, y2)`，不要用 `A.south -- B.north`（不同大小盒子 anchor 点计算可能偏差）
- 箭头长度 0.5-1.5cm（外观最清爽）
- midway label：`node[chanlabel, midway, above] {text}`，`chanlabel/.style={font=\scriptsize, text=morandigray!90!black}`

###### C6. 反馈 / 回流路径（虚线语义色）

```latex
rosepath/.style={->, thick, rose, dash pattern=on 3pt off 2pt},
```

**绝对禁止** `-|` / `|-` 搭配 `rounded corners`（TikZ 圆角算法画出的弧不工整，经常比预期大或歪）。

**场景 a：单个锐角拐弯**（可以不用圆角）：
```latex
\draw[rosepath]
    (src.east) -- ++(0.5, 0) -- ++(0, -2.1) -- (dst.east);    % 三段显式 polyline
```

**场景 b：必须圆角**（比如 backtrack 弧上去再左折下来）：
```latex
\draw[rosepath, rounded corners=4pt]
    (pm.north) -- ++(0, 0.45) -| (s1.north)
    node[chanlabel, text=rose, pos=0.3, above] {Backtrack};
```
`-|` 在这里可用，因为弧线不和其他 rounded corner 图形相交，视觉上圆角弧够小够工整。如果路径多次拐弯 → 拆成多段手写 polyline。

**场景 c：绕过其他盒子**：
如果 A→B 的直线路径天然穿过盒 C（或 C 的 y 范围）：
- 方案 1：把 C 挪走
- 方案 2：路径多绕一段（从 A 向外走足够距离，再拐向 B）
- **不让路径穿过任何盒体**

###### C7. 跨层索引 / 依赖虚线（小短路径）

```latex
\draw[->, thick, morandigray, dash pattern=on 3pt off 2pt]
    (src.south) -- (dst.north);
```

- 用**灰虚线**而非玫瑰色（玫瑰留给"反馈/干预"语义）
- 短、直、少拐弯
- 用于 DTT source_id 依赖、vector store → retrieve 的 index 连接等

###### C8. 标题 + metadata（图顶部元数据）

**硬规则：两行分开 y，不同 y 坐标**：
```latex
\node[font=\small\bfseries, text=black!85] at (center_x, y1)
    {Case A30 (P2 laboratory) --- DTT excerpt};
\node[font=\scriptsize, text=morandigray!90!black] at (center_x, y1 - 0.4)
    {KCR = 1.00 \quad ETR = 0.32 (S2, S3) / 1.94 (S4)};
```

- y 间距约 0.4cm
- 字号对比清晰：主 `\small\bfseries`，副 `\scriptsize`
- 若同 y 放两 node 且 x 跨度重叠 → 文字会叠印（典型 bug）

###### C9. 关键原则 callout（rose 边 + 白填）

```latex
notebox/.style={draw=rose, thick, fill=white, rounded corners=3pt,
    font=\scriptsize, text=rose, text width=8cm, align=center, inner sep=5pt},
\node[notebox] (principle) at (center_x, top_y) {%
    \textbf{Key principle}: the LLM does not compute;
    all quantitative reasoning is performed by FC functions.};
```

- 放图最顶或图中醒目位置
- 内容短而关键（一句话原则）
- 作为视觉锚点，吸引读者第一眼看到

###### C10. 图例（legend）

- 底部一行水平列出，左对齐或均分
- 每项：`\node[font=\scriptsize, text=<accent>, anchor=west] at (x, y) {\textbullet\ 说明}`
- 条目间 x 间距 ≥ 3cm 防挤
- 最后一条通常是 arrows 含义说明（灰色文本）

```latex
\node[font=\scriptsize, text=steelblue!85!black, anchor=west]
    at (0.2, -4.3) {\textbullet\ explicit\_RAG (retrieved)};
\node[font=\scriptsize, text=gold!75!black, anchor=west]
    at (4.8, -4.3) {\textbullet\ tacit\_FC (computed)};
\node[font=\scriptsize, text=morandigray, anchor=west]
    at (8.9, -4.3) {arrows: source\_id $\rightarrow$ dependent node};
```

---

##### D. 坐标布局公式（布局前必须手算）

###### D1. 盒子间距公式

对每对相邻盒 A、B（中心 x_A、x_B，宽度 w_A、w_B）：
```
gap(A, B) = x_B - w_B/2 - (x_A + w_A/2)
必须  gap ≥ 0.4 cm，建议 0.5-0.7 cm
```

**在 .tex 开头用注释写出所有 x 位置**，作为自检：
```latex
% Row positions (all gaps = 0.5 cm):
%   s1 center=0.85  w=2.6  span [-0.45, 2.15]
%   s2 center=3.95  w=2.6  span [ 2.65, 5.25]   gap to s1 = 0.50 OK
%   pm center=6.50  w=1.5  span [ 5.75, 7.25]   gap to s2 = 0.50 OK
%   s3 center=9.05  w=2.6  span [ 7.75,10.35]   gap to pm = 0.50 OK
%   s4 center=12.15 w=2.6  span [10.85,13.45]   gap to s3 = 0.50 OK
%   hd center=14.70 w=1.5  span [13.95,15.45]   gap to s4 = 0.50 OK
```

若编辑 .tex 时注释里出现 Unicode `−` (U+2212) 或 `±` → unicode-guard 会拦下写入 → **注释只用 ASCII `-` 和 `+/-`**。

###### D2. 容器宽度 / 高度

```
container_width  ≥ Σ(box_widths) + Σ(gaps) + 2 × padding      (padding ≥ 0.3 cm)
container_height = box_height + top_space + bottom_space       (top/bottom ≥ 0.3 cm)
```

若容器顶部要走 backtrack 弧线：`top_space` 再加 0.5-0.6cm。

###### D3. 多带图的上下带对齐

上下两个 layerbox 同宽 + 同 center x + 对应列 x 相同。这样跨带垂直连线才能笔直。

例（fig2 RAG pipeline）：
- 上带 indexing：Chunk / Embed / Store 在 x=6.4 / 10.0 / 13.6
- 下带 query：Cosine-top-k / Rerank 在 x=10.0 / 13.6（与上带同列）
- index 虚线从 Store.south 直接垂直下到 Cosine-top-k.north，完全笔直

###### D4. 多行堆叠（DTT 样式）

每行一个背景带 + 固定行高：
```
row_y_step = box_height + row_gap    (row_gap ≥ 0.3cm)
背景带 minimum_height = box_height + 0.25 cm  (盒子高度 + 小内边距)
```

例（fig5 DTT）：盒高 1.05cm + 行间距 0.35cm → row_y_step = 1.4cm。

###### D5. 同列对齐（列 x 锁定）

一旦确定某图用 N 列布局（N = 3/4/5），**所有行共享同一组列 x**。某行盒子数 < N 则右侧留空。不要重新均分（否则列错位）。

---

##### E. 路径路由硬规则

1. **E.1 垂直箭头用显式坐标**，不用 `.south / .north` anchor（不同大小盒子 anchor 计算会偏）
2. **E.2 禁止** `-|` / `|-` 配 `rounded corners`（除非单次 90° 折角，场景 C6.b）
3. **E.3 多段折线用显式 3 段 polyline**：`(x1,y1) -- (x2,y1) -- (x2,y2) -- (x3,y2)`
4. **E.4 反馈路径绕图外部**，不穿越任何盒体
5. **E.5 Backtrack 弧**：从 PM 顶 → 向上出容器 → 向左 → 向下入 S1 顶。容器高度要给弧线留 0.5cm+
6. **E.6 Override feedback**：从 HD → 向右出容器 → 向下到 DTT 高度 → 向左入 DTT 东边。走右侧，不穿过中间内容
7. **E.7 Index/依赖短链接**：纯灰虚线，`.south -- .north` 或显式坐标，不加 label 除非必要

---

##### F. 五种常见场景的配方（直接抄）

###### F.1 单行 N 个异构盒（fig4：4 stages + 2 humans）

- 盒子按 D1 公式算好 x，gap 0.5cm
- 水平主流程箭头 `.east -- .west`
- 顶部 CR Input（iobox），底部 AR Output
- 回流弧（Backtrack / Override）走容器上方/右侧外部
- 容器 layer label 放右上角（避开 Backtrack label）

###### F.2 两带平行布局（fig2：indexing + query）

- 两个 layerbox 同宽 + 同 center x + 上下叠放
- 上下带内部各自按 F.1 布局
- 跨带箭头：虚线 3 段 polyline，或 `.south -- .north` 直连
- 带间垂直距离 ≥ 1.5cm（给跨带虚线箭头呼吸空间）
- 底部若有附加信息（preference note），用 rose notebox，dashed 箭头回指相关盒子

###### F.3 上带 generic + 下带 example（fig3：通用 FC loop + S2→F1 实例）

- 上带 3 个 phase box（主要尺寸，比如 4.6cm 宽 × 3.8cm 高）
- 下带 3 个 example box（略小，比如 4.6cm 宽 × 2.6cm 高）
- 两带用单条 "instantiates" 虚线垂直连接，在 center x
- 上带 label "Generic ..."，下带 label "Example: ..."
- 图顶放 Key principle rose callout 吸引注意

###### F.4 多行 stage 堆叠（fig5：DTT 按 S1/S2/S3/S4 四行）

- 每行一个背景色块（`fill=steelbluelight!15` 或 `!18`，低饱和度做分区）
- 行间 y step 1.4cm（盒高 1.05 + 间距 0.35）
- 固定 N 列（如 4 列，x=1.9, 5.0, 8.1, 11.2）
- 每行最多 N 个盒子，少于 N 则右侧留空（不重排）
- 行左侧 stage 标签 `anchor=east` @ 最左侧固定 x（如 0.2）
- 顶部标题 + metadata 两行（C8），底部图例一行（C10）

###### F.5 中心辐射（hub-and-spoke，本手册未实战，仅原则）

- 中心放主体框，周围 4-6 个卫星框
- 所有箭头从中心出发或指向中心（靠近中心的那端用 `.north/.south/.east/.west` 对应方向）
- 卫星间不连线（避免干扰）
- 用角度均布卫星位置：`at ({center_x + r*cos(angle)}, {center_y + r*sin(angle)})`

---

##### G. 致命陷阱速查（出 bug 先查这 10 条）

| # | 症状 | 原因 | 修复 |
|:-:|:-----|:-----|:-----|
| G1 | 盒子"消失"只剩文字 | `fill=color!30` 或更低 | fill 下限 `!45`，常用 `!50-!60` |
| G2 | draw=steelblue 白填盒子边框不出 | xcolor 命名冲突 | B.3：`draw=morandigray + fill=accent!50` |
| G3 | 多行文字挤一行 (如 "Chunking117 chunks") | 节点内 `\\` 静默失效 | C3：空容器 + 独立 title/sub/body 节点 |
| G4 | 相邻盒 0.1-0.3cm 肉眼看不到的重叠 | 布局前没算 | D1：注释里写出 [x_min, x_max] + gap |
| G5 | Backtrack 弧和 layer label 挤顶部 | 同一个容器顶部两元素抢位置 | C2：layer label 换 `anchor=south east` |
| G6 | 标题和 metadata 叠印 | 同 y 放两 node | C8：两行分开 y，间距 0.4cm |
| G7 | `-\|` 或 `\|-` 配 rounded corners 出现诡异圆弧 | TikZ 圆角算法 | E.3：三段显式 polyline |
| G8 | 跨带垂直箭头歪斜 | `.south/.north` anchor 计算偏差 | C5：显式 `(center_x, y1) -- (center_x, y2)` |
| G9 | Write .tex 被 unicode-guard 拦 | 注释里有 Unicode `±` `−` | D1：注释只用 ASCII `+/-` `-` |
| G10 | `pdflatex && rm` 触发权限提示 | Claude Code 复合命令整体匹配 | 两条独立 Bash 调用，或白名单 `Bash(pdflatex * && rm *)` |

### 2A.4 编译验证 + 视觉自查闭环（强制）

**核心原则**：编译通过不等于图对。必须编译 → Read PDF → 视觉诊断 → 修 → 再编译，**自循环**直到视觉无缺陷，再交给用户。不要写完就甩给用户说"改好了"。

```bash
cd {project_root}/{FIGURES_DIR} && pdflatex -interaction=nonstopmode fig{N}_{description}.tex 2>&1 | tail -5
```

**编译层**：
- 编译成功 → 进入视觉自查
- 编译失败 → 解析错误，修复，重试（最多 3 次）
- 3 次仍失败 → 展示错误给用户，等待指示

**视觉自查层**（强制，不得跳过）：

每次编译成功后，**主 agent 必须用 Read 工具打开 PDF** 视觉检查。检查 checklist（每一条都要确认）：

1. **盒子是否渲染到 `minimum width/height`？**
   - 常见坑：`fill=<color>!30` 等过淡填充让盒子几乎不可见
   - 常见坑：`draw=<某个重定义的 xcolor 命名色>` 可能与预定义色冲突导致边框不显示（如 `draw=steelblue` 与 xcolor 的 `steelblue` 冲突）
   - **修复**：fill 不低于 !50 / !55；改用 `draw=morandigray` 灰边 + 彩色 fill 的稳定组合
2. **节点内多行文本是否换行？**
   - 常见坑：`\\` 在某些 style 下没生效，title 和 subtitle 挤在一行（如 "Chunking117 chunks"）
   - **修复**：style 必须显式含 `align=center`，或者用**独立的 title 节点 + 独立的 sub 节点**相对盒子 center 做 yshift 定位
3. **箭头是否和其他元素重叠/穿过？**
   - 常见坑：反馈箭头垂直上升穿过下游输出盒；`|-` / `-|` 与 `rounded corners` 产生不工整圆弧
   - **修复**：用显式 3 段 polyline `(x1,y1) -- (x2,y1) -- (x2,y2) -- (x3,y2)`；把被穿过的节点移到别的 x 坐标
4. **层容器边框是否有内部元素溢出？**
   - 检查每个容器的 `minimum width/height` 能否包住所有子元素 + 0.3cm 内边距
   - Backtrack / 回流弧线是否压到容器上边框（通常因为容器高度不够给弧线留空间）
5. **标签位置是否被其他元素遮挡？**
   - Layer label 是否被虚线边框穿过？（须 `anchor=south west` + 向外偏移 0.08cm）
   - 箭头 midway label 是否被另一条线覆盖？
6. **三色纪律是否守住？**
   - 全图强调色是否 ≤ 3 种？结构性元素是否全灰？
   - Fill 和 draw 是否二选一（避免同时 `fill=彩色` + `draw=同色` 双装饰）
7. **对齐是否严格？**
   - 同一"带"内的盒子中心 y 是否一致？同一列的 x 是否一致？
   - 上下两带的对应列 x 是否对齐（方便垂直连接）？

**循环规则**：
- 发现 ≥1 条缺陷 → 立刻修代码，重编译，再 Read PDF，再查 checklist
- **不要**一次集齐所有缺陷再改——每次只改 1-2 处，避免引入新问题
- **不要**只凭视觉"看起来差不多"就收工——每条 checklist 条目都要明确 ✓ 或确认不适用
- 单个图的迭代次数不设上限，但如果 > 5 轮还没收敛，回到草稿阶段重新想布局

**终止条件**：checklist 7 条全过 → 才能把图交给用户 / 进入下一张图。

### 2A.5 展示结果

用 Read 工具展示生成的 PDF 给用户。

```
✅ TikZ 图生成成功

📄 源文件: {FIGURES_DIR}fig{N}_{description}.tex
📊 PDF: {FIGURES_DIR}fig{N}_{description}.pdf

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

> ⚠️ **占位符替换契约**：下方模板中的 `{FIGURES_DIR}`、`{N}`、`{desc}` 是**写盘前**必须由主 agent Edit 替换为实际字符串的占位符——Python/R 运行时**不会**展开它们。例如 `{FIGURES_DIR}` → `structure/figures_tables/figures/`、`{N}` → `3`、`{desc}` → `network_topology`。忘记替换会生成字面量名为 `{FIGURES_DIR}fig{N}_{desc}.pdf` 的文件。

**Python (matplotlib)**：
```python
import matplotlib.pyplot as plt
MORANDI = {"steel_blue": "#576fa0", "gold": "#e3b87f", "rose": "#b57979",
           "gray": "#7c7c7c", "gray_mid": "#b5b5b5",
           "steel_blue_light": "#a7b9d7", "gold_light": "#fadcb4",
           "rose_light": "#dea3a2", "gray_light": "#cfcece"}
plt.rcParams.update({
    "font.family": "serif", "font.serif": ["Times New Roman"],
    "font.size": 10, "axes.labelsize": 10, "xtick.labelsize": 9,
    "ytick.labelsize": 9, "legend.fontsize": 9, "figure.dpi": 300,
})
# 输出
plt.savefig("{FIGURES_DIR}fig{N}_{desc}.pdf", bbox_inches="tight", dpi=300)
```

**R (ggplot2)**：
```r
morandi <- c("#576fa0", "#e3b87f", "#b57979", "#7c7c7c",
             "#a7b9d7", "#fadcb4", "#dea3a2", "#b5b5b5", "#cfcece")
theme_morandi <- theme_minimal(base_family = "Times New Roman") +
  theme(text = element_text(family = "Times New Roman"),
        plot.title = element_text(size = 12, face = "bold"),
        axis.title = element_text(size = 10),
        axis.text = element_text(size = 9),
        legend.text = element_text(size = 9),
        panel.grid.minor = element_blank())
ggsave("{FIGURES_DIR}fig{N}_{desc}.pdf", width = 7, height = 5, dpi = 300)
```

### 2B.6 运行脚本 + 视觉自查闭环（强制）

**与 2A.4 同一原则**：运行通过不等于图对，必须 Read PDF 视觉确认。

```bash
cd {project_root} && python3 {FIGURES_DIR}fig{N}_{desc}.py 2>&1 | tail -20
# 或
cd {project_root} && Rscript {FIGURES_DIR}fig{N}_{desc}.R 2>&1 | tail -20
```

- 运行失败 → 展示错误，修复重试
- 运行成功 → **必须 Read PDF** 自查 checklist：
  1. 坐标轴标签是否被截断？（`bbox_inches="tight"` 是否生效）
  2. 图例是否遮挡数据？位置是否合理？
  3. 字号在正文尺寸下是否可读？（一般正文宽度下 9-10pt 最小）
  4. 颜色是否严格 Morandi 色板？（不可出现 matplotlib 默认红绿蓝）
  5. 多面板 (a)(b) 标签是否一致、对齐？
  6. Y 轴数值范围是否合理（不应有过多空白或刻度标签溢出）？

发现缺陷 → 改脚本 → 重跑 → 再 Read PDF → 再查。自循环直到 checklist 全过，才展示给用户。

**用户确认轮**：自查通过后展示给用户，接受用户的语义反馈 → 改 → 再自查 → 直到用户确认。

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

写入 `{FIGURES_DIR}fig{N}_{description}.{py|R}`。

### 2C.4 运行 + 验证

同 Route B 的步骤 2B.6。

---

## Route D：跨图一致性审计

### 2D.1 扫描所有图源文件

```bash
python3 ~/.claude/skills/shared/figure_audit.py inventory --figures-dir {FIGURES_DIR}
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
- 源文件: {FIGURES_DIR}fig{N}_{description}.{tex|py|R}
- 输出: {FIGURES_DIR}fig{N}_{description}.pdf

📋 index.md 已更新（编号 Fig. {N}）

🔗 在 manuscript.tex 中引用（使用纯文件名，依赖 preamble `\graphicspath{}` 兜底）:
\begin{figure}[!htbp]
\centering
\includegraphics[width=\textwidth]{fig{N}_{description}.pdf}
\caption{TODO}
\label{fig:TODO}
\end{figure}

> **注**：如果 preamble 未设置 `\graphicspath{}`，请临时改成绝对路径 `{FIGURES_DIR}fig{N}_{description}.pdf`，并建议把 `\graphicspath{{structure/figures_tables/figures/}{figures_tables/figures/}{figures/}}` 加到主 tex 的 preamble，以免 `/finalize` 清理脚手架后所有图链断裂。

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
- Python/R: 独立脚本，输出 PDF 到 `{FIGURES_DIR}`
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
- `/paper-init` 创建 `structure/figures_tables/figures/` 目录和 `index.md` 注册表（项目初始默认结构；`/figure` 通过 Step 0.1 类型探测决定最终 `{FIGURES_DIR}` 值）
- `/figure audit` 是 `/pre-submit` 图表检查的前置增强版
- 图表注册表 `structure/figures_tables/index.md` 是图表元数据的唯一索引
