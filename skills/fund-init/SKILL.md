---
description: "初始化基金申请项目：关联源项目 + 按基金类型选择模板骨架 + 生成项目结构和 CLAUDE.md"
---

## 核心使命

从 `/fund-mine` 产出的 `fund-idea.md`（或用户直接提供的选题方向）出发，在 `fundings/` 目录下初始化一个标准化的基金申请项目，包含完整的目录结构、章节骨架文件和项目 CLAUDE.md。

## 输出语言规范

全程使用中文。方法论术语、理论名称等专有名词可保留英文原文。

## Pipeline（六步流程）

### Step 1: 读取选题方案

**来源优先级（降级链）**：
1. 当前目录下 `fund-idea.md`（用户本地已有）
2. 用户显式指定的路径（如 `$ARGUMENTS` 传入）
3. `/fund-mine` 产出的 `_drafts/fund-idea_*.md`：
   ```bash
   DRAFTS_DIR="/Users/zylen/Library/CloudStorage/Dropbox/02-Research/fundings/_drafts"
   LATEST=$(ls -t "$DRAFTS_DIR"/fund-idea_*.md 2>/dev/null | head -1)
   if [ -n "$LATEST" ]; then
     echo "发现 fund-mine 最新产出: $LATEST"
     # AskUserQuestion 确认是否使用此文件（默认"是"）
   fi
   ```
4. 以上均无 → 使用 AskUserQuestion 逐项询问：
   - 基金类型（国自然/省基金/校级/其他）
   - 项目题目
   - 研究方向简述
   - 关联的源项目（可选）

命中 1/2/3 时，读取并提取：基金类型、拟题目、源项目列表、创新点、研究内容。

### Step 2: 项目基本信息确认

使用 AskUserQuestion 确认/补充以下信息：

```
请确认以下项目信息（从 fund-idea.md 读取的信息已预填，请修改或确认）：

1. 基金类型: {预填}
2. 基金名称（如"2026年度国家自然科学基金青年项目"）: {待填}
3. 项目题目: {预填}
4. 经费预算范围（万元）: {待填}
5. 研究期限（如 2027.01-2029.12）: {待填}
6. 申请人: {待填}
7. 依托单位: {待填}
```

记录为 `{FUND_INFO}`。

### Step 3: 创建项目目录

**项目创建位置**：`/Users/zylen/Library/CloudStorage/Dropbox/02-Research/fundings/`

**文件夹命名**：`{基金类型简称}_{年份}_{项目简称}`

命名示例：
- `nsfc_2026_供应链韧性` （国自然）
- `provincial_2026_数字化转型` （省基金）
- `university_2026_BIM协同` （校级）

基金类型简称映射：
- 国家自然科学基金 → `nsfc`
- 省自然科学基金 → `provincial`
- 校级科研基金 → `university`
- 其他 → 用户指定

创建目录结构（根据基金类型选择对应模板）：

#### 国自然目录结构

```
{项目文件夹}/
├── CLAUDE.md                          ← 项目元信息 + 章节规划
├── fund-idea.md                       ← 选题方案（从 /fund-mine 复制或新建）
├── {项目简称}.bib                      ← 参考文献（与 paper-init 约定一致）
├── sections/                          ← 章节正文
│   ├── 01_立项依据.md
│   ├── 02_研究目标.md
│   ├── 03_研究内容.md
│   ├── 04_研究方案.md
│   ├── 05_创新点.md
│   ├── 06_可行性分析.md
│   ├── 07_研究基础.md
│   └── 08_经费预算.md
├── structure/                         ← 与通用 skill（lit-*、figure、latex-table）对齐的共享目录
│   ├── 0_global/
│   │   └── idea.md                    ← 从 fund-idea.md 复制，供 /lit-plan 读取
│   ├── 2_literature/                  ← /lit-plan、/lit-review 工作目录
│   └── figures_tables/
│       ├── figures/                   ← /figure 输出
│       └── tables.tex                 ← /latex-table 输出
└── attachments/                       ← 附件材料
    ├── CV/                            ← 简历
    └── support/                       ← 支撑材料
```

#### 省基金目录结构

```
{项目文件夹}/
├── CLAUDE.md
├── fund-idea.md
├── {项目简称}.bib
├── sections/
│   ├── 01_立项依据.md
│   ├── 02_研究目标与内容.md
│   ├── 03_研究方案.md
│   ├── 04_创新点与可行性.md
│   ├── 05_研究基础.md
│   └── 06_经费预算.md
├── structure/
│   ├── 0_global/
│   │   └── idea.md
│   ├── 2_literature/
│   └── figures_tables/
│       ├── figures/
│       └── tables.tex
└── attachments/
    ├── CV/
    └── support/
```

#### 校级基金目录结构

```
{项目文件夹}/
├── CLAUDE.md
├── fund-idea.md
├── {项目简称}.bib
├── sections/
│   ├── 01_立项依据与研究目标.md
│   ├── 02_研究内容与方案.md
│   ├── 03_创新点与可行性.md
│   └── 04_研究基础与经费.md
├── structure/
│   ├── 0_global/
│   │   └── idea.md
│   ├── 2_literature/
│   └── figures_tables/
│       ├── figures/
│       └── tables.tex
└── attachments/
```

