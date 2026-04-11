---
description: "从 Obsidian 价值观笔记生成深度长文博客 + DALL-E 配图，输出到 Academic Site"
---

# Blog Draft — 深度博客长文生成

从 Obsidian Vault 中的价值观/哲学笔记出发，生成 3000-5000 字的深度长文博客，配 DALL-E 3 封面图。

**输入**：主题关键词（如"任我行"、"陀飞轮"、"存在主义"）或指定 Obsidian 文件

---

## 步骤 1：素材采集

### 1.1 定位 Obsidian 源文件

素材目录：`/Users/zylen/Library/CloudStorage/Dropbox/Apps/Zylen's Obsidian/01-Zylen's repositories/2-Values/`

核心素材文件：

| 文件 | 主题覆盖 |
|:-----|:---------|
| `Eason.md` | 夕阳无限好、任我行、与我常在、陀飞轮 |
| `人生哲学.md` | 存在主义、体制化批判、意义自构建、废物哲学 |
| `事业与科研.md` | 陀飞轮×Ikigai、神圣预约、科研工作流 |
| `人际与亲密关系.md` | 与我常在、筛选哲学、适度冷漠 |
| `注意力与专注.md` | 注意力管理、信息断舍离 |
| `投资与消费.md` | 投资哲学、消费观 |

辅助素材：`/Users/zylen/Library/CloudStorage/Dropbox/Apps/Zylen's Obsidian/04-fun/马拉松训练知识.md`

### 1.2 读取相关内容

根据用户指定的主题，读取 1-3 个相关 Obsidian 文件。提取与主题直接相关的段落、引用、观点。

### 1.3 读取已有博客

读取 `src/data/blog/` 下所有已有博客的 frontmatter（标题、日期、标签），避免重复主题。如果是扩写已有博客，读取其完整内容作为基础。

---

## 步骤 2：与用户对齐

向用户展示：

```
## 博客素材概览

**主题**：{主题}
**素材来源**：{文件1} + {文件2}
**核心观点**：
1. {观点1}
2. {观点2}
3. {观点3}

**文章结构草案**：
1. {引子 — 用什么切入}
2. {展开1}
3. {展开2}
4. {升华/收尾}

**预计字数**：{3000-5000}字
**是否扩写已有博客**：{是/否}

确认后开始写作。
```

**用户确认后才继续。**

---

## 步骤 2.5：加载人格蒸馏

读取 `~/.claude/zylen-perspective.md`，加载 Zylen 的：
- 6 个核心心智模型（夕阳平常事、枷锁中的自由、体制化解构、意义自构建、反派思维、Ikigai×陀飞轮）
- 10 条决策启发式
- 表达 DNA（语言特征、文章风格、禁忌用语）
- 价值边界和内在张力

**写作时必须以 zylen-perspective 为"认知底座"**，确保文章是"Zylen 会写的"而非"AI 风格的"。

---

## 步骤 3：写作

### 3.1 写作要求

- **字数**：3000-5000 字，宁长勿短
- **深度**：不是素材搬运，是基于素材的深度思考和重新组织
- **风格**：
  - 第一人称，个人化表达
  - 哲学思辨 + 生活化案例
  - 可以引用歌词、哲学家观点、个人经历
  - 段落不宜过长，保持阅读节奏
  - 有思想锐度，敢于表达不主流的观点
- **结构**：
  - 开头：引人入胜的切入（歌词、场景、问题）
  - 中间：层层递进，每个 section 有独立观点
  - 结尾：不要鸡汤式总结，留有余味或反转
- **语言**：中文为主，歌词/术语可保留原文（粤语、英文、日文）
- **格式**：markdown，使用 `##` 和 `###` 分节，`>` 引用歌词/名言，`**` 加粗关键概念

### 3.2 禁忌

- 不要写成 AI 味的"总分总"八股文
- 不要每段结尾都总结一遍
- 不要堆砌名人名言，引用要精准且有机融入
- 不要泛泛而谈，要有具体的、个人化的洞察

---

## 步骤 4：生成封面图

用 ChatAnywhere API 调用 DALL-E 3 生成封面配图。

### 4.1 确定插图位置

按文章段落结构，在每个 `##` 大节之间插入一张图。通常一篇 3500 字的文章需要 **1 张封面 + 4-5 张插图**，共 5-6 张。

### 4.2 生成 prompt

为封面和每张插图分别生成英文图片描述 prompt，要求：

**固定要素（视觉签名）：**
- minimalist, ink wash watercolor style
- 抽象概念化（不要直白的图解），体现该段落的情感和意象
- 宽幅构图（1792x1024）
- 末尾加 "No text."

**配色随主题变（不锁死）：** 根据文章主题选择对应色调：

| 主题方向 | prompt 配色关键词 | 适用场景 |
|:---------|:-----------------|:---------|
| 哲学 / Eason / 自由 | warm amber, burnt orange, deep indigo tones | 任我行、夕阳平常事、存在主义 |
| 科研 / 博弈论 / 建模 | cool steel blue, silver grey, crisp white tones | 论文解读、方法论、前沿速递 |
| 跑步 / 运动 / 马拉松 | vibrant orange, fresh green, bright golden tones | 跑步感悟、运动哲学 |
| 生活感悟 / 日常 | soft blush pink, warm cream, gentle lavender tones | 日常随笔、注意力管理 |
| 批判 / 反体制 / 锐利观点 | deep charcoal, muted crimson, stark contrast tones | 体制化批判、反派思维 |

