---
description: "交互式构建叙述型章节的要点（论点 + citations），为 /draft 提供高质量输入"
---

# Outline Workflow — 交互式构建章节要点

为叙述型章节（Introduction, Literature Review, Discussion）逐子节构建要点（核心论点 + citation key），经用户确认后写入章节 md 文件。技术型章节不适用本技能。

**执行模式**：Form 1（单节）直接运行；Form 2（有子节的 section）逐个子节交互。

**输入** `$ARGUMENTS`：`section=XXX`（必须）。

## 步骤 0：前置准备

### 0.1 解析 `$ARGUMENTS`

- 提取 `section` 参数
- 无 `section` → AskUserQuestion 询问要为哪个 section 构建要点

### 0.2 获取项目文件路径

- 从 CLAUDE.md 获取主文件和 bib 文件路径
- Fallback：Glob("*.tex") 查找含 `\documentclass` 的文件（排除 supplementary/appendix/*.cls）
- 读取主文件了解论文结构

### 0.3 构建 Section Tree `{SECTION_TREE}`

- 正则 `\\(section|subsection|subsubsection)\{([^}]+)\}` 提取所有 section 命令（忽略 `*` 变体）
- 记录级别、标题、行号，构建父子关系树，记录 parent/children/siblings/preceding/following

### 0.4 Section 匹配与 Form 判定

将 `section=XXX` 在 `{SECTION_TREE}` 中匹配：

- **匹配规则**：先精确匹配，后模糊匹配（忽略大小写、"and"/"&"互换、冠词省略）
- **有子 section** → `{INPUT_FORM}` = "multi"，`{SPLIT_SEGMENTS}` = 子 section 列表
- **无子 section** → `{INPUT_FORM}` = "single"
- **匹配失败** → 列出 `{SECTION_TREE}` 中所有可用 section，AskUserQuestion 让用户选择

### 0.5 叙述型章节检查

判断匹配到的 section 所属顶层 section 是否为叙述型：

```
叙述型: Introduction, Literature review, Discussion
技术型: Model formulation, Equilibrium analysis, Numerical simulation
```

- **技术型** → 显示警告并退出：
  ```
  ⚠️ "{section title}" 属于技术型章节。
  /outline 仅适用于叙述型章节（Introduction, Literature Review, Discussion）。
  技术型章节的素材应直接在章节 md 的 "## 完整素材" 中编写。
  ```
- **Conclusion** → 显示提示并退出：Conclusion 无对应 md 文件，不适用 /outline。

### 0.6 自动解析源文件 `{SOURCE_FILES}`

从匹配到的 section 自动定位需要读取的素材文件：

**a. 定位章节 md 文件**：

1. 找到匹配 section 的**顶层父 section**（如 "Platform economics..." → 父 "Literature review"）
2. 扫描 `structure/` 子目录，用关键词匹配目录名：

```
section 关键词        → 目录
introduction         → structure/1_introduction/introduction.md
literature           → structure/2_literature/literature.md
discussion           → structure/6_discussion/discussion.md
```

3. 记录 `{CHAPTER_MD_PATH}`

**b. 定位 citation pool 文件**：

1. 读取 `{CHAPTER_MD_PATH}`
2. 查找底部 `## 引用池` 区块（或 `## Citation Pool`）
3. 解析该区块中列出的 citation pool 文件路径（格式如 `→ 见 \`2_literature/citation_pool/LR.md\``）
4. 构建完整路径列表 → `{CITATION_POOL_PATHS}`
5. 如无引用池区块 → `{CITATION_POOL_PATHS}` = 空列表，不报错

**c. 全局上下文**：

- 固定读取 `structure/0_global/idea.md` → `{IDEA_PATH}`

**d. 其他章节 md 扫描**（交叉参考）：

- 扫描 `structure/` 下所有章节 md 文件（排除当前章节）
- 对每个文件：检查 `## 大纲` 或 `## 完整素材` 下是否有实质内容（非 TODO/空）
- 有实质内容的文件 → `{OTHER_MD_PATHS}` 列表
- 读取时仅提取标题和要点（不读全文），避免上下文过长

## 步骤 1：读取并组装上下文

**动作**：

1. 读取 `{IDEA_PATH}` → `{IDEA_CONTEXT}`（idea.md 全文）
2. 读取 `{CHAPTER_MD_PATH}` → `{CHAPTER_MD_CONTENT}`（当前章节 md 全文）
3. 读取 `{CITATION_POOL_PATHS}` 中所有文件 → `{CITATION_POOL_CONTENT}`
4. 读取 `{OTHER_MD_PATHS}` 中的文件（仅标题和要点摘要）→ `{CROSS_REF_CONTEXT}`
5. 读取 bib 文件用于验证 citation key 存在性

显示已读取的文件列表：
```
📂 上下文已加载：
- 纲领: structure/0_global/idea.md
- 当前章节: {CHAPTER_MD_PATH}
- 引用池: {逐行列出}
- 交叉参考: {有内容的其他章节 md 列表}
```

## 步骤 1.5：Form 2 调度确认

`{INPUT_FORM}` = "single" → 跳过，直接执行步骤 2。

**1.5a 确认**：AskUserQuestion 显示：
- Parent section 名称
- 子节列表（编号）
- 将读取的源文件列表
- 预计交互：每个子节 2 轮确认（intent + 要点）

等待用户确认后开始循环。

**1.5b 循环处理**：
```
FOR i, child IN enumerate({SPLIT_SEGMENTS}):
  a. 设置 {CURRENT_TITLE} = child.title
  b. 从 {CHAPTER_MD_CONTENT} 按 heading 提取该子节已有内容：
     匹配规则：忽略编号前缀（如 "### 2.1 "），对标题部分做模糊匹配
  c. 显示 "▶ [{i+1}/{total}]: {CURRENT_TITLE}"
  d. 执行步骤 2（单子节交互流程）
  e. 显示 "✓ [{i+1}/{total}] done"
END FOR
```

完成后跳转步骤 3 汇总写入。

## 步骤 2：单子节交互流程

> Form 1 执行一次，Form 2 每个子 section 重复。

### 2.1 检查已有要点

从 `{CHAPTER_MD_CONTENT}` 中提取当前子节对应 heading 下的内容：

- **已有要点**（以 `- ` 开头的条目，且包含实质内容而非 TODO）→ 显示已有要点，AskUserQuestion：
  ```
  📋 该子节已有以下要点：
  {列出已有要点}

  选择操作：
  (1) 保留现有要点，跳过此子节
  (2) 在现有基础上补充/调整
  (3) 重新构建（覆盖）
  ```
  用户选 (1) → 跳过此子节，进入下一个
  用户选 (2) → 将已有要点作为起点，进入 2.2
  用户选 (3) → 忽略已有要点，进入 2.2

- **无要点或仅 TODO** → 直接进入 2.2

### 2.2 Intent 确认

基于以下信息生成该子节的一句话意图（概括这个子节要达成的论证目的）：

- idea.md 中的相关信息
- 章节 md 的 `## 必备元素` 中对应要求
- 章节 md 大纲中该子节的现有提示
- Section Tree 中的位置（前后关系）
- 其他章节 md 中的交叉参考信息

**输出格式**：
```
💡 子节 intent：
> {one-line intent}
```

AskUserQuestion：确认 intent 或提出修改意见。

**循环**：用户不满意 → 修改 intent → 再次展示 → 直到用户确认。

### 2.3 要点构建

基于已确认的 intent，结合所有上下文，生成要点列表：

**生成依据**：
- 已确认的 intent 作为目标导向
- idea.md 中的相关论点
- 章节 md 大纲中的现有提示（如有）
- citation pool 中的可用文献
- 交叉参考上下文（确保一致性）
- bib 文件验证 citation key 存在性

**要点写作规范**：
- 中文表述，citation key/专用术语/公式符号用英文原文
- 每个要点包含核心论点 + 对应的 `\citep{}` 或 `\citet{}`
- 需要引用但 citation pool 中找不到合适文献 → 标记 `(ref)`
- 同一要点引用不超过 3 处
- 如用户选了 (2) 补充模式，在已有要点基础上调整

**输出格式**：

```
### {subsection title}
> {confirmed intent}

- 要点1：论点内容 \citep{key1, key2}
- 要点2：论点内容 \citet{key3}
- 要点3：论点内容 (ref)
- ...

| # | Citation | 引用理由 |
|:-:|:---------|:---------|
| 1 | key1 | 为什么选这篇文献支撑该要点 |
| 2 | key2 | 为什么选这篇文献支撑该要点 |
| 3 | key3 | 为什么选这篇文献支撑该要点 |
```

AskUserQuestion：确认要点或提出修改意见（可以要求增删改某个要点、换引用、调整顺序等）。

**循环**：用户不满意 → 修改要点和引用理由表 → 再次展示 → 直到用户确认。

### 2.4 记录确认结果

将用户确认的要点（不含引用理由表）暂存，等待步骤 3 统一写入。

## 步骤 3：写入章节 md 文件

所有子节完成后（或 Form 1 的单节完成后），将确认的要点写入 `{CHAPTER_MD_PATH}`。

**写入规则**：

1. 读取 `{CHAPTER_MD_PATH}` 当前内容
2. 对每个已确认的子节：
   a. 定位 md 中对应的 heading（模糊匹配，忽略编号前缀）
   b. 替换该 heading 下的内容为：
   ```
   > {intent}

   - 要点1...
   - 要点2...
   ```
   c. 保留 heading 本身不变
3. 保留 `## 必备元素`、`## 引用池` 等非大纲区块不变
4. 仅修改 `## 大纲` 区块内的对应子 heading 内容

**写入确认**：写入前 AskUserQuestion 展示即将写入的内容摘要：
```
📝 即将写入 {CHAPTER_MD_PATH}：

### {subsection1}
> {intent1}
- {N1} 个要点

### {subsection2}
> {intent2}
- {N2} 个要点

确认写入？
```

用户确认 → 执行写入。用户拒绝 → 结束，不写入（要点已在对话中展示，用户可手动复制）。

## 步骤 4：完成提示

显示：
- ✅ 完成状态
- 📂 读取的源文件列表
- 📊 各子节要点数量汇总
- ⚠️ 标记 `(ref)` 的数量（提醒用户后续补充文献）
- 💡 提示：要点就绪后可运行 `/draft section=XXX` 生成初稿
