---
description: "每日写作完整 workflow：源选择 → 主题/方向漏斗 → 思想锻造 → 长文撰写 → NB2 配图 → 站点部署 → 微信公众号草稿"
---

# /daily-write — 每日写作 Workflow

合并原 `/blog-draft` + `/wechat-publish` 完整工作流，从素材选源到公众号草稿一站式完成。对齐 academic-os-dashboard 的数据契约（`_writing/daily/{date}/runs/{runId}/`），dashboard 作为只读 viewer。

**输入语法**：
```
/daily-write [date=YYYY-MM-DD] [mode=lyrics|links|library] [from-phase=N] [skip-deploy] [skip-wechat]
```

| 参数 | 含义 |
|:-----|:-----|
| `date` | 写作日期，默认今天（Asia/Shanghai 时区） |
| `mode` | 源类型；省略时进入 Phase 1a 交互选择 |
| `from-phase` | 从某 phase 继续（resume），如 `from-phase=4` 跳过选题漏斗直接进入 draft |
| `skip-deploy` | 跳过 Phase 7 站点部署（写完到 Phase 6 停） |
| `skip-wechat` | 跳过 Phase 8-9 微信发布 |

---

## 与其他 skill 的边界

| skill | 关系 |
|:------|:-----|
| `/kb` | **完全独立**。本 skill `library` mode 直接读 KB 文件，**不调用 /kb** |
| `/web-access` | Phase 1b 的 `links` mode **调用** /web-access（基础设施 skill） |
| `/wechat-publish` | **保留为独立后置入口**——专门处理"已有 src/data/blog/{slug}.md，单独发微信"。本 skill Phase 8 的实现与 /wechat-publish 主体步骤对齐，**修改 wechat 协议时两边必须同步更新** |

---

## 路径常量

```
{Vault}         = /Users/zylen/Library/CloudStorage/Dropbox/Apps/Zylen's Obsidian/01-Zylen's repositories/2-Values
{Site}          = /Users/zylen/Library/CloudStorage/Dropbox/04-Coding/academic-site
{WechatAssets}  = /Users/zylen/Library/CloudStorage/Dropbox/04-Coding/wechat-assets

{DailyRoot}     = {Vault}/_writing/daily
{DailyDir}      = {DailyRoot}/{date}
{RunDir}        = {DailyDir}/runs/{runId}

{SiteBlogDir}     = {Site}/src/data/blog
{SitePublicBlog}  = {Site}/public/blog
{WechatBlogDir}   = {WechatAssets}/blog
```

---

## 三层目录性质（关键）

| 目录 | 性质 | 允许内容 |
|:-----|:-----|:---------|
| `{RunDir}/` | **工作区**——本 skill 的过程文件落点 | 草稿、bug audit、checklist、process notes、迭代历史；可保留多 run；publishable 与否都可放 |
| `{SiteBlogDir}/{slug}.md` | **发布区**——站点正本 | **必须 publish-clean**（无 process notes / "待下一轮确认" / Bug Cascade Audit / Context Card 等内部记号）；只在 Phase 6 写入 |
| `{WechatBlogDir}/{date}_{cat}_{title}/` | **永久归档区** | 图片副本 + md 副本，按时间排序 |

**铁律**：Phase 1-5 的所有迭代都在 `{RunDir}/drafts/blog-draft.md` 进行，**Phase 6 才把 publish-clean 版本写到 `{SiteBlogDir}/{slug}.md`**。绝不在选题/写作阶段污染发布区。

---

## Phase 0：准备 daily 目录

### 0.1 解析参数

```
date    = ${args.date || localDate("Asia/Shanghai")}     # YYYY-MM-DD
mode    = ${args.mode || "ask"}                           # lyrics | links | library | ask
fromPhase = ${args.fromPhase || 0}
runId   = "{HHMMSS}-{mode}-{4位hex}"                      # 例：200503-lyrics-43bd
```

### 0.2 创建目录结构

```bash
mkdir -p "{RunDir}/drafts" "{RunDir}/images" "{RunDir}/wechat"
```

### 0.3 写 run.json

```json
{
  "runId": "{runId}",
  "date": "{date}",
  "mode": "{mode}",
  "createdAt": "{ISO8601}",
  "phase": "0"
}
```

### 0.4 Resume 检测

如果 `fromPhase > 0`，跳到指定 phase。从 `{RunDir}/` 读取已有产物作为上下文：
- `topics.json` / `directions.json` / `selected.json` / `workflow.json`
- `drafts/blog-draft.md` / `drafts/blog-context-card.md`
- `images/image-manifest.json`

任何引用的前序产物缺失 → 报错并要求降低 fromPhase。

---

## ═══ Stage A：选题漏斗（对齐 dashboard）═══

## Phase 1a：Source Mode 决策（Decision Card）

如果 `mode != ask`，直接采用；否则向用户展示三选项：

```
## 今天的写作来源是？

  [1] lyrics  — 歌词解读（Eason 或其他）
  [2] links   — 外部素材（公众号文章 / 知乎 / 推文 / YouTube 等）
  [3] library — KB 已有素材（Obsidian 主题文件 + _mental-model + _writing-craft）
```

写入：`{RunDir}/request.json`
```json
{
  "date": "{date}",
  "mode": "{mode}",
  "rawInput": "{用户附加的描述/链接/歌曲名}"
}
```

