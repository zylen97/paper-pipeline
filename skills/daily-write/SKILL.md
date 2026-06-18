---
description: "每日写作完整 workflow：源选择 → 方向漏斗 → 思想锻造 → 长文撰写 → NB2 配图 → 站点部署 → 微信公众号草稿"
---

# /daily-write — 每日写作 Workflow

合并原 `/blog-draft` + `/wechat-publish` 完整工作流，从素材选源到公众号草稿一站式完成。本 skill 是 `_writing/daily/{date}/runs/{runId}/` 目录的唯一写入方（目录结构沿用早期 academic-os-dashboard 的设计，便于历史 run 复用）。

**输入语法**：
```
/daily-write [date=YYYY-MM-DD] [mode=lyrics|links|library] [from-phase=N] [runId=...] [direction-id=...] [skip-deploy] [skip-wechat]
```

| 参数 | 含义 |
|:-----|:-----|
| `date` | 写作日期，默认今天（Asia/Shanghai 时区） |
| `mode` | 源类型；省略时进入 Phase 1a 交互选择 |
| `from-phase` | 从某 phase 继续（resume），如 `from-phase=4` 跳过选题漏斗直接进入 draft |
| `runId` | 指定 runId（resume 已有 run，或多 direction 分治时给同 daily 下不同 run 命名） |
| `direction-id` | 从 directions-backlog.md 复活某个未写的 direction，配合 `from-phase=2` 使用 |
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
runId   = ${args.runId || "{HHMMSS}-{mode}-{4位hex}"}    # 例：200503-lyrics-43bd
                                                         # 多 direction 分治时主 agent 自动改用：{HHMMSS}-{mode}-d{N}-{4位hex}（N=1,2,3）
directionId = ${args.directionId || null}                # 从 directions-backlog 复活时使用
```

### 0.2 创建目录结构

```bash
mkdir -p "{RunDir}/drafts" "{RunDir}/images" "{RunDir}/wechat" "{RunDir}/sources"
```

| 子目录 | 用途 |
|:-------|:-----|
| `drafts/` | blog-draft.md / blog-context-card.md / site-preview.md / site-sync-checklist.md |
| `images/` | image-plan.md / image-manifest.json |
| `wechat/` | wechat-draft.md / wechat-checklist.md / wechat-body.html / wechat-publish-result.json |
| `sources/` | 外部素材原始文件（YouTube 字幕 / 完整歌词 / 链接抓取内容等），按类型 + slug 命名（如 `youtube-{videoId}.{json,md}` / `lyrics-{song-slug}.md`） |

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
- `directions.json` / `selected.json` / `workflow.json`
- `drafts/blog-draft.md` / `drafts/blog-context-card.md`
- `drafts/self-audit.log` / `drafts/main-line-check.md`（Phase 4.5 审计产物）
- `sensitive-words.txt`（Phase 1b 提取的本 run 专用敏感词清单）
- `images/image-manifest.json`

任何引用的前序产物缺失 → 报错并要求降低 fromPhase。

**审计强制兜底**：
- from-phase ≥ 4.5 时若 `sensitive-words.txt` 不存在 → 回退到 §1b.末尾 重新提取（不重抓 source-pack）
- from-phase ≥ 5 时若 `drafts/self-audit.log` 不存在 → 强制回退到 §4.5 跑一遍 Self-Audit
- 详见 §Phase 间 Resume 契约的"铁律"段

### 0.5 directions backlog 复活（多 direction 分治时使用）

如果传入 `direction-id`（来自 `{DailyDir}/directions-backlog.md`）：
- 跳过 Phase 1a-1c（不重新生成 directions）
- 从 `{DailyDir}/directions.json`（**daily 层共享**，如已存在）或当前 runDir 的 `directions.json` 读取该 direction
- 直接进入 Phase 1d 用该 direction 走完后续流程
- 如果用户没传 `from-phase`，默认 `from-phase=2`（已选定 direction，不需要再选）

> **directions.json 的存放位置**：原方案在 `{RunDir}/`，多 direction 分治时如果三个 run 共享一份 directions（同一天三方向），第一个 run 同时把 directions.json 复制一份到 `{DailyDir}/directions.json`，后续 run 直接读 daily 层。

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

### 1b 末尾：提取本 run 专用敏感词清单（强制）

> **为什么需要这一步**：§4.5.2 (c) 具体作品/节目/书名（如「大人的 Small Talk」「奇葩说」「EP666」）很难通用 grep——只有抓素材的此刻知道本 run 涉及哪些专有名词。光靠主 agent 写作时"自觉避免"撑不住——必须落到文件，扫描兜底。

主 agent 从 `source-pack.json` 提取，写到 `{RunDir}/sensitive-words.txt`，每行一个：

```
# 1. 节目/书/专辑/作品名（出现在 lyrics 元信息 / external-link 标题 / vault-file 引用源）
大人的 Small Talk
你不是胆小，你只是地图太黑