同一篇文章内所有图片使用相同配色，保持篇内一致性。不同文章之间配色可以不同。

### 4.3 并行调用 API

所有图片**并行生成**以节约时间：

```bash
API_KEY="$(grep CHATANYWHERE_API_KEY ~/.claude/scheduled/email-config.sh | cut -d= -f2 | tr -d '"')"
cd /Users/zylen/Library/CloudStorage/Dropbox/04-Coding/academic-site
BASE="public/blog"

generate_image() {
  local slug="$1"; local prompt="$2"
  local url=$(curl -s -X POST "https://api.chatanywhere.tech/v1/images/generations" \
    -H "Authorization: Bearer $API_KEY" \
    -H "Content-Type: application/json" \
    -d "{\"model\":\"dall-e-3\",\"prompt\":\"$prompt\",\"n\":1,\"size\":\"1792x1024\",\"quality\":\"standard\"}" \
    | python3 -c "import sys,json; print(json.load(sys.stdin)['data'][0]['url'])")
  curl -s -o "$BASE/$slug.png" "$url"
}

generate_image "{slug}" "{prompt1}" &
generate_image "{slug}-01" "{prompt2}" &
generate_image "{slug}-02" "{prompt3}" &
# ... 并行
wait
```

### 4.4 归档素材

图片生成完成后，归档到 wechat-assets 项目（Dropbox 同步，永久保存）：

```bash
ASSETS="/Users/zylen/Library/CloudStorage/Dropbox/04-Coding/wechat-assets/blog/{slug}"
mkdir -p "$ASSETS"
cp public/blog/{slug}*.png "$ASSETS/"
```

> **素材归档规范**：
> - 博客图片存两份：`public/blog/`（网站部署用）+ `wechat-assets/blog/{slug}/`（素材归档）
> - 公众号头像等非博客素材存 `wechat-assets/avatars/`
> - 素材归档目录：`/Users/zylen/Library/CloudStorage/Dropbox/04-Coding/wechat-assets/`

### 4.5 插入文章

在文章 markdown 对应位置插入图片引用：

```markdown
![](/academic-site/blog/{slug}-01.png)
```

确保每张图片独占一个段落（前后各有一个空行），渲染器才能正确识别。

### 4.6 成本控制

- 模型：`dall-e-3` standard quality
- 尺寸：`1792x1024`（封面宽幅）
- 预算：每篇文章 5-6 张 ≈ ¥1.5-2.0

---

## 步骤 5：组装输出

### 5.1 生成博客文件

写入：`src/data/blog/{slug}.md`

```markdown
---
title: "{标题}"
date: "{YYYY-MM-DD}"
tags: ["{tag1}", "{tag2}", "{tag3}"]
summary: "{1-2 句摘要}"
cover: "/academic-site/blog/{slug}.png"
---

*阅读时间：约 {N} 分钟 · {字数} 字*

{文章正文 markdown}
```

阅读时间计算：统计正文汉字数 ÷ 500（中文平均阅读速度），向上取整。放在 frontmatter 之后、正文第一行之前。

### 5.2 检查 blog 渲染器图片支持

读取 `src/pages/blog/[slug].astro` 的 `mdToHtml` 函数，检查是否支持：
- `![alt](url)` 图片语法
- 封面图片（从 frontmatter `cover` 字段读取）

如不支持，提示用户需要补充图片渲染逻辑（不自动修改）。

---

## 步骤 6：预览与部署

向用户展示：
1. 文章标题 + 字数统计
2. 封面图（展示图片路径）
3. 前 500 字预览

询问是否：
- 修改内容
- 重新生成封面图（换风格）
- 部署到 GitHub Pages

**用户确认后部署：**

```bash
cd /Users/zylen/Library/CloudStorage/Dropbox/04-Coding/academic-site
npm run build
npx gh-pages -d dist --dotfiles
```

> **注意**：必须加 `--dotfiles`，否则 `public/.nojekyll` 不会被推送，GitHub Jekyll 会吞掉 `_astro/` 目录导致 CSS 404。

---

## 边界条件

| 情况 | 处理 |
|:-----|:-----|
| Obsidian 素材不足 | 提示用户素材太少，建议先在 Obsidian 中积累再写 |
| 主题与已有博客重复 | 提示用户是扩写还是写新角度 |
| DALL-E API 失败 | 重试 1 次；仍失败则跳过配图，用文字占位 |
| 图片 URL 过期（24h） | 生成时立即下载到本地，不依赖远程 URL |
| `public/blog/` 目录不存在 | 自动创建 |
| 博客渲染器不支持图片 | 提醒用户需更新 `[slug].astro`，不自动修改 |
| `zylen-perspective.md` 不存在 | 跳过人格蒸馏，提醒用户文章可能缺少个人风格 |