---

## Phase 1b：Source Pack 准备

按 mode 分支取材，统一打包到 `{DailyDir}/source-pack.json`（**注意**：source-pack 在 daily 层共享，不在 run 层；同一天多个 run 复用）。

### 1b.A — `lyrics` mode

1. 用户提供歌曲名 / 歌手 / 完整歌词（**必须完整**，不能只有 chorus）
2. 优先从 `{Vault}/Eason.md` 检索；缺失则向用户索要完整歌词
3. 同步读两个系统文件：
   - `{Vault}/_mental-model.md`
   - `{Vault}/_writing-craft.md`
4. 提取相关 Obsidian 主题文件（按歌曲主题，1-3 个）

### 1b.B — `links` mode

1. 用户提供链接列表
2. 调用 `/web-access` skill 抓取每条链接的正文（按 web-access 现有契约：WebFetch 优先，失败升级 CDP）
3. 抓取失败的链接报告给用户，让用户决定是否继续
4. 同步读 `_mental-model.md` + `_writing-craft.md`

### 1b.C — `library` mode

1. 询问用户主题关键词（如"任我行" / "陀飞轮" / "存在主义" / "AI 时代"）
2. **直接读 Obsidian 文件**（不调用 /kb）：
   - `_mental-model.md` + `_writing-craft.md`（必读）
   - 按主题相关性读 1-3 个主题文件（核心素材文件清单见下表）
   - 必要时读辅助素材（如 `04-fun/马拉松训练知识.md`）

| 文件 | 主题覆盖 |
|:-----|:---------|
| `Eason.md` | 夕阳无限好、任我行、与我常在、陀飞轮 |
| `人生哲学.md` | 顶层设计、存在主义、认知与智慧、健康、生活品质 |
| `心态与行动力.md` | 行动力、自信、边界与拒绝 |
| `事业与科研.md` | 工作哲学、Ikigai、教育、科研、AI 时代 |
| `人际与亲密关系.md` | 人际原则、社交、亲密关系、性格 |
| `注意力与专注.md` | 注意力管理、信息断舍离 |
| `投资与消费.md` | 金钱观、消费主义、投资方法论 |
| `新技术与AI.md` | AI 能力分层、Claude Code、知识管理 |

### Source Pack 写出格式

```json
{
  "date": "{date}",
  "mode": "{mode}",
  "rawInput": "...",
  "items": [
    {"type": "lyrics", "song": "任我行", "lyricsText": "..."},
    {"type": "vault-file", "path": "{Vault}/Eason.md", "excerpts": [...]},
    {"type": "vault-system", "path": "{Vault}/_mental-model.md", "summary": "..."},
    {"type": "external-link", "url": "...", "extractedText": "..."}
  ]
}
```

**素材使用约定**（写作阶段必须遵守）：
- 主题文件中 `**思考：**` 段是 Zylen 最个人化的反思——**最高优先级**
- `**来源：** Zylen` 的原创章节优先于他人观点
- `> 引用块` 中的金句适合作"钉子"
- 每篇文章至少深度使用 5 条以上知识库素材

---

## Phase 1c：抽 Topics（候选主题）

读 `source-pack.json`，从中提取 **5-8 个候选主题**。

每个 topic 包含：
- `id`：snake-case slug
- `title`：中文主题名
- `kernel`：1 句话核心命题
- `sourcePointers`：[]（指向 source-pack 中的素材索引）
- `tensionScore`：1-5 分（基于 _mental-model.md §六「内在张力」的契合度）

写出：
- `{RunDir}/topics.json`
- `{RunDir}/topics.md`（人类可读版）

向用户展示 topics.md，要求选 1 个深挖（也可选多个或要求重新生成）。

**Decision Card 1**：用户选 topic 后才进入 Phase 1d。

---

## Phase 1d：每 Topic 深挖 3 Directions

对用户选定的 topic，**生成 3 个写作方向**，必须有实质差异（不是换个标题，而是不同的论证路径 / 不同的情感基调 / 不同的读者收获）。

每个 direction 字段（与 dashboard `directions.json` 对齐）：

```json
{
  "id": "kebab-case-slug",
  "title": "完整中文标题",
  "angle": "切入角度描述（哲学思辨 / 挑衅型 / 叙事型 ...）",
  "hook": "开头第一句话（必须制造认知冲突：反直觉断言 / 具体画面 / 灵魂拷问）",
  "logicChain": ["论点1", "论点2", "论点3", "收尾余味"],
  "keyQuote": "核心金句预设",
  "personalAnchor": "会在哪个环节接入 Zylen 的个人经历",
  "nextPrompt": "下一步执行提示（用户选定后注入 Phase 2）"
}
```

写出：
- `{RunDir}/directions.json`
- `{RunDir}/directions.md`

**写作方案设计要求**（来自 `_writing-craft.md`）：
- 开头必须制造认知冲突（**禁用**"在这个快节奏的时代"这种烂大街开头）
- 逻辑链至少穿透三层（现象 → 原因 → 结构性洞察）
- 标明哪些环节会用到个人经历做锚点
- 三个方向之间的差异必须实质化，不是"严肃版 / 调侃版"这种换风格

---

## Phase 1e：选 Direction（Decision Card）