### Step 3.5: 创建 LaTeX 骨架（可选，用户选择启用）

AskUserQuestion："是否初始化 LaTeX 骨架（main.tex + chapters/）？基金 md 写作与 LaTeX 编译可并行，正式提交时从 md 灌入 tex。"

若选"是"，按基金类型复制模板（**变量必须来自 Step 2 的 `{FUND_INFO}` 结果，主 agent 在执行此块前需 export 为 shell 变量**）：

```bash
# 前置：主 agent 需已 export 以下变量（值来自 Step 2）
: "${FUND_TYPE:?missing}"      # nsfc | provincial | university
: "${PROJECT_SLUG:?missing}"   # 英文简称，snake_case
: "${PROJECT_TITLE:?missing}"  # 中文题目
: "${APPLICANT:?missing}"      # 申请人姓名
: "${AFFILIATION:?missing}"    # 依托单位

TEMPLATE_DIR=~/.claude/skills/fund-init/templates

case "$FUND_TYPE" in
  nsfc)
    cp "$TEMPLATE_DIR/nsfc.tex.tmpl" main.tex
    CHAPTERS=(01_立项依据 02_研究目标 03_研究内容 04_研究方案 05_创新点 06_可行性分析 07_研究基础 08_经费预算)
    ;;
  provincial)
    cp "$TEMPLATE_DIR/provincial.tex.tmpl" main.tex
    CHAPTERS=(01_立项依据与研究意义 02_研究目标与内容 03_研究方案与技术路线 04_创新点 05_研究基础与工作条件)
    ;;
  university)
    cp "$TEMPLATE_DIR/university.tex.tmpl" main.tex
    CHAPTERS=(01_选题与研究意义 02_研究内容与方案 03_创新点 04_研究基础)
    ;;
  *)
    echo "✗ unknown FUND_TYPE: $FUND_TYPE"; exit 1
    ;;
esac
cp "$TEMPLATE_DIR/latexmkrc.tmpl" latexmkrc

# 替换占位符（perl 写法跨平台，避免 macOS/Linux sed -i 差异）
PROPOSAL_DATE=$(date +%Y-%m-%d)
for f in main.tex latexmkrc; do
  perl -pi -e "s/\\{PROJECT_SLUG\\}/$PROJECT_SLUG/g;   \
                s/\\{PROJECT_TITLE\\}/$PROJECT_TITLE/g; \
                s/\\{APPLICANT\\}/$APPLICANT/g;         \
                s/\\{AFFILIATION\\}/$AFFILIATION/g;     \
                s/\\{PROPOSAL_DATE\\}/$PROPOSAL_DATE/g" "$f"
done

# 创建 chapters/ 骨架（每个 .tex 是 \input 对象，内容后期从 sections/*.md 灌入）
mkdir -p chapters
for chap in "${CHAPTERS[@]}"; do
  cat > "chapters/${chap}.tex" <<EOF
% ${chap} — skeleton created by /fund-init
% 内容来源：sections/${chap}.md（由 /fund-draft 生成后灌入此处）
%
% TODO: /fund-draft 生成初稿后，从 sections/${chap}.md 复制内容替换本占位

\section{${chap#*_}}

\noindent (本节初稿待 \verb|/fund-draft| 生成)
EOF
done

echo "✓ LaTeX 骨架创建完成 — main.tex + ${#CHAPTERS[@]} 个 chapters/*.tex"
```

> **Bib 契约**：`{项目简称}.bib` 在项目根目录（与 paper-init 对齐），LaTeX 通过 `\addbibresource{{项目简称}.bib}` 加载。
>
> **图路径契约**：main.tex 已含 `\graphicspath{{structure/figures_tables/figures/}{figures_tables/figures/}{figures/}}`，与 figure skill 的产出目录对齐。
>
> **编译验证**：生成后运行 `latexmk -xelatex main.tex` 做空稿验证；失败记录到 build log，不阻断 init。

### Step 4: 生成项目 CLAUDE.md

在项目根目录生成 `CLAUDE.md`，内容模板：

