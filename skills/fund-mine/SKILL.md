---
description: "基金项目 idea 挖掘：基于已有科研项目 + 已读论文 + 基金指南，与用户交互确认基金选题方向"
---

## 核心使命

帮助用户从已有科研积累（论文项目、已读文献）出发，结合基金申请指南的特定要求，交互式挖掘并确认基金申请选题方向。产出 `fund-idea.md`，可直接灌入 `/fund-init` 初始化基金项目。

## 输出语言规范

全程使用中文。方法论术语、理论名称、期刊名等专有名词可保留英文原文。

## Pipeline（五步交互流程）

### Step 1: 基金类型确认

使用 AskUserQuestion 询问：

```
申请什么类型的基金？
  [1] 国家自然科学基金（青年/面上/地区）
  [2] 省自然科学基金
  [3] 校级科研基金
  [4] 其他（请说明）
```

记录为 `{FUND_TYPE}`。

追问：

```
基金指南中有无特定主题要求/优先资助方向？
（如有，请粘贴相关段落或说明关键词；如无特定限制，回复"无"）
```

记录为 `{FUND_GUIDE}`。

### Step 2: 源项目选择

使用 AskUserQuestion 询问：

```
请选择 2-3 个你希望作为基金选题基础的科研项目。
请提供项目编号或文件夹名（如 zy15、dj03 等）。

个人项目目录：/Users/zylen/Library/CloudStorage/Dropbox/02-Research/papers
合作项目目录：/Users/zylen/Library/CloudStorage/Dropbox/02-Research/_GYM group dropbox/_gym paper
```

记录为 `{SOURCE_PROJECTS}`（列表）。

### Step 3: 源项目分析

对每个源项目执行：

1. **定位 idea.md**：在项目目录中查找 `structure/0_global/idea.md` 或项目根目录下的 `idea.md`
2. **定位 manuscript**：查找 `manuscript.tex` 或主 tex 文件
3. **提取关键信息**：
   - 研究问题（RQ）
   - 理论框架/方法论
   - 核心发现/贡献
   - 关键变量与数据
   - 研究领域标签

如果项目中没有 idea.md（如早期项目），尝试从 manuscript.tex 的 abstract/introduction 提取信息。

### Step 4: 交叉分析与方向生成

基于 Step 1-3 的信息，分析：

1. **共性线索**：多个项目间的共同主题、方法、理论基础
2. **互补视角**：不同项目覆盖同一问题的不同维度
3. **潜在综合**：将多个项目的方法/发现整合为更大叙事的可能性
4. **基金指南契合度**：每个潜在方向与 `{FUND_GUIDE}` 的匹配程度

生成 **2-3 个基金选题方向**，每个方向包含：

```markdown
### 方向 {N}: {拟题目}

**源项目组合**
- {项目编号}: 贡献了{什么}（方法/数据/理论/发现）
- {项目编号}: 贡献了{什么}

**核心创新点**（3-4 条）
1. ...
2. ...
3. ...

**可行性评估**
- 研究基础：已有哪些可复用的成果（数据、模型、文献积累）
- 技术可行性：方法是否成熟、数据是否可获取
- 时间可行性：在基金周期内能否完成
- 风险点：{潜在困难}

**与基金指南的契合度**
- {具体说明如何呼应指南要求}

**预估研究内容**（概要）
1. ...
2. ...
3. ...
```

将以上内容展示给用户，使用 AskUserQuestion 询问：

```
以上 {N} 个方向，你倾向哪个？
可以选择一个方向，也可以要求调整/合并/重新生成。
```

### Step 5: 定稿输出 fund-idea.md

用户确认方向后，**锚定**落盘路径为 `/Users/zylen/Library/CloudStorage/Dropbox/02-Research/fundings/_drafts/fund-idea_{YYYYMMDD}_{slug}.md`（`_drafts/` 若不存在则 `mkdir -p`；`{slug}` 为基金简称或题目关键词 snake_case）。这样 `/fund-init` 能通过固定路径 glob 找到最新的 fund-idea 文件。

执行（主 agent 必须先把 `{slug}` 替换为实际字面量，否则文件名会出现字面量 `{slug}` 或空串；然后用 Write 工具写入 `$OUT` 指向的路径，shell 本身不写文件）：
```bash
SLUG="{slug}"   # 主 agent 替换为实际字符串（snake_case 基金简称）
mkdir -p /Users/zylen/Library/CloudStorage/Dropbox/02-Research/fundings/_drafts
OUT="/Users/zylen/Library/CloudStorage/Dropbox/02-Research/fundings/_drafts/fund-idea_$(date +%Y%m%d)_${SLUG}.md"
echo "OUT=$OUT"   # 由主 agent 读取后用 Write 工具写入 fund-idea 内容
```

fund-idea.md 内容格式：

```markdown
# 基金选题方案

## 基本信息

- **基金类型**: {FUND_TYPE}
- **拟题目**: {确认后的题目}
- **源项目**: {项目列表及各自贡献}
- **生成日期**: {YYYY-MM-DD}

## 基金指南要求

{FUND_GUIDE 原文或摘要}

## 核心创新点

1. ...
2. ...
3. ...
4. ...

## 研究内容概要

### 研究目标
{总目标 + 分目标}

### 研究内容
1. {内容一}
2. {内容二}
3. {内容三}

### 拟采用的方法与技术路线
{基于源项目的方法组合}

## 可行性分析

### 研究基础
{来自源项目的已有积累}

### 数据与工具
{可用数据、模型、代码}

### 风险与应对
{识别的风险及对策}

## 源项目详情

### {项目编号}: {项目名}
- idea.md 路径: {绝对路径}
- manuscript 路径: {绝对路径}
- 关键贡献: {对基金项目的贡献}

### {项目编号}: {项目名}
...
```

## 注意事项

- **不修改源项目的任何文件**，只读取信息
- 如果源项目处于早期阶段（无 idea.md），从可用材料中尽量提取，不足部分标注"待补充"
- 基金选题不必完全等于任何一个源项目，鼓励跨项目综合
- `fund-idea.md` 的输出粒度应足够支撑 `/fund-init` 初始化，但不必达到申请书正文的详细程度