向用户展示 3 个 directions（拼接 topics.md + directions.md），用户选 1 个或要求混搭。

派生字段（用 writing-daily.cjs 的同款 inferCategory/inferTags 逻辑）：

```js
slug = slugify(direction.id)
topic_id = `${slug}-${date}-${4位hex}`
category = inferCategory(direction)   // 夕阳随笔 / 词间散记 / 求索手记
tags     = inferTags(direction)        // 最多 6 个
```

写出：
- `{RunDir}/selected.json`：用户选定的 direction id + 完整对象
- `{RunDir}/selected-direction.json`：扁平化的派生字段（slug / topic_id / category / tags / hook / angle / logicChain）
- `{RunDir}/workflow.json`：后续 phase 的配置（skip-deploy / skip-wechat 等）

---

## ═══ Stage B：写作核心 ═══

## Phase 2：Personal Anchors（个人锚点采集）

> **为什么需要这一步**：第一版文章最常见的问题是"缺少作者的血肉"——KB 素材 + AI 推演写出来的东西正确但缺少温度。用户的个人经历往往在看到 direction 后才会被激发，所以必须在开写前主动采集。

向用户提三问（如初始请求或 direction 讨论中已涉及，跳过已答的，只补问未覆盖的）：

```
## 个人锚点采集

direction 选定了，开写之前我需要你的"血肉"——

1. **这个主题让你想到自己哪段经历？**
   （不需要完整故事，几句话就行。比如某个场景、某个阶段、某次对话）

2. **你对这个主题最私人的感受是什么？**
   （不是"道理上我认为"，而是"我真实感受到的"。可以是矛盾的、说不清的）

3. **有没有哪句歌词/哪个观点是你反复想过的？**
   （帮我识别你最在意的着力点，写的时候会在这里加重笔墨）

可以只答一个，也可以三个都答。答得越具体，文章越有你的味道。
```

**用户回答处理**：
- 整理为具体写作锚点（场景 / 时间 / 细节）
- 确定每个锚点在逻辑链中的嵌入位置
- 涉及亲密关系的内容**用第二人称泛化处理**（参见全局隐私红线）
- 没有相关经历可分享 → 标注"本篇无个人锚点，用 KB 素材 + 假设场景"

写入：`{RunDir}/drafts/blog-context-card.md` 的 `## Personal Anchors` 段。

---

## Phase 3：Deep-Forging（思想锻造）

> **为什么**：单次 LLM 调用产出"正确但可预测"的分析。真正有穿透力的洞察需要观点碰撞——多视角互相否定后在张力交叉点产出新东西。

### 3.1 识别 3-4 个深度锚点

从 selected direction 的 logicChain 中提取需要"穿透三层"的核心论点。选择标准：
- 标注了"个人锚点"或"结构性洞察"的位置
- 容易写成"正确但平庸"的观点
- 与 `_mental-model.md §六 内在张力` 共鸣的主题

每个锚点描述为：「{主题} 的深层问题是 {问题}」

### 3.2 双 sub-agent 并行碰撞

对每个深度锚点，**并行**启动两个 subagent（`subagent_type: general-purpose, model: sonnet`，**不传 isolation 参数**）：

**Challenger Agent（Devil's Advocate）**
- 站常识 / 主流立场，论证"为什么大多数人的看法是对的"
- 用真实有说服力的论据，**不是稻草人**
- Zylen 读了会觉得"嗯，这话有道理，不好反驳"
- 产出：200-300 字论证 + 1 句最强论据

**Deep-Diver Agent**
- 站 Zylen 立场（基于 `_mental-model.md`），把观点推到逻辑极限
- 连续追问三次"所以呢？这跟我有什么关系？为什么这很重要？"
- 撞到一个**意想不到的结论**
- 产出：200-300 字纵深推演 + 1 句极限结论

每个 prompt 必含：当前锚点描述 / 相关 source-pack 摘录 / `_mental-model.md` 对应张力 / 写作风格要求。

### 3.3 主 agent 合成

读两个 sub-agent 产出，找张力交叉点，合成三层递进：
1. **现象层**（挑战者的"大多数人这么想"）
2. **原因层**（纵深者的"但其实..."）
3. **结构性洞察**（合成的"真正的问题是..."）

每个锚点的锻造笔记格式：
```
### 锚点 {N}：{主题}

**挑战者最强论据：** {1-2 句}
**纵深者极限推论：** {1-2 句}

**锻造洞察（三层递进）：**
第一层（现象）：{大多数人看到的}
第二层（原因）：{背后的机制}
第三层（结构性洞察）：{意想不到的结论}

**可用金句：** 「{一句话}」
```

写入 `{RunDir}/drafts/blog-context-card.md` 的 `## Deep-Forging` 段。

### 3.4 用户确认

展示 3-4 个锚点的锻造笔记，用户可：
- 接受全部 → 进入 Phase 4
- 指定新方向碰撞（"这个点应该从 XX 角度切入"）
- 重新锻造（换一组 sub-agent 再跑）
- 提供自己的洞察替换（**用户思考永远优先**）

### 3.5 成本节奏

3-4 锚点 × 2 agent = 6-8 次并行 sub-agent 调用，耗时 ≈ 单 agent。每个 agent 只输出 200-300 字。一篇 3000 字文章中，3-4 处锻造洞察对应每 700-1000 字一个深度爆点。