```markdown
# {项目题目}

## 项目信息

- **基金类型**: {基金类型}
- **基金名称**: {基金名称}
- **项目题目**: {项目题目}
- **经费预算**: {预算} 万元
- **研究期限**: {起止时间}
- **申请人**: {申请人}
- **依托单位**: {单位}
- **创建日期**: {YYYY-MM-DD}
- **输出格式**: markdown

## 项目阶段

`init`

## 源项目关联

| 源项目 | 路径 | 贡献内容 |
|--------|------|----------|
| {项目编号} | {绝对路径} | {贡献说明} |
| {项目编号} | {绝对路径} | {贡献说明} |

## 章节规划

> 以下三个章节规划表**择一使用**，根据 `基金类型` 字段选择对应表格，删除其余两个。

### 国自然章节规划

| 章节 | 文件 | 目标字数 | 状态 |
|------|------|----------|------|
| 立项依据 | sections/01_立项依据.md | 3000-4000 | 待写 |
| 研究目标 | sections/02_研究目标.md | 500-800 | 待写 |
| 研究内容 | sections/03_研究内容.md | 2000-3000 | 待写 |
| 研究方案 | sections/04_研究方案.md | 2000-3000 | 待写 |
| 创新点 | sections/05_创新点.md | 500-800 | 待写 |
| 可行性分析 | sections/06_可行性分析.md | 1000-1500 | 待写 |
| 研究基础 | sections/07_研究基础.md | 1500-2000 | 待写 |
| 经费预算 | sections/08_经费预算.md | 500-800 | 待写 |

### 省基金章节规划

| 章节 | 文件 | 目标字数 | 状态 |
|------|------|----------|------|
| 立项依据 | sections/01_立项依据.md | 2000-3000 | 待写 |
| 研究目标与内容 | sections/02_研究目标与内容.md | 1500-2000 | 待写 |
| 研究方案 | sections/03_研究方案.md | 1500-2000 | 待写 |
| 创新点与可行性 | sections/04_创新点与可行性.md | 800-1200 | 待写 |
| 研究基础 | sections/05_研究基础.md | 1000-1500 | 待写 |
| 经费预算 | sections/06_经费预算.md | 300-500 | 待写 |

### 校级基金章节规划

| 章节 | 文件 | 目标字数 | 状态 |
|------|------|----------|------|
| 立项依据与研究目标 | sections/01_立项依据与研究目标.md | 1500-2000 | 待写 |
| 研究内容与方案 | sections/02_研究内容与方案.md | 1500-2000 | 待写 |
| 创新点与可行性 | sections/03_创新点与可行性.md | 500-800 | 待写 |
| 研究基础与经费 | sections/04_研究基础与经费.md | 800-1200 | 待写 |

## 源项目素材索引

{列出源项目中可直接复用的材料}

### 可复用素材

| 素材 | 来源 | 用途 |
|------|------|------|
| {素材描述} | {源项目路径/文件} | {对应章节} |

## 写作注意事项

- 基金申请书的叙事逻辑：问题重要性 → 现有研究不足 → 本项目如何填补 → 预期成果
- 创新点表述：避免空泛，要具体到方法/视角/数据层面
- 可行性论证：紧扣已有研究基础，展示"我能做"而非"该做"
- 参考文献：近 5 年文献占比 > 60%，体现前沿性
- 语言风格：学术严谨但不晦涩，逻辑链清晰
```

### Step 5: 生成章节骨架文件

为每个章节 md 文件写入初始骨架，内容包含：

```markdown
# {章节标题}

<!-- 目标字数: {字数范围} -->
<!-- 状态: 待写 -->

## 写作要点

{基于 fund-idea.md 和基金类型，列出该章节需要覆盖的 3-5 个要点}

## 源项目素材

{列出该章节可引用的源项目素材及路径}

---

<!-- 正文从此开始 -->
```

### Step 5.5: 初始化进度文件

在 `sections/` 目录下创建 `progress.md`，根据 CLAUDE.md 章节规划表初始化：

```markdown
# 基金申请书撰写进度

| 章节 | 状态 | 字数 | 最后更新 |
|:-----|:-----|:-----|:---------|
| {章节1} | 待开始 | — | — |
| {章节2} | 待开始 | — | — |
| ... | ... | ... | ... |
```

### Step 6: 复制/链接 fund-idea.md + 同步到 structure/0_global/idea.md

1. 如果 `fund-idea.md` 存在于其他位置，复制到项目根目录
2. 如果不存在，基于 Step 1-2 收集的信息生成一个精简版
3. **同步一份到 `structure/0_global/idea.md`**（供下游通用 skill /lit-plan 读取；与 papers 工作流的路径契约对齐）：

```bash
cp fund-idea.md structure/0_global/idea.md
```

> 说明：`fund-idea.md` 是基金项目的领域语义正本，`structure/0_global/idea.md` 是通用 skill 的路径契约副本。两者内容同步，任一修改后需 `cp` 刷新另一份（或未来增加 hook 自动同步）。

完成后输出项目结构概览：

```
项目已初始化:
  路径: /Users/zylen/Library/CloudStorage/Dropbox/02-Research/fundings/{项目文件夹}/
  基金类型: {类型}
  章节数: {N}
  关联源项目: {列表}

下一步建议:
  1. 运行 `/lit-plan` 补充文献（特别是中文文献）
  2. 文献就绪后运行 `/fund-outline` 生成各节大纲
```

## 注意事项

- **不修改源项目的任何文件**，只读取和引用
- `fundings/` 目录如果不存在，自动创建
- 项目文件夹命名避免特殊字符，使用下划线分隔
- CLAUDE.md 中的源项目路径必须使用绝对路径
- 章节骨架的写作要点应具体到该基金项目，不是泛泛的模板话