# 2. 主讲人/作者全名（"Bryan 说" 这种短姓 OK；"约书亚·福尔" 这种全名进清单）
约书亚·福尔

# 3. 集数/期数/卷数标识（如出现在 source URL 或文件名）
EP666
S03E12

# 4. 平台特定标签（视频频道名 / 公众号名 / Substack 作者名等可定位 ID）
{平台 ID}

# 5. 用户在 Phase 2 个人锚点中提到的"不希望出现在文章里"的人名/项目名/产品名
{用户补充}
```

**抓取规则**：
- lyrics mode：歌名通常 OK 写出来（这就是词间散记的素材本质），但同张专辑的其他歌名、专辑名、演唱会名进清单
- links mode：必填——所有 source 标题、作者名、平台名、集数标识全进
- library mode：通常清单为空（KB 是 Zylen 原创素材），但如有引用第三方书/作者，也进清单

**处理空清单**：如果确实没有需要屏蔽的专有名词，写一行 `# (本 run 无专有敏感词)` 占位，避免 §4.5.2 (c) 误判文件缺失。

---

## Phase 1c：生成 3 Directions

读 `source-pack.json`，**直接生成 3 个写作方向**，必须有实质差异——不同的 topic 切入 + 不同的论证路径 + 不同的情感基调，**不是同一个 topic 的三种风格变体**。

每个 direction 字段（与 dashboard `directions.json` 兼容）：

```json
{
  "id": "kebab-case-slug",
  "title": "完整中文标题",
  "topic": "本 direction 的 topic（核心命题，1 句话）",
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
- `{RunDir}/directions.md`（人类可读版）

**写作方案设计要求**（来自 `_writing-craft.md`）：
- 开头必须制造认知冲突（**禁用**"在这个快节奏的时代"这种烂大街开头）
- 逻辑链至少穿透三层（现象 → 原因 → 结构性洞察）
- 标明哪些环节会用到个人经历做锚点
- 三个方向之间的差异必须实质化（**topic 错开 + angle 错开**，不是同一主题的三种风格变体）

---

## Phase 1d：选 Direction（Decision Card）

向用户展示 3 个 directions（读 `directions.md`）+ 选择分支：

```
## 方向选择

  [1] 选 1 个写（其他 2 个存 directions-backlog.md，未来想写直接：
      /daily-write date={date} from-phase=2 runId={新id} direction-id={backlog-id}）
  [2] 三个全写（依次跑，每个 direction 独立 runId 走完 Phase 2-9）
  [3] 混搭（你提示我合成一个新 direction，覆盖到 selected.json）
```

### 1d.A — 用户选 [1]（单 direction，默认路径）

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

**未选中的 2 个写入 backlog**：

```
{DailyDir}/directions-backlog.md
```

```markdown
# Directions Backlog ({date})

source-pack: {DailyDir}/source-pack.json
未来 resume：`/daily-write date={date} from-phase=2 runId={新HHMMSS-mode-{4位hex}} direction-id={backlog-id}`

- [ ] **{direction-A.id}** — {direction-A.title}
  - hook: {direction-A.hook}
  - logicChain: {direction-A.logicChain[:60字]}...
  - 创建于：{ISO8601}
- [ ] **{direction-B.id}** — {direction-B.title}
  - hook: {direction-B.hook}
  - logicChain: {direction-B.logicChain[:60字]}...
  - 创建于：{ISO8601}