---

## Phase 4：Draft 撰写（Write Gate）

写到 `{RunDir}/drafts/blog-draft.md`（**不**写 `{SiteBlogDir}`）。

### 4.1 写作要求

- **字数**：3000-3500 字，不少于 3000
- **深度**：论证至少穿透三层；至少 3 处使用 Phase 3 的锻造洞察作"深度爆点"
- **KB 深度融入**：至少深度使用 5 条以上 KB 素材；**素材是骨骼不是装饰**
- **歌词密度**（词间散记必须）：至少 5 处不同歌词段落独立引用 + 解读，每处后跟 2-3 段基于歌词的分析
- **风格**：第一人称 / 哲学思辨 + 生活化案例 / 长短句交错 / 思想锐度 / 段落不冗长
- **结构**：开头制造认知冲突 / 中间每 500 字一个钩子 / 结尾留余味或反转
- **格式**：markdown，`##` 和 `###` 分节，`>` 引用歌词/名言，`**` 加粗关键概念

### 4.2 禁忌（硬约束）

- ❌ AI 味"总分总"八股文
- ❌ 每段结尾总结一遍
- ❌ 堆砌名人名言
- ❌ **歌词/诗句/名言宁缺勿错**——sub-agent 输出的具体引用必须核实（让用户确认 / web-search 查原文 / 从 Eason.md 检索），不能直接照抄
- ❌ **隐私红线**：详见全局约束 §隐私红线

### 4.3 草稿组装

`{RunDir}/drafts/blog-draft.md` 的结构：

```markdown
---
title: "{完整标题}"
date: "{date}"
tags: [...]
category: "{夕阳随笔 | 词间散记 | 求索手记}"
summary: "{1-2 句}"
cover: "/academic-site/blog/{slug}.png"
topic_id: "{topic_id}"
---

*阅读时间：约 {N} 分钟 · {字数} 字*

{正文}
```

阅读时间计算：正文汉字数 ÷ 500，向上取整。

### 4.4 sidecar：blog-context-card.md

所有 process notes / hook 候选 / bug audit / 风险检查 / 缺素材记录 → 写到 `{RunDir}/drafts/blog-context-card.md`，**绝不混入 blog-draft.md**。

### 4.5 Write Gate

向用户展示草稿（**完整正文**，不是前 500 字——用户需要全文才能给反馈）+ 字数统计 + 引用了哪些 KB 素材。

用户审阅后选项：
- [1] 接受 → 进入 Phase 5
- [2] 指定段落修改 → 改完再展示
- [3] 全部重写（保留方向，换风格/重组）
- [4] 回退到 Phase 3 重新锻造某个锚点

---

## Phase 5：配图（Write Gate）

### 5.1 image-plan.md

按文章 `##` 大节结构设计图片位置：1 张封面 + 4-5 张插图 = 5-6 张总。

| 用途 | 尺寸 | 说明 |
|:-----|:-----|:-----|
| 封面图 | 900×383px（2.35:1） | 公众号封面大图规范 |
| 正文配图 | 900×500px（9:5） | 公众号正文最佳显示 |

写入：`{RunDir}/images/image-plan.md`，每张图含：filename / position / prompt / 用途说明。

### 5.2 风格签名（每个 prompt 必须包含）

```
sophisticated graphic novel illustration, confident ink linework with watercolor washes,
style reference: European BD meets Taniguchi Jiro — clean lines, atmospheric depth, literary sensibility.
No text.
```

**配色随板块变化**：

| 板块 | 配色关键词 |
|:-----|:-----------|
| 夕阳随笔 | warm amber, burnt sienna, soft indigo twilight |
| 词间散记 | muted teal, warm gold, soft paper texture tones |
| 求索手记 | cool steel blue, warm grey, crisp morning light tones |

### 5.3 NB2 调用（chat completions 接口）

```bash
source ~/.claude/scheduled/email-config.sh
cd "{Site}"
BASE="public/blog"

generate_nb2_image() {
  local output_path="$1"; local prompt="$2"
  SAFE_PROMPT=$(echo "$prompt" | jq -Rs .)
  curl -s -X POST "https://api.chatanywhere.tech/v1/chat/completions" \
    -H "Authorization: Bearer $CHATANYWHERE_API_KEY" \
    -H "Content-Type: application/json" \
    -d "{\"model\":\"gemini-3.1-flash-image-preview\",\"messages\":[{\"role\":\"user\",\"content\":$SAFE_PROMPT}]}" \
    | python3 -c "
import sys, json, base64, re
d = json.load(sys.stdin)
content = d['choices'][0]['message']['content']
match = re.search(r'data:image/[^;]+;base64,([A-Za-z0-9+/=\n]+)', content)
if match:
    img_data = base64.b64decode(match.group(1))
    with open('$output_path', 'wb') as f:
        f.write(img_data)
    print(f'Saved: $output_path ({len(img_data)} bytes)')
else:
    print('ERROR: no image in response')
"
}

# 必须串行（每张 60-90 秒，并行触发 ChatAnywhere 限流）
generate_nb2_image "$BASE/{slug}.png" "{cover_prompt}"
generate_nb2_image "$BASE/{slug}-01.png" "{prompt1}"
# ...
```

**铁律**：禁止 `run_in_background` 并行多张图——会大批超时。

### 5.4 sips 裁剪（先等比缩放再裁剪）

```bash
# 封面 900×383
sips --resampleWidth 900 "$BASE/{slug}.png" --out "$BASE/{slug}.png"
sips --cropToHeightWidth 383 900 "$BASE/{slug}.png" --out "$BASE/{slug}.png"

# 正文配图 900×500
sips --resampleWidth 900 "$BASE/{slug}-01.png" --out "$BASE/{slug}-01.png"
sips --cropToHeightWidth 500 900 "$BASE/{slug}-01.png" --out "$BASE/{slug}-01.png"
```

**禁用 `sips -z`**：那是强制缩放会变形。

### 5.5 image-manifest.json

```json
{
  "topic_id": "{topic_id}",
  "slug": "{slug}",
  "cover": {"path": "public/blog/{slug}.png", "size": "900x383", "prompt": "..."},
  "inline": [
    {"path": "public/blog/{slug}-01.png", "afterHeading": "## ...", "prompt": "..."}
  ]
}
```

写入：`{RunDir}/images/image-manifest.json`。

### 5.6 失败回退

| 失败 | 处理 |
|:-----|:-----|
| NB2 接口失败 | 重试 1 次；仍失败 → 询问是否回退 DALL-E 3（images/generations 接口）；再失败 → 跳过该图，继续其他 |
| 返回内容无 base64 | 检查 response content；空则换 prompt 措辞重试 |
| `public/blog/` 不存在 | 自动创建 |

### 5.7 把图片引用插入草稿

更新 `{RunDir}/drafts/blog-draft.md`，在每个 `##` 大节后插入：

```markdown
![](/academic-site/blog/{slug}-NN.png)
```

确保图片独占段落（前后空行）。

---

## ═══ Stage C：发布双轨 ═══

## Phase 6：Site 预览 + Iterate

### 6.1 Publish-Clean Scan

扫描 `{RunDir}/drafts/blog-draft.md`，**禁止以下记号进入发布版**：

| 记号 |
|:-----|
| 待下一轮确认 |
| Bug Cascade Audit |
| FAIL-BLOCKED |
| Context Card |
| 是否仍需用户确认 |
| 开头候选 / 候选开头 |
| 内部 checklist |
| 内部审计 / 发布前审计 |
| Subagent Run Board |

**任一命中 → 拒绝写入 `{SiteBlogDir}`，列出污染位置，要求清理后再来**。

### 6.2 写发布版

通过扫描后，把 publish-clean 的内容写到：

```
{SiteBlogDir}/{slug}.md
```

同时保留 `{RunDir}/drafts/blog-draft.md` 作为工作版（不删除，便于未来 resume / 比对）。

写出：`{RunDir}/drafts/site-preview.md`（snapshot 版本，等同于 `{SiteBlogDir}/{slug}.md`）。

### 6.3 用户审阅完整正文

向用户展示：
1. 完整正文（不是摘要）
2. 图片渲染路径
3. 字数 / 阅读时间 / 引用 KB 素材数

询问：
- 哪里需要调整？
- 有没有要补充的个人经历或感受？
- 歌词/KB 素材使用是否到位？

### 6.4 迭代修改

迭代发生在 `{RunDir}/drafts/blog-draft.md`，每轮后**重新做 6.1 publish-clean scan + 6.2 写出**。

**典型迭代**：补充个人经历 / 增加歌词独立解读 / 替换空泛段落用具体 KB 素材 / 精修语气。

迭代 1-2 轮后，用户说"OK"才进入 Phase 7。

---

## Phase 7：Site Deploy（A-level External Action Gate）

### 7.1 External Action Gate

向用户展示**显式授权请求**：

```
⚠️ Site Deploy External Action

target: github.com/zylen97/academic-site (gh-pages branch)
action: npm run build + npx gh-pages -d dist --dotfiles
artifacts: dist/ 全量推送（含 _astro/ + .nojekyll）
回滚: 上次成功 commit 的 SHA={...}

授权短语：必须输入 "deploy site" 才执行（"ok" / "继续" 不算授权）
```

`--skip-deploy` 参数可跳过此 phase。

### 7.2 执行

```bash
cd "{Site}"
npm run build
npx gh-pages -d dist --dotfiles
```

> **铁律**：必须加 `--dotfiles`，否则 `public/.nojekyll` 不会被推送，GitHub Jekyll 会吞掉 `_astro/` 导致 CSS 404（已踩坑）。

### 7.3 写入 site-sync-checklist.md

```markdown
# Site Sync Checklist

- [x] publish-clean scan passed
- [x] {SiteBlogDir}/{slug}.md written
- [x] images in public/blog/ (cover + N inline)
- [x] npm run build succeeded
- [x] gh-pages -d dist --dotfiles deployed
- [ ] 验证线上 URL 可访问（用户手动验证）
```

写入：`{RunDir}/drafts/site-sync-checklist.md`。

---

## Phase 8：WeChat Publish（A-level External Action Gate）

> **协议同步声明**：本 phase 与 `/wechat-publish` SKILL.md 主体步骤对齐。修改 wechat 协议时（标题/摘要长度变化、API 路径变化、HTML 转换规则变化等）**两个 skill 必须同步更新**，避免行为漂移。