```

> **复活时机**：用户后续启动新 run 并传 `direction-id={X}` → 主 agent 从 `{DailyDir}/directions.json` 找该 direction，从 Phase 1d.A 走单 direction 流程，并把 backlog 该项划掉（`- [x]` + 标注复活的 runId）。

### 1d.B — 用户选 [2]（三个全写，多 run 分治）

主 agent 自动执行：

1. 当前 runId 改名为 `{HHMMSS}-{mode}-d1-{4位hex}`（追加 `d1`）
2. 把 `directions.json` 复制到 `{DailyDir}/directions.json`（daily 层共享，方便后续 run 直接读）
3. 第一个 direction（用户指定排序，不指定则按 directions.json 顺序）作为当前 run 的 selected direction，走完 Phase 1d.A 派生字段
4. 创建 `{RunDir}/run.json` 时加字段：

   ```json
   {
     "siblingRuns": [
       {"directionId": "{d1-id}", "runId": "{HHMMSS}-{mode}-d1-{hex}", "status": "active"},
       {"directionId": "{d2-id}", "runId": "{HHMMSS}-{mode}-d2-{hex}", "status": "queued"},
       {"directionId": "{d3-id}", "runId": "{HHMMSS}-{mode}-d3-{hex}", "status": "queued"}
     ],
     "currentSiblingIdx": 0
   }
   ```

5. **同时把后续 d2 / d3 写到 directions-backlog.md**（与 [1] 模式相同格式），状态标 `queued`，备注 sibling runId。这样：
   - 用户中途中断（关 session / 第二天回来），下次启动只需 `from-phase=2 direction-id={dN-id}` 复活，跟 [1] 模式恢复路径完全一致
   - 不需要新增"启动时检测 queued siblings"的运行时逻辑

6. 走完 Phase 9 后，自动启动下一个 sibling run：
   - 创建新 RunDir `{DailyDir}/runs/{HHMMSS}-{mode}-d2-{hex}/`（保留原 runId 命名规则，d2 表示第 2 个）
   - 复用 `{DailyDir}/source-pack.json` 和 `{DailyDir}/directions.json`
   - 复用 `{DailyDir}/sensitive-words.txt`（同一天素材源相同，敏感词清单可共享；如某 run 个人锚点引入新敏感词，由该 run 自己追加到 `{RunDir}/sensitive-words.txt` 覆盖）
   - **不复用** `{RunDir}/drafts/*` / `{RunDir}/images/*` / `{RunDir}/wechat/*`（每篇文章独立草稿、独立配图、独立微信推送）
   - 从 Phase 2（个人锚点采集）开始——不同 direction 需要不同的个人锚点
   - 把上一个 run 的 `siblingRuns[N].status` 改为 `"completed"`，下一个改为 `"active"`，并把 backlog 该项划掉（`- [x]`）

7. 三个全跑完后，最后一个 run 的 §Phase 9 提示用户："已完成 3 篇文章的全套发布流程，sibling runs: [...]"

### 1d.C — 用户选 [3]（混搭，合成新 direction）

主 agent 询问用户："想从哪几个 direction 各取什么元素？"——比如 "用 A 的 hook + B 的 logicChain + C 的金句"。

合成后写出新 direction（id 形如 `{date}-merged-{4位hex}`），覆盖到 `{RunDir}/selected.json` + `selected-direction.json`，未被采用的 directions 不进 backlog（用户已经放弃了）。后续走单 direction 流程。

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

- **主线锚定（铁律 #1）**：文章逻辑主线 = **素材源的逻辑流**（YouTube/podcast 论点流 / 歌词起承转合 / 链接核心论证）。Phase 3 锻造产出是**深度爆点**，以 1-2 句钉子或几段穿插的形式**嵌入主线节内部**，**不可独立成节**。锻造没用上的部分进 context card sidecar，不进正文。
  - **判断标准**：每个 `##` 大节都必须能在素材源主线中找到对应位置（"这一节素材源讲的是什么对应论点？"）。找不到对应 = 你在用锻造产出造伪骨架，**重写或合并**。
  - **反例**：素材是 Bryan 讲"預設值"机制，文章却有一节叫「神经科学下的勇气」——这是把锻造的反方论据扛起来撑了一整节，**不允许**。
  - 详见 §4.5.4 主线对齐检查（强制）
- **字数**：3000-3500 字，不少于 3000
- **深度**：论证至少穿透三层；至少 3 处使用 Phase 3 的锻造洞察作"深度爆点"（嵌入主线，不独立成节）
- **主源使用**（铁律）：素材源（YouTube/链接/歌词/Vault 主题）是文章主线骨架（参见 §4.5.4 主线对齐检查），不可让位于其他东西
- **KB 素材使用（按 mode 条件化）**：
  - **library mode**：KB 是主源（用户没给外部素材，主题文件就是素材），**至少深度使用 5 条以上 KB 素材**；素材是骨骼不是装饰
  - **lyrics / links mode**：KB 是辅助参考（主源是歌词或外部链接），**心智模型 + 写作技法作为底层风格隐式贯穿即可**，建议交互式融入 1-3 条相关心智模型素材，**不强制条数**——主源 vs KB 是骨骼 vs 调味，弄反了反而让文章像通用哲学散文
- **歌词使用（仅 mode=lyrics 或 category=词间散记 时要求）**：
  - **lyrics mode / 词间散记**：至少 5 处不同歌词段落独立引用 + 解读，每处后跟 2-3 段基于歌词的分析
  - **其他 mode / 板块**：**不引用歌词**——硬塞歌词让文章不伦不类
- **风格**：第一人称 / 哲学思辨 + 生活化案例 / 长短句交错 / 思想锐度 / 段落不冗长
- **结构**：开头制造认知冲突 / 中间每 500 字一个钩子 / 结尾留余味或反转
- **格式**：markdown，`##` 和 `###` 分节，`>` 引用歌词/名言/重要金句，`**` 加粗关键概念

### 4.2 禁忌（硬约束）

#### 4.2.1 隐私红线（违反必须立即修，不允许进入 Write Gate）

- ❌ **不暴露作者具体身份/职业**：大学 / 学术 / 教师 / 老师 / 科研 / 学院 / 课题 / 讲师 / 副教授 / 学者 / 博士 / 论文 / 教授 / 研究方法等关键词**禁止出现**
  - 替代：用"我熟悉的圈子"代替"我所在的学术圈"，用"日常打交道的圈子"代替具体职业描述
- ❌ **不暴露具体学术指标**：SSCI / 影响因子 / 引用量 / 项目编号 / 课题号
- ❌ **不暴露工作强度量化**：凌晨 X 点 / 深夜 X 点 / 每天 X 小时 / X 个 skill / X 个项目 / N 篇论文 / 每周 X 次
  - 替代：用"一段时间"/"陆续搭了一些工具"/"前阵子"等泛化表达
- ❌ **不暴露感情经历**：详见全局约束 §隐私红线
- 详见 §4.5.1 隐私关键词扫描（强制）

#### 4.2.2 中文语境敏感词（写作时替换，**不直接出现在正文**）

中文读者多在公众号/博客生态，正文应保持"地理中性 / 平台中性 / 作品中性"——既不亲切也可能触发审核风险或过度暴露素材源。素材源标识在 frontmatter `tags: ["外部素材"]` 即可，正文以"我看到的""我听到的""我读到的"自然带过。

**(a) 海外平台名**：

| 原平台名 | 替换 |
|:---|:---|
| 推特 / Twitter / X.com | "国外某个汇集了 XXX 的平台" / "国外某个社群" |
| YouTube / 油管 | 视内容选用："一档 podcast" / "一段访谈视频" / "博客作者" / "播客主讲人" |
| Facebook / 脸书 | "国外某个社群" |
| Instagram / Reddit / TikTok | "海外某个平台" / 直接省略平台名 |

**(b) 地区敏感词**（涉及政治/审核敏感的地名）：

| 原词 | 替换 |
|:---|:---|
| 台湾 / 台北 / 台中 / 台南 / 高雄 | 直接省略地理修饰词，或用"老家""一个地方"等中性表达 |
| 香港 / 澳门 | 同上，或视语境用"南方""一座沿海城市" |
| 新疆 / 西藏 | 同样泛化处理 |

**反例**："听一档台湾 podcast" → 应改为 "听一档 podcast"
**反例**："Bryan 后来回台北创业" → 应改为 "Bryan 后来回老家创业"

**(c) 具体作品/节目标识**（暴露素材源精确坐标）：

| 原标识 | 替换 |
|:---|:---|
| 「大人的 Small Talk」/ 「奇葩说」/「圆桌派」/《XX 之书》等具体节目/书名 | 一档 podcast / 一档节目 / 一本书 / 一个作者 |
| EP666 / 第 N 集 / 第 N 期 / S1E2 | 直接省略集数标识 |
| 主讲人姓名 | 视情况保留（"Bryan 说"OK，但不能拼接出"大人的 Small Talk + Bryan + EP666"这种坐标） |

**判断标准**：去掉这些信息后，读者依然能理解论点，但搜不到原始素材源——刚好。

详见 §4.5.2 中文语境敏感词扫描（强制）

#### 4.2.3 专业术语未翻译成大白话（命中即重写）

- 神经科学：杏仁核 / amygdala / 前额叶 / cortisol / 肾上腺素 / 多巴胺 / 血清素 / serotonin / 皮质醇 / 神经质
  - 替代：用"自动恐惧反应"/"理性思考"/"心跳飙了、手心出汗、胃发紧"等具体感觉描述
- 心理学：依恋类型 / 认知失调 / 防御机制等术语 → 用日常语言重述
- **判断标准**：一个完全不读相关书的朋友能秒懂吗？不能 → 改
- 详见 §4.5.3 术语扫描（强制）

#### 4.2.4 写作风格禁忌

- ❌ AI 味"总分总"八股文
- ❌ 每段结尾总结一遍
- ❌ 堆砌名人名言
- ❌ **歌词/诗句/名言宁缺勿错**——sub-agent 输出的具体引用必须核实（让用户确认 / web-search 查原文 / 从 Eason.md 检索），不能直接照抄

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

### 4.5 Self-Audit（强制扫描，命中必修）

**Write Gate 之前必须执行**。这是硬步骤，不允许跳过。

> **为什么需要这一步**：靠主 agent 自觉的软约束撑不住——主 agent 写嗨了就漏。隐私违规、海外平台名、专业术语、伪骨架——这四类错误必须用扫描兜底，不能等用户来挑。

#### 4.5.1 隐私关键词扫描

```bash
DRAFT="{RunDir}/drafts/blog-draft.md"

# 身份/职业（命中必改）
grep -nE "大学|学术|教师|老师|科研|学院|课题|讲师|副教授|学者|博士|论文|教授|研究方法" "$DRAFT"

# 工作强度量化（命中必改）
grep -nE "凌晨[0-9]|深夜[0-9]|每天[0-9]+小时|[0-9]+ 个 skill|[0-9]+ 个项目|[0-9]+ 篇论文|每周[0-9]" "$DRAFT"

# 学术指标（命中必改）
grep -nE "SSCI|SCI|影响因子|引用量|项目编号|课题号|青基|国基|自科|社科" "$DRAFT"
```

任一命中 → **不允许进 Write Gate**，主 agent 自己用 Edit 工具修正后重扫，全过才推进。

#### 4.5.2 中文语境敏感词扫描（含平台名 / 地区 / 具体作品标识）

```bash
DRAFT="{RunDir}/drafts/blog-draft.md"
WORDS="{RunDir}/sensitive-words.txt"

# (a) 海外平台名（通用清单 — 任何 run 都扫）
grep -nE "推特|Twitter|X\.com|YouTube|油管|Facebook|脸书|Instagram|Reddit|TikTok|Discord" "$DRAFT"

# (b) 地区敏感词（通用清单）
grep -nE "台湾|台北|台中|台南|高雄|香港|澳门|新疆|西藏" "$DRAFT"

# (c) 具体节目/集数标识（通用 pattern）
grep -nE "EP[0-9]+|S[0-9]+E[0-9]+|第[一二三四五六七八九十百0-9]+集|第[0-9]+期" "$DRAFT"

# (d) 本 run 专用敏感词（来自 §1b 末尾提取的 sensitive-words.txt）
if [ ! -f "$WORDS" ]; then
  echo "ERROR: sensitive-words.txt 缺失，回退到 Phase 1b 末尾重新提取"
  exit 1
fi
while IFS= read -r word; do
  # 跳过空行和注释
  [ -z "$word" ] && continue
  [[ "$word" =~ ^# ]] && continue
  if grep -nF "$word" "$DRAFT"; then
    echo "命中 run 专用敏感词：$word"
  fi
done < "$WORDS"
```

任一命中 → 替换为 §4.2.2 的泛化表达，重扫。

**为什么 (a)(b)(c) 是通用 pattern + (d) 是 run 专用清单**：通用 pattern 处理"任何文章都不该出现"的词；run 专用清单处理"本素材源带入的专有名词"——比如本期素材是 podcast 「大人的 Small Talk」EP666，这两个词都进 sensitive-words.txt，扫描就能兜住。

#### 4.5.3 专业术语扫描

```bash
grep -nE "杏仁核|amygdala|前额叶|cortisol|肾上腺素|多巴胺|serotonin|神经质|prefrontal|血清素|皮质醇|海马体|hippocampus" "$DRAFT"
```

任一命中 → 翻译成大白话（具体感觉描述、生活类比），重扫。

#### 4.5.4 主线对齐检查（铁律 #1 的强制兜底）

逐 `##` 节回答："这一节在素材源主线中对应哪个论点？"

写入 `{RunDir}/drafts/main-line-check.md`：

```markdown
| `##` 节标题 | 素材源中的对应论点（必须是原文摘录或精确转述） | 对应位置 |
|:---|:---|:---|
| {节 1} | "{从素材源里实际摘录的句子或精确转述}" | sources/xxx 第 N 行 / source-pack 论点 #M |
| {节 2} | ... | ... |
| ... | ... | ... |
```

**验证铁律**：表格"对应位置"列必须用 Read 工具实际验证（在 `sources/xxx.txt` 第 N 行能找到 / `source-pack.json` 论点 #M 存在），**不允许编造行号应付检查**。lyrics mode 用 `source-pack.json items[].lyricsText` 摘录定位，library mode 用 `vault-file` 路径 + 章节标题定位。

**判定**：
- ✅ 每个 `##` 节都能在素材源中找到对应论点（且摘录已用 Read 验证） → 通过
- ❌ 某节找不到对应位置（"这是我从锻造结果撑起来的"）→ **重写或并入相邻节**——锻造产出必须以 1-2 句钉子或几段穿插嵌入主线节内部，**不可独立成节**

#### 4.5.5 全部通过后写入 audit log

```
{RunDir}/drafts/self-audit.log

- 隐私扫描：✓ 通过 / 修正 N 处
- 平台名扫描：✓ 通过 / 修正 N 处
- 术语扫描：✓ 通过 / 修正 N 处
- 主线对齐：✓ {节数} 节 / {节数} 全部找到对应位置
- 时间戳：{ISO8601}
```

只有 self-audit.log 写入后，才能进入 Phase 4.6 Write Gate。

---

### 4.6 Write Gate

向用户展示草稿（**完整正文**，不是前 500 字——用户需要全文才能给反馈）+ 字数统计 + 引用了哪些 KB 素材 + Self-Audit 结果摘要。

用户审阅后选项：
- [1] 接受 → 进入 Phase 5
- [2] 指定段落修改 → 改完再展示（修改后必须重跑 §4.5 Self-Audit）
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

迭代发生在 `{RunDir}/drafts/blog-draft.md`，每轮后**强制按以下顺序重跑**：

1. **§4.5 Self-Audit 全部子节**（隐私 / 平台名 / 术语 / 主线对齐）——新文本可能引入 Phase 4 时不存在的隐私违规或敏感词，必须重扫
2. **§6.1 Publish-Clean Scan**——扫 process notes 标记
3. **§6.2 写发布版**——只有 1 + 2 都过才允许写

跳过 §4.5 重跑就直接发布 = Phase 4 的硬扫描在 Phase 6 失效。**不允许**。

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

### 8.2 标题 + 摘要决策

> **两个标题的角色**：
> - **api_title** ≤ **10 个汉字**（30 bytes）— **技术占位符**。写到草稿箱里临时显示，**用户后台必然会手动覆盖掉**。超限返回 `45003 title size out of limit`
> - **backend_title** ≤ **22 个汉字**（约 64 字节）— 用户实际发布给关注者看到的版本，由用户在草稿箱**手动编辑**改成
> - **摘要** ≤ **15 个汉字**。超限返回 `45004 description size out of limit`
>
> **关键设计**：因为 api_title 必然被后台覆盖，**它的质量不重要、不需要用户决策**——主 agent 自动从 backend_title 衍生即可。Phase 8.2 只让用户对齐 **(1) backend_title + (2) digest** 两项，节省用户注意力。

#### 决策展示给用户

```
## 公众号标题/摘要决策

⚠️ 公众号工作流：API 推送时草稿箱标题最多 10 字（技术限制），
   你后台手动改成长标题再发布。所以只需对齐两项：

(1) 后台长标题（≤22 字，你后台手动改成这个，也是博客 frontmatter 同步目标）
   候选：
     [A] 8-12 字（精炼钉子型，hook 感最强）
     [B] 13-18 字（带副标题/逗号补充型，最自然）
     [C] 原博客标题精简版（如博客标题已在 22 字内，可直接用）
     或自定义

(2) 摘要（≤15 字）
   候选：
     [a] {候选 1}
     [b] {候选 2}

板块：{夕阳随笔 / 词间散记 / 求索手记}（基于 frontmatter category 推断）

(api_title 由主 agent 自动从 backend_title 衍生 — 见下，不需要你决策)
```

> **22 字是上限不是目标**：实际公众号长标题 12-18 字最自然，硬撑 22 字反而拗口。候选 [A]/[B] 通常已经够用，[C] 是兜底。

#### api_title 自动衍生规则

主 agent 用以下优先级从 `backend_title` 自动生成 `api_title`：

1. **如果 backend_title ≤10 字** → 直接复用，`api_title = backend_title`
2. **如果 backend_title >10 字** → **按标点切分取最前一个 ≤10 字且语义完整的子句**：
   - 切分符号：`，` / `。` / `！` / `？` / `：` / `—` / `——` / `,` / `.` / `!` / `?` / `:`
   - 例：`你不是胆小，你只是地图太黑` → 按 `，` 切 → 取首句 `你不是胆小`（5 字 ≤10 ✓）
   - 例：`「勇气」是个误译——你以为的胆量，其实是看过的多` → 按 `——` 切 → 取首句 `「勇气」是个误译`（7 字 ✓）
   - 切完所有子句都 >10 字 → 进规则 3
3. **从博客原标题或文章金句挑 ≤10 字 hook 短语**（避免拖尾标点 / 半句话）
4. **兜底**：仍找不到合适的 → **询问用户手填 api_title**（不机械截断）

**主 agent 必须在确认后展示衍生结果**：

```
✓ 已确认：
  backend_title = "{用户选定的长标题}" ({N} 字)
  digest = "{用户选定的摘要}" ({N} 字)
  api_title = "{自动衍生}" ({N} 字)  ← 草稿箱里临时显示，你后台改掉就行

是否调整？(默认继续推送)
```

#### 写到 `{RunDir}/wechat/wechat-checklist.md`

```yaml
api_title: "{自动衍生 ≤10 字}"     # 技术占位符，后台覆盖
backend_title: "{用户确认 ≤22 字}"  # 用户后台手动改成这个，也是 Phase 9 同步博客目标
digest: "{用户确认 ≤15 字}"
category: "{板块}"
```

后续步骤的 contract：
- §8.8 API 推送 只读 `api_title`（自动衍生的占位符）—— §8.7 HTML 转换处理 body，不读标题字段
- §8.10 完成提示**重点展示 backend_title** 作为用户后台编辑目标
- Phase 9 默认用 `backend_title` 同步博客 frontmatter（无需用户再次提供）

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

写出两个文件：
- `{RunDir}/wechat/wechat-draft.md`（含 inline HTML 完整内容，给用户预览用）
- `{RunDir}/wechat/wechat-body.html`（纯 HTML 备份，不含 markdown 头尾，供 Phase 8.8 直接 POST 到微信 API）

### 8.8 推送草稿（External Action Gate）

```
⚠️ WeChat Draft Creation External Action

target: api.weixin.qq.com/cgi-bin/draft/add
action: 创建一篇草稿
title: {api_title}    ← 自动衍生的占位符，用户后台改成 backend_title 再发布
digest: {digest}
backend_title (草稿箱编辑目标): {backend_title}
remote leftover: 草稿留在公众号后台草稿箱（不自动发布，需用户手动审核 + 改标题 + 发布）

授权短语：必须输入 "publish wechat draft"
```

```python
import requests, json

# 获取 access_token（有效期 7200 秒，每次推送前重新获取避免 40014 invalid access_token）
r = requests.get(f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={APPID}&secret={APPSECRET}")
token = r.json()["access_token"]

draft_data = {
    "articles": [{
        "title": api_title,           # 来自 wechat-checklist.yaml 的 api_title 字段（自动衍生 ≤10 字）
        "author": "Zylen",
        "digest": digest,             # wechat-checklist.yaml 的 digest 字段 (≤15 字)
        "content": inline_html,
        "thumb_media_id": cover_media_id,
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

**写出 API 响应记录**：
```
{RunDir}/wechat/wechat-publish-result.json
{
  "createdAt": "{ISO8601}",
  "api_title": "{推送时用的 ≤10 字标题，自动衍生}",
  "backend_title_target": "{Phase 8.2 商定的 ≤22 字长标题，用户后台改成它再发布}",
  "digest": "{Phase 8.2 用户确认的 ≤15 字摘要}",
  "thumb_media_id": "...",
  "draft_media_id": "{微信返回的 media_id}",
  "errcode": 0,
  "errmsg": "ok",
  "uploadedImages": [{"local": "...", "wechatUrl": "https://mmbiz.qpic.cn/..."}]
}
```

记录用于：失败重试 / 去重检测 / 审计追溯。

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

API 推送标题（草稿箱里临时显示）：{api_title ≤10 字}
👉 **请去草稿箱手动把标题改成（§8.2 已确认的长标题）**：{backend_title ≤22 字}

摘要：{digest ≤15 字}
封面：{thumb_media_id}
图片：{N} 张已上传 mmbiz CDN

→ 前往「微信公众号 → 草稿箱」
→ **关键步骤**：把标题改成上面那个 backend_title（API 限 10 字所以草稿箱显示是短标题，必须手动改）
→ 预览 + 发布

发布后回来告诉我，进入 Phase 9 同步博客 frontmatter title。
（如果你后台改成的标题跟 §8.2 商定的不一样，告诉我新的；一致就直接同步。）
```

---

## Phase 9：Title Back-sync

§8.2 已经和用户商定了 `backend_title`（≤22 字），用户在草稿箱手动改标题 + 发布完之后回来确认。

### 9.1 信号识别（默认快路径）

读 `{RunDir}/wechat/wechat-checklist.md` 的 `backend_title`。**不要无脑展示决策卡**——先看用户是怎么回来的：

| 用户消息 | 走法 |
|:---|:---|
| "已发布" / "go" / "发布了" / "推送好了" / 等同于"按 §8.2 商定的来" | **直接走 §9.2 同步**（不展示决策卡） |
| "我改成了 XXX" / "后台标题是 YYY" | 把 XXX/YYY 作为新 backend_title 写回 wechat-checklist.md，再走 §9.2 同步 |
| "暂时不同步" / "保持博客原标题" | 跳过 |
| 不明确 | 才展示决策卡（见下） |

**决策卡（仅 fallback 时使用）**：

```
公众号已发布。

§8.2 商定的 backend_title 是：{backend_title}
博客 frontmatter 当前 title 是：{原标题}

  [1] 同步 backend_title 到博客 frontmatter（更新 {SiteBlogDir}/{slug}.md → 询问 site redeploy）
  [2] 后台你改成了别的标题 → 告诉我新的，我用新的同步
  [3] 保持差异（博客长标题 / 公众号短标题，正文同步）
  [4] 跳过
```

### 9.2 执行（用户选 [1] 或 [2]）

更新 `{SiteBlogDir}/{slug}.md` 的 frontmatter `title` 字段为 `backend_title`（或用户提供的新标题）。

询问是否触发 site redeploy（A-level External Action Gate，复用 Phase 7 协议——必须输入 "deploy site" 才执行）。

> **原则**：公众号是标题的 source of truth，博客跟随同步。**正文内容两端一致**，不做差异化。
> **简化收益**：因为 §8.2 已经商定了 `backend_title`，多数情况下 Phase 9 只需要用户一句确认，不需要他重新告诉我标题——除非他后台临时改了主意。

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
- ❌ 具体工具链清单：`/lit-plan` `/narrative` `/method-audit` 这种暴露工作流细节
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
| 1d | request.json + source-pack.json + directions.json |
| 2  | selected-direction.json + workflow.json + source-pack.json + sensitive-words.txt |
| 3  | drafts/blog-context-card.md（含 Personal Anchors）+ sensitive-words.txt |
| 4  | drafts/blog-context-card.md（含 Deep-Forging）+ sensitive-words.txt |
| 4.5 | drafts/blog-draft.md + sensitive-words.txt |
| 5  | drafts/blog-draft.md **+ drafts/self-audit.log**（确认 Phase 4.5 Self-Audit 已通过） |
| 6  | images/image-manifest.json + drafts/self-audit.log |
| 7  | {SiteBlogDir}/{slug}.md（publish-clean）+ drafts/self-audit.log |
| 8  | site deployed（如未 skip-deploy）+ drafts/self-audit.log |
| 9  | wechat draft created（wechat-publish-result.json 存在） |

**铁律**：
- from-phase ≥ 4.5 时若 `sensitive-words.txt` 不存在 → 回退到 §1b 末尾重新提取（不重抓 source-pack）
- from-phase ≥ 5 时若 `self-audit.log` 不存在 → **强制回退到 Phase 4.5 跑一遍 Self-Audit**，不允许跳过审计直接进入发布链路。这防止旧版 skill 写的 blog-draft.md（未审计）越过隐私扫描进入发布区。

**多 direction 分治时的 resume**（用户传 `direction-id=X`）：
- 必须存在 `{DailyDir}/directions.json` + `{DailyDir}/source-pack.json`（daily 层共享）
- 主 agent 在新 RunDir 中：从 directions 找该 direction → 走 §Phase 1d.A 派生字段 → 复用 daily 层 sensitive-words.txt（如本 run 个人锚点引入新词，可在新 RunDir 追加）→ 从 Phase 2 走完
- backlog 中该项更新为 `- [x]` 并标注复活的 runId

### 三层目录铁律

- 工作区污染允许：`{RunDir}/`（process notes / sidecar / 迭代历史）
- 发布区严控：`{SiteBlogDir}/{slug}.md` 必须 publish-clean
- 归档区永久：`{WechatBlogDir}/{date}_{cat}_{title}/`

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
| Phase 4.5 Self-Audit 反复扫不过 | 列出最顽固的命中位置（命中关键词 + 段落），向用户求助决策——是改写为泛化、删除整段、还是改文章方向。绝不允许"忽略命中"硬推进。 |
| 用户中断后再启动 | 用 `from-phase=N` 指定恢复点；若目标 phase ≥ 5 而 self-audit.log 缺失，自动回退到 §4.5 |

### 踩坑记录

| 坑 | 现象 | 教训 |
|:---|:-----|:-----|
| NB2 并行限流 | 多张图并行 → ChatAnywhere 限流挂起 | **必须串行**，不要 `run_in_background` |
| `sips -z` 变形 | 强制缩放破坏比例 | 用 `--resampleWidth + --cropToHeightWidth` 两步走 |
| 第一版直接部署 | 半成品被公开访问 | Phase 6 必须迭代后用户确认 OK 才进 Phase 7 |
| 歌词只抓 chorus | 词间散记内容空洞 | **仅 lyrics/词间散记必须**完整歌词 + 至少 5 处独立引用，其他板块不要硬塞歌词 |
| KB 素材浮于表面 | 文章像通用哲学散文 | **仅 library mode** 必须深用 5+ 条；lyrics/links mode 主源是外部素材，KB 是辅助参考不强制条数 |
| 给非 lyrics 文章硬塞歌词 / 给非 library 文章硬塞 5 条 KB | 文章节奏拧巴、像八股 | §4.1 写作要求按 mode 条件化（2026-04-28 修订），不再无差别要求 |
| 第一版缺个人经历 | direction 选完直接写 | Phase 2 必须采集锚点 |
| `requests json=` 中文乱码 | 标题/正文全变 `\uXXXX` | 必须 `json.dumps(..., ensure_ascii=False).encode("utf-8")` + `data=` 参数 |
| WeChat 标题 11 字 | `45003 title size out of limit` | API 限制 ≤10 汉字，比后台严 |
| `--dotfiles` 缺失 | 部署后 CSS 404 | `npx gh-pages -d dist --dotfiles` 必加 |
| frontmatter 缺 cover | 公众号无封面 | Phase 5 必须生成封面图，frontmatter 必须含 `cover` |
| 把 process notes 写到 site | 发布版含 "Bug Cascade Audit" 等内部记号 | Phase 6.1 publish-clean scan 强制兜底 |
| 用锻造结果撑起整节伪骨架 | 文章某节素材源里找不到对应论点（如 Bryan podcast 文章里出现"神经科学下的勇气"独立节）| 主线 = 素材源；锻造做嵌入式爆点不可独立成节。Phase 4.1 铁律 #1 + 4.5.4 主线对齐检查 强制兜底 |
| 暴露作者身份/职业 | 正文出现"我在大学体制内工作""我所在的学术圈"等 | Phase 4.5.1 隐私关键词扫描强制兜底（grep 命中即修） |