`--skip-wechat` 参数可跳过此 phase。

### 8.1 凭证 + 板块确认

```bash
source ~/.claude/scheduled/email-config.sh   # WECHAT_APPID + WECHAT_APPSECRET
```

板块确认（基于 frontmatter `category` 或 `tags` 推断；不确定时问用户）：

| 板块 | tags 关键词 |
|:-----|:-----------|
| 夕阳随笔 | 人生哲学, 存在主义, 心态, 注意力 |
| 词间散记 | Eason, 林夕, 歌词 |
| 求索手记 | 科研, 学术, Ikigai, AI, 技术 |

### 8.2 标题 + 摘要（关键长度限制）

> **个人订阅号 API 硬限制**：
> - 标题 ≤ **10 个汉字**（30 bytes）。超限返回 `45003 title size out of limit`
> - 摘要 ≤ **15 个汉字**。超限返回 `45004 description size out of limit`
> - 这比公众号后台手动编辑严格

```
## 公众号标题/摘要确认

博客原标题：{title}
公众号标题候选（≤10 字）：
  [A] {候选 1}
  [B] {候选 2}
  [C] {候选 3}

摘要候选（≤15 字）：
  [A] {候选 1}
  [B] {候选 2}

板块：{夕阳随笔 / 词间散记 / 求索手记}
```

用户确认后写到：`{RunDir}/wechat/wechat-checklist.md`。

### 8.3 archive 到 wechat-assets

```bash
BLOG_MD="{SiteBlogDir}/{slug}.md"
CATEGORY=$(grep '^category:' "$BLOG_MD" | sed 's|category: *"||;s|"$||')
TITLE=$(grep '^title:' "$BLOG_MD" | sed 's|title: *"||;s|"$||')
DATE=$(grep '^date:' "$BLOG_MD" | sed 's|date: *"||;s|"$||')
FOLDER="${DATE}_${CATEGORY}_${TITLE}"

ASSETS="{WechatBlogDir}/$FOLDER"
mkdir -p "$ASSETS"

# 按 md 中实际引用的图片路径 cp（不要用 {slug}* glob，文件名可能不匹配）
for img in $(grep -o '/academic-site/blog/[^)]*' "$BLOG_MD" | sed 's|/academic-site/blog/||'); do
  cp "{Site}/public/blog/$img" "$ASSETS/" 2>/dev/null
done
# 封面图
cover=$(grep '^cover:' "$BLOG_MD" | sed 's|cover: "/academic-site/blog/||;s|"||g')
[ -n "$cover" ] && cp "{Site}/public/blog/$cover" "$ASSETS/" 2>/dev/null
# 博客 md
cp "$BLOG_MD" "$ASSETS/"
```

### 8.4 图片压缩（≤1MB）

```bash
mkdir -p /tmp/wechat-upload
sips -s format jpeg -s formatOptions 60 "{Site}/public/blog/{name}.png" --out "/tmp/wechat-upload/{name}.jpg"
```

仍 >1MB → 降到 quality 40 重试。

### 8.5 上传封面（永久素材，External Action Gate）

```
⚠️ WeChat Upload External Action

target: api.weixin.qq.com/cgi-bin/material/add_material (永久素材)
action: 上传 1 张封面图 → 获得 thumb_media_id
remote leftover: 永久素材占用账户配额（5000 张上限）

授权短语：必须输入 "upload wechat assets"
```

```bash
curl -s -X POST \
  "https://api.weixin.qq.com/cgi-bin/material/add_material?access_token={TOKEN}&type=image" \
  -F "media=@/tmp/wechat-upload/{cover}.jpg"
```

### 8.6 上传正文图片

```bash
curl -s -X POST \
  "https://api.weixin.qq.com/cgi-bin/media/uploadimg?access_token={TOKEN}" \
  -F "media=@/tmp/wechat-upload/{name}.jpg"
```

返回 `{"url": "https://mmbiz.qpic.cn/..."}` → 替换到 HTML。

### 8.7 Markdown → 微信 HTML

阅读时间行专属样式（不走斜体规则）：
```html
<p style="font-size:13px;color:#999;margin:0 0 24px;text-align:center;">阅读时间：约 {N} 分钟 · {字数} 字</p>
```

转换规则（**必须 inline CSS**，无外部样式表）：

| Markdown | HTML |
|:---------|:-----|
| `## 标题` | `<h2 style="font-size:20px;font-weight:600;color:#191918;margin:32px 0 12px;border-left:4px solid #C9714E;padding-left:12px;">{text}</h2>` |
| `### 标题` | `<h3 style="font-size:17px;font-weight:600;color:#191918;margin:24px 0 8px;">{text}</h3>` |
| 段落 | `<p style="font-size:15px;line-height:2;color:#3b3b3b;margin:12px 0;text-align:justify;">{text}</p>` |
| `> 引用` | `<blockquote style="border-left:3px solid #C9714E;padding:8px 16px;margin:16px 0;color:#888;font-style:italic;font-size:15px;line-height:1.8;">{text}</blockquote>`。**多行连续 `> ` 合并为同一 `<blockquote>`**，行间用 `<br>` |
| `**加粗**` | `<strong style="color:#191918;">{text}</strong>` |
| `*斜体*` | `<em>{text}</em>`（**例外**：`*阅读时间：` 走专属样式） |
| `- 列表项` | 连续 `- ` 行合并为一个 `<ul>`：`<ul style="padding-left:1.5em;margin:12px 0;"><li style="font-size:15px;line-height:2;color:#3b3b3b;">...</li></ul>` |
| `1. 列表项` | 连续 `N. ` 行合并为 `<ol>`，同上 |
| `` `code` `` | `<code style="background:#f5f5f5;padding:2px 6px;border-radius:4px;font-size:14px;">{text}</code>` |
| 围栏代码块 | `<pre style="background:#f5f5f5;padding:16px;border-radius:8px;overflow-x:auto;font-size:14px;line-height:1.6;margin:16px 0;"><code>{code}</code></pre>` |
| `![](url)` | `<p style="text-align:center;margin:24px 0;"><img src="{wechat_cdn_url}" style="max-width:100%;border-radius:12px;" /></p>` |

注意：
- 图片 URL **必须替换为 8.6 上传后的 mmbiz.qpic.cn URL**
- `<p>` 间空行由 margin 控制，不要 `<br>`
- 列表/引用按 block 为单位转换（连续同类行属于同一 block）

写出：`{RunDir}/wechat/wechat-draft.md`（含 inline HTML 完整内容）。

### 8.8 推送草稿（External Action Gate）

```
⚠️ WeChat Draft Creation External Action

target: api.weixin.qq.com/cgi-bin/draft/add
action: 创建一篇草稿
title: {≤10 字标题}
digest: {≤15 字摘要}
remote leftover: 草稿留在公众号后台草稿箱（不自动发布，需用户手动审核 + 发布）

授权短语：必须输入 "publish wechat draft"
```

```python
import requests, json

# 获取 access_token（有效期 7200 秒，每次推送前重新获取避免 40014 invalid access_token）
r = requests.get(f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={APPID}&secret={APPSECRET}")
token = r.json()["access_token"]

draft_data = {
    "articles": [{
        "title": "{≤10 字}",
        "author": "Zylen",
        "digest": "{≤15 字}",
        "content": "{inline HTML}",
        "thumb_media_id": "{封面 media_id}",
        "need_open_comment": 1,
        "only_fans_can_comment": 0,
    }]
}

# 关键：必须 ensure_ascii=False，否则中文变 \uXXXX 乱码
r = requests.post(
    f"https://api.weixin.qq.com/cgi-bin/draft/add?access_token={token}",
    data=json.dumps(draft_data, ensure_ascii=False).encode("utf-8"),
    headers={"Content-Type": "application/json; charset=utf-8"}
)
```

> **不要用 `json=draft_data`**——`requests` 默认 `ensure_ascii=True`，中文标题/正文全变 `\uXXXX`。

成功返回 `{"media_id": "..."}` → 草稿创建完成。

### 8.9 清理测试草稿（如有）

调试过程中产生的测试草稿，**单独 Decision Card 确认后才删**：

```
## Cleanup 候选

| media_id | title | created | 推断为测试 |
|:---------|:------|:--------|:----------|
| ... | 测试 | 1h 前 | ✓（标题"测试"） |

确认删除哪些？（生产草稿绝不出现在此列表）
```

```python
# 列出
r = requests.post(f"https://api.weixin.qq.com/cgi-bin/draft/batchget?access_token={token}",
                  json={"offset": 0, "count": 20, "no_content": 1})

# 删除（**用户确认每一项后才删**）
requests.post(f"https://api.weixin.qq.com/cgi-bin/draft/delete?access_token={token}",
              json={"media_id": "{id}"})
```

### 8.10 完成提示

```
## 公众号草稿推送成功

API 标题：{≤10 字}
摘要：{≤15 字}
封面：{thumb_media_id}
图片：{N} 张已上传 mmbiz CDN

→ 前往「微信公众号 → 草稿箱」预览发布
→ 后台可改标题（不受 API 10 字限）

发布后告诉我**最终标题**，进入 Phase 9 同步回博客。
```

---

## Phase 9：Title Back-sync

用户在公众号后台确认 / 修改标题并发布后，提供最终标题。

### 9.1 对比展示

```
博客原标题：{原标题}
公众号最终标题：{新标题}

是否同步博客 frontmatter title 字段？
  [1] 同步（更新 {SiteBlogDir}/{slug}.md 并触发 site redeploy）
  [2] 保持差异（博客长标题 / 公众号短标题）
  [3] 跳过
```

### 9.2 执行（用户选 [1]）

更新 `{SiteBlogDir}/{slug}.md` 的 frontmatter `title` 字段。

询问是否触发 site redeploy（A-level External Action Gate，复用 Phase 7 协议）。

> **原则**：公众号是标题的 source of truth，博客跟随同步。**正文内容两端一致**，不做差异化。

---

## 全局约束

### 隐私红线（**铁律**）

#### 不暴露作者感情/恋爱经历

- 工作经历 / 科研经历 / 性格自剖 → ✅ 可作为个人锚点
- 亲密关系场景 → **必须**用第二人称泛化处理（"你"视角）或假设场景
- 即使主题是亲密关系，也不能暗示"我经历过这些"

#### 不暴露作者工作强度/频次的具体量化细节

读者里有熟人（学生、同事、同行），会识别"卷度"。具体禁忌：

- ❌ 具体时间戳：凌晨 1 点 / 深夜 2 点 / 周末还在改 / 每天 12 小时
- ❌ 具体数量：几十个 skill / 18 个项目 / 10 篇论文 / N 门课
- ❌ 具体工具链清单：`/lit-plan` `/pen-outline` `/method-end` 这种暴露工作流细节
- ❌ 具体学术指标：一篇 SSCI / 某影响因子期刊 / 某专项基金
- ✅ 替代表达：一个深夜 / 前阵子 / 这段时间 / 一些 skill / 陆续搭了一些 / 一份成果 / 一篇论文（单数指代）

**判断标准**：如果熟人读到这句话能还原出作者的工作强度画像，就要改。抽象化程度要让"任何认真工作的人"都可能这样说。

### 引用核实

sub-agent（尤其是 Phase 3 Deep-Diver）输出里如果出现具体歌词 / 名人原话 / 具体引用：

- 必须核实：让用户确认 / web-search 查原文 / 从 Obsidian 原始素材检索
- **宁缺勿错**——没有合适的真实引用就不引用，让正文自己说话
- 幻觉的代价是作者公开出糗

### Phase 间 Resume 契约

每个 phase 完成后写 `{RunDir}/run.json` 的 `phase` 字段，记录进度。中断后用 `from-phase=N` 继续：

| from-phase | 前置必需 |
|:-----------|:--------|
| 1c | request.json + source-pack.json |
| 1d | topics.json |
| 1e | directions.json |
| 2  | selected-direction.json + workflow.json |
| 3  | drafts/blog-context-card.md（含 Personal Anchors） |
| 4  | drafts/blog-context-card.md（含 Deep-Forging） |
| 5  | drafts/blog-draft.md |
| 6  | images/image-manifest.json |
| 7  | {SiteBlogDir}/{slug}.md（publish-clean） |
| 8  | site deployed（如未 skip-deploy） |
| 9  | wechat draft created（用户已提供最终发布标题） |
| 9  | wechat draft created |

### 三层目录铁律

- 工作区污染允许：`{RunDir}/`（process notes / sidecar / 迭代历史）
- 发布区严控：`{SiteBlogDir}/{slug}.md` 必须 publish-clean
- 归档区永久：`{WechatBlogDir}/{date}_{cat}_{title}/`

### Dashboard 协作

dashboard `academic-os-dashboard` 读取 `{DailyRoot}/` 目录展示状态，**不写入**。本 skill 是唯一写入方。

### 边界条件

| 情况 | 处理 |
|:-----|:-----|
| Obsidian 素材不足 | 提示用户素材太少，建议先 `/kb ingest` 积累 |
| 主题与已有博客重复 | 询问扩写还是写新角度 |
| 歌词不完整 | 必须主动索要完整歌词，不接受片段 |
| `_mental-model.md` 不存在 | 跳过心智模型加载并建议 `/kb model` 生成 |
| `public/blog/` 不存在 | 自动创建 |
| Site renderer 不支持图片 | 提醒用户更新 `[slug].astro`，不自动改 |
| NB2 全部失败 | 询问是否回退 DALL-E 3；再失败询问是否跳过配图 |
| 微信 IP 白名单错误（40164） | 提取 IP，让用户到「微信开发者平台 → IP 白名单」添加，重试 |
| access_token 过期（40014） | 重新获取（每次推送前主动获取新 token） |
| 微信图片 >1MB | 降到 quality 40 重试 |
| Phase 6 publish-clean scan FAIL | 列出污染位置，**拒绝写发布区**，要求清理后再来 |
| 用户中断后再启动 | 用 `from-phase=N` 指定恢复点 |

### 踩坑记录

| 坑 | 现象 | 教训 |
|:---|:-----|:-----|
| NB2 并行限流 | 多张图并行 → ChatAnywhere 限流挂起 | **必须串行**，不要 `run_in_background` |
| `sips -z` 变形 | 强制缩放破坏比例 | 用 `--resampleWidth + --cropToHeightWidth` 两步走 |
| 第一版直接部署 | 半成品被公开访问 | Phase 6 必须迭代后用户确认 OK 才进 Phase 7 |
| 歌词只抓 chorus | 词间散记内容空洞 | 必须完整歌词 + 至少 5 处独立引用 |
| KB 素材浮于表面 | 文章像通用哲学散文 | KB 素材必须是论证支撑而非装饰，深用 5+ 条 |
| 第一版缺个人经历 | direction 选完直接写 | Phase 2 必须采集锚点 |
| `requests json=` 中文乱码 | 标题/正文全变 `\uXXXX` | 必须 `json.dumps(..., ensure_ascii=False).encode("utf-8")` + `data=` 参数 |
| WeChat 标题 11 字 | `45003 title size out of limit` | API 限制 ≤10 汉字，比后台严 |
| `--dotfiles` 缺失 | 部署后 CSS 404 | `npx gh-pages -d dist --dotfiles` 必加 |
| frontmatter 缺 cover | 公众号无封面 | Phase 5 必须生成封面图，frontmatter 必须含 `cover` |
| 把 process notes 写到 site | 发布版含 "Bug Cascade Audit" 等内部记号 | Phase 6.1 publish-clean scan 强制兜底 |
