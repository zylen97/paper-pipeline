---
description: "已有 src/data/blog/{slug}.md 的独立后置入口：把博客适配并推送到微信公众号「夕阳乃常事」草稿箱"
---

# WeChat Publish — 博客 → 公众号草稿（独立后置入口）

读取 academic-site 的博客 markdown，自动适配微信格式，推送到公众号草稿箱。

**输入**：`/wechat-publish {slug}`（slug 对应 `src/data/blog/{slug}.md`）

> **定位（重要）**：
> 本 skill 是**独立后置入口**——专门处理"已有 `src/data/blog/{slug}.md`，单独发微信"的场景（如：补发老博文、博文从其他途径产生）。
>
> 日常的"写新文章 + 同步发微信"完整 workflow 在 `/daily-write`（Phase 8 inline 完整 wechat 逻辑）。
>
> **协议同步声明**：本 skill 与 `/daily-write` Phase 8 主体步骤对齐。修改 wechat 协议时（标题/摘要长度、API 路径、HTML 转换规则等）**两个 skill 必须同步更新**，避免行为漂移。

---

## 前置条件

### 凭证位置

```bash
# Dropbox/Apps/secrets-vault/email-config.sh 中存储（通过 ~/.claude/scheduled/email-config.sh 符号链接访问）：
# WECHAT_APPID 和 WECHAT_APPSECRET
source ~/.claude/scheduled/email-config.sh
```

### IP 白名单

微信 API 要求调用方 IP 在白名单中。如遇 `40164 invalid ip` 错误：
1. 从错误信息中提取 IP
2. 用户到 **微信开发者平台 → 开发接口管理 → IP 白名单** 添加
3. 重试

---

## Step 0.5：板块确认

「夕阳乃常事」设三个板块，根据文章内容确认归属：

| 板块 | 内容类型 | 对应 blog tags |
|:-----|:---------|:---------------|
| **夕阳随笔** | 人生哲学、存在主义、价值观思辨 | 人生哲学, 存在主义, 心态, 注意力 |
| **词间散记** | 歌词解读（Eason 为主，不限于 Eason） | Eason, 林夕, 歌词 |
| **求索手记** | 科研方法论、青椒生活、AI/新技术使用与思考 | 科研, 学术, Ikigai, AI, 技术 |

根据博客 frontmatter 的 tags 自动判断板块归属。如果不确定，向用户确认。板块信息将体现在公众号草稿的摘要中（如「夕阳随笔 · 第 N 篇」）。

---

## Step 1：读取博客源文件

> **上游来源**：由 `/daily-write` Phase 6 输出到 `src/data/blog/{slug}.md`，或用户手动放置

读取：`/Users/zylen/Library/CloudStorage/Dropbox/04-Coding/academic-site/src/data/blog/{slug}.md`

解析 frontmatter（title, date, tags, summary, cover）和正文 markdown。

提取所有图片引用：`![alt](/academic-site/blog/{filename}.png)` → 收集文件名列表。

图片文件位于：`/Users/zylen/Library/CloudStorage/Dropbox/04-Coding/academic-site/public/blog/`

> **铁律：正文一个字都不改。** 博客和公众号的正文内容必须完全一致。只允许改标题和摘要。直接从博客 md 文件解析转换为 HTML，禁止手动重写或精简内容。

---

## Step 2：标题 + 摘要决策

> **两个标题的角色**：
> - **api_title** ≤ **10 个汉字**（30 bytes）— **技术占位符**。写到草稿箱里临时显示，**用户后台必然会手动覆盖掉**。超限返回 `45003 title size out of limit`
> - **backend_title** ≤ **22 个汉字**（约 64 字节）— 用户实际发布给关注者看到的版本，由用户在草稿箱**手动编辑**改成
> - **摘要** ≤ **15 个汉字**。超限返回 `45004 description size out of limit`
>
> **关键设计**：因为 api_title 必然被后台覆盖，**它的质量不重要、不需要用户决策**——主 agent 自动从 backend_title 衍生即可。Step 2 只让用户对齐 **(1) backend_title + (2) digest** 两项，节省用户注意力。

### 决策展示给用户

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

### api_title 自动衍生规则

主 agent 用以下优先级从 `backend_title` 自动生成 `api_title`：

1. **如果 backend_title ≤10 字** → 直接复用，`api_title = backend_title`
2. **如果 backend_title >10 字** → **按标点切分取最前一个 ≤10 字且语义完整的子句**：
   - 切分符号：`，` / `。` / `！` / `？` / `：` / `—` / `——` / `,` / `.` / `!` / `?` / `:`
   - 例：`你不是胆小，你只是地图太黑` → 按 `，` 切 → 取首句 `你不是胆小`（5 字 ≤10 ✓）
   - 例：`「勇气」是个误译——你以为的胆量，其实是看过的多` → 按 `——` 切 → 取首句 `「勇气」是个误译`（7 字 ✓）
   - 切完所有子句都 >10 字 → 进规则 3
3. **从博客原标题或文章金句挑 ≤10 字 hook 短语**（避免拖尾标点 / 半句话）
4. **兜底**：仍找不到合适的 → **询问用户手填 api_title**（不机械截断）

主 agent 在确认后展示衍生结果：

```
✓ 已确认：
  backend_title = "{用户选定的长标题}" ({N} 字)
  digest = "{用户选定的摘要}" ({N} 字)
  api_title = "{自动衍生}" ({N} 字)  ← 草稿箱里临时显示，你后台改掉就行

是否调整？(默认继续推送)
```

### 示例

| 博客标题 | api_title（自动衍生 ≤10 字）| backend_title（用户选 ≤22 字）| digest（≤15 字）|
|:---------|:----------|:----------|:-----|
| 任我行：在枷锁中选择你的自由 | 任我行：在枷锁中 | 任我行：在枷锁中选择你的自由 | 自由在于选择闯红灯还是等绿灯 |
| 「勇气」是个误译——你以为的胆量，其实是脑中例子的密度 | 勇气是个误译 | 「勇气」是个误译——你以为的胆量 | 你以为的胆量，其实是看过的多 |

### 写到 wechat-checklist

```yaml
api_title: "{自动衍生 ≤10 字}"     # 技术占位符，后台覆盖
backend_title: "{用户确认 ≤22 字}"  # 用户后台手动改成这个，也是 Step 6 后博客同步的目标
digest: "{用户确认 ≤15 字}"
category: "{板块}"
```

后续步骤的 contract：
- Step 5 API 推送 只读 `api_title`（自动衍生的占位符）—— Step 4 HTML 转换处理 body，不读标题字段
- Step 6 完成提示**重点展示 backend_title** 作为用户后台编辑目标
- Step 6 后回博客同步默认用 `backend_title`

---

## Step 3：图片处理

### 3.1 压缩

微信 `uploadimg` 接口限制图片 ≤1MB。NB2（Nano Banana 2）生成的 PNG 通常 1-2MB，必须压缩：

```bash
sips -s format jpeg -s formatOptions 60 "{input}.png" --out "/tmp/wechat-upload/{name}.jpg"
```

### 3.2 归档素材

压缩上传完成后，将本篇图片归档到 wechat-assets 项目。

> **归档文件夹命名格式**：`{date}_{category}_{title}`（日期在前，方便按时间排序）
> - `date`：frontmatter 的 `date`（YYYY-MM-DD）
> - `category`：frontmatter 的 `category`（夕阳随笔 / 词间散记 / 求索手记）
> - `title`：frontmatter 的 `title`（中文原标题，保留冒号/问号等符号）
> - 示例：`2026-04-11_词间散记_任我行：在枷锁中选择你的自由`
> - 文件夹**内部**的 PNG/md 文件名保持英文 slug 不变（仅外层文件夹用中文格式）

```bash
BLOG_MD="src/data/blog/{slug}.md"
CATEGORY=$(grep '^category:' "$BLOG_MD" | sed 's|category: *"||;s|"$||')
TITLE=$(grep '^title:' "$BLOG_MD" | sed 's|title: *"||;s|"$||')
DATE=$(grep '^date:' "$BLOG_MD" | sed 's|date: *"||;s|"$||')
FOLDER="${DATE}_${CATEGORY}_${TITLE}"

ASSETS="/Users/zylen/Library/CloudStorage/Dropbox/04-Coding/wechat-assets/blog/$FOLDER"
mkdir -p "$ASSETS"
# 根据博客 md 中实际引用的图片路径 cp，不要用 {slug}* glob（实际文件名可能不匹配）
# 例如：从 md 中提取 ![](/academic-site/blog/fc-01-midnight-lights.png) → cp public/blog/fc-01-midnight-lights.png
# 封面图从 frontmatter cover 字段提取路径
for img in $(grep -o '/academic-site/blog/[^)]*' "$BLOG_MD" | sed 's|/academic-site/blog/||'); do
  cp "public/blog/$img" "$ASSETS/" 2>/dev/null
done
# 封面图
cover=$(grep '^cover:' "$BLOG_MD" | sed 's|cover: "/academic-site/blog/||;s|"||g')
[ -n "$cover" ] && cp "public/blog/$cover" "$ASSETS/" 2>/dev/null
# 博客正文 md
cp "$BLOG_MD" "$ASSETS/" 2>/dev/null
```

> **素材归档目录**：`/Users/zylen/Library/CloudStorage/Dropbox/04-Coding/wechat-assets/`
> - `blog/{date}_{category}_{title}/` — 每篇文章的原始 PNG（封面 + 插图）+ 博客 md
> - `avatars/` — 公众号头像备选图

### 3.3 上传封面（永久素材）

封面图用于文章列表缩略图，需上传为永久素材：

```bash
curl -s -X POST \
  "https://api.weixin.qq.com/cgi-bin/material/add_material?access_token={TOKEN}&type=image" \
  -F "media=@/tmp/wechat-upload/{cover}.jpg"
```

返回 `media_id` → 用作 `thumb_media_id`。

### 3.4 上传正文图片（文章图片）

正文插图用 `uploadimg` 接口，返回微信 CDN URL：

```bash
curl -s -X POST \
  "https://api.weixin.qq.com/cgi-bin/media/uploadimg?access_token={TOKEN}" \
  -F "media=@/tmp/wechat-upload/{name}.jpg"
```

返回 `{"url": "https://mmbiz.qpic.cn/..."}` → 替换到 HTML 中。

---

## Step 4：Markdown → 微信 HTML

### 4.0 阅读时间

博客 md 中已由 `/daily-write` 插入了阅读时间行（`*阅读时间：约 {N} 分钟 · {字数} 字*`），**不要重复插入或修改源文件**。

转换为公众号 HTML 时，检测以 `*阅读时间：` 开头的段落，使用专属样式（不走普通斜体规则）：
- `<p style="font-size:13px;color:#999;margin:0 0 24px;text-align:center;">阅读时间：约 {N} 分钟 · {字数} 字</p>`

### 4.1 转换规则

微信文章必须使用 **inline CSS**（无外部样式表）。转换规则：

| Markdown | HTML |
|:---------|:-----|
| `## 标题` | `<h2 style="font-size:20px;font-weight:600;color:#191918;margin:32px 0 12px;border-left:4px solid #C9714E;padding-left:12px;">{text}</h2>` |
| `### 标题` | `<h3 style="font-size:17px;font-weight:600;color:#191918;margin:24px 0 8px;">{text}</h3>` |
| 段落 | `<p style="font-size:15px;line-height:2;color:#3b3b3b;margin:12px 0;text-align:justify;">{text}</p>` |
| `> 引用`（单行或多行） | `<blockquote style="border-left:3px solid #C9714E;padding:8px 16px;margin:16px 0;color:#888;font-style:italic;font-size:15px;line-height:1.8;">{text}</blockquote>`。**多行引用**：连续的 `> ` 行合并为同一个 `<blockquote>`，行间用 `<br>` 分隔 |
| `**加粗**` | `<strong style="color:#191918;">{text}</strong>` |
| `*斜体*` | `<em>{text}</em>`（注意：`*阅读时间：` 开头的行走 Step 4.0 专属样式，不走此规则） |
| `- 列表项`（无序列表） | 连续的 `- ` 行合并为一个 `<ul>`，每行一个 `<li>`：`<ul style="padding-left:1.5em;margin:12px 0;"><li style="font-size:15px;line-height:2;color:#3b3b3b;">{text}</li>...</ul>` |
| `1. 列表项`（有序列表） | 连续的 `N. ` 行合并为一个 `<ol>`：`<ol style="padding-left:1.5em;margin:12px 0;"><li style="font-size:15px;line-height:2;color:#3b3b3b;">{text}</li>...</ol>` |
| `` `code` ``（行内代码） | `<code style="background:#f5f5f5;padding:2px 6px;border-radius:4px;font-size:14px;">{text}</code>` |
| 围栏代码块（` ``` `） | `<pre style="background:#f5f5f5;padding:16px;border-radius:8px;overflow-x:auto;font-size:14px;line-height:1.6;margin:16px 0;"><code>{code}</code></pre>` |
| `![](url)` | `<p style="text-align:center;margin:24px 0;"><img src="{wechat_cdn_url}" style="max-width:100%;border-radius:12px;" /></p>` |

注意事项：
- 图片 URL 必须替换为 Step 3 上传后的微信 CDN URL（`mmbiz.qpic.cn` 域名）
- 不支持外部图片链接
- `<p>` 之间的空行由 margin 控制，不需要 `<br>`
- 列表和引用按 block（段落）为单位转换，不是逐行独立转换——连续的同类行属于同一个 block

### 配色方案

与 academic-site 保持一致：
- 正文色：`#3b3b3b`
- 标题色：`#191918`
- 强调色/引用线：`#C9714E`（academic-site accent color）
- 引用文字色：`#888`

---

## Step 5：推送草稿

### 5.1 获取 access_token

```python
r = requests.get(f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={APPID}&secret={APPSECRET}")
token = r.json()["access_token"]  # 有效期 7200 秒
```

### 5.2 创建草稿

```python
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
# 关键：必须用 ensure_ascii=False，否则中文变成 \uXXXX 乱码
r = requests.post(
    f"https://api.weixin.qq.com/cgi-bin/draft/add?access_token={token}",
    data=json.dumps(draft_data, ensure_ascii=False).encode("utf-8"),
    headers={"Content-Type": "application/json; charset=utf-8"}
)
```

> **不要用 `json=draft_data`**，那会走 `requests` 默认的 `ensure_ascii=True`，中文标题/正文全变 `\uXXXX`。

成功返回 `{"media_id": "..."}` → 草稿已创建。

### 5.3 清理测试草稿（如有）

如果调试过程中产生了测试草稿：

```python
# 列出草稿
r = requests.post(f"https://api.weixin.qq.com/cgi-bin/draft/batchget?access_token={token}", json={"offset": 0, "count": 20, "no_content": 1})
# 删除指定草稿
requests.post(f"https://api.weixin.qq.com/cgi-bin/draft/delete?access_token={token}", json={"media_id": "{id}"})
```

---

## Step 6：提示用户 + 标题回同步

### 6.1 推送成功提示

输出：

```
## 公众号草稿推送成功

**API 推送标题（草稿箱里临时显示）**：{api_title ≤10 字}
👉 **请去草稿箱手动把标题改成（Step 2 已确认的长标题）**：{backend_title ≤22 字}

**摘要**：{digest ≤15 字}
**封面**：{封面描述}
**图片**：{N} 张已上传至微信 CDN

→ 前往公众号后台「内容管理 → 草稿箱」
→ **关键步骤**：把标题改成上面的 backend_title（API 限 10 字所以草稿箱里是短标题，必须手动改）
→ 预览 + 发布

发布后回来确认博客同步（Step 6.2）。
```

### 6.2 标题回同步

Step 2 已经和用户商定了 `backend_title`（≤22 字），用户在草稿箱手动改标题 + 发布完之后回来确认。

**信号识别（默认快路径，不无脑展示决策卡）**：

| 用户消息 | 走法 |
|:---|:---|
| "已发布" / "go" / "发布了" / "推送好了" / 等同于"按 Step 2 商定的来" | **直接走同步**（不展示决策卡） |
| "我改成了 XXX" / "后台标题是 YYY" | 把新标题写回 wechat-checklist.md，再同步 |
| "暂时不同步" / "保持博客原标题" | 跳过 |
| 不明确 | 才展示决策卡（见下） |

**决策卡（仅 fallback 时使用）**：

```
公众号已发布。

Step 2 商定的 backend_title 是：{backend_title}
博客 frontmatter 当前 title 是：{原标题}

  [1] 同步 backend_title 到博客 frontmatter（更新 src/data/blog/{slug}.md → 询问 site redeploy）
  [2] 后台你改成了别的标题 → 告诉我新的，我用新的同步
  [3] 保持差异（博客长标题 / 公众号短标题，正文同步）
  [4] 跳过
```

执行（用户走快路径或选 [1] / [2]）：

1. 更新 `src/data/blog/{slug}.md` 的 frontmatter `title` 字段为 `backend_title`（或用户提供的新标题）
2. 如果用户选 [3]，则不修改
3. 部署到 GitHub Pages（询问用户）：

```bash
cd /Users/zylen/Library/CloudStorage/Dropbox/04-Coding/academic-site
npm run build
npx gh-pages -d dist --dotfiles
```

> **注意**：必须加 `--dotfiles`，否则 `.nojekyll` 不会被推送，GitHub Jekyll 会吞掉 `_astro/` 目录导致 CSS 404。

> **原则**：公众号是标题的 source of truth，博客跟随同步。正文内容两端一致，不做差异化。

---

## 踩坑记录

| 坑 | 现象 | 解法 |
|:---|:-----|:-----|
| 标题 10 字限制 | `45003 title size out of limit` | 个人订阅号 API 限 10 汉字（30 bytes），后台编辑无此限制 |
| 摘要字数限制 | `45004 description size out of limit` | digest 控制在 ≤15 汉字 |
| IP 白名单 | `40164 invalid ip` | 到微信开发者平台添加调用方 IP |
| 图片 >1MB | uploadimg 报错 | NB2 PNG 通常 1-2MB，必须 `sips` 压缩为 JPEG quality=60 |
| f-string 中文引号 | Python SyntaxError | 中文引号 `""「」` 在 f-string 中可能被误识别，用字符串拼接代替 |
| access_token 过期 | `40014 invalid access_token` | token 有效期 2 小时，每次推送前重新获取 |
| 开发接口迁移 | 公众号后台找不到 AppSecret | 2025-12-01 起迁移至「微信开发者平台」管理 |
| 中文变 `\uXXXX` 乱码 | 标题/正文全是转义码 | `requests` 的 `json=` 参数默认 `ensure_ascii=True`，必须手动 `json.dumps(data, ensure_ascii=False).encode("utf-8")` + `data=` + `Content-Type: charset=utf-8` |

---

## 边界条件

| 情况 | 处理 |
|:-----|:-----|
| 博客文件不存在 | 报错并列出可用的 slug |
| 博客无图片 | 正常推送，跳过图片上传步骤 |
| 图片压缩后仍 >1MB | 降低 quality 到 40 重试 |
| API 返回未知错误 | 打印完整错误信息，不静默吞掉 |
| 已有同标题草稿 | 微信允许重复标题，但提醒用户检查是否重复推送 |
| 凭证缺失 | 提示用户检查 `~/.claude/scheduled/email-config.sh`（→ secrets-vault 符号链接） |
| 所有图片上传失败 | 询问用户是否推送无图草稿，或放弃本次推送 |
| 博客 frontmatter 缺 title | 报错，title 为必须字段 |
| 博客 frontmatter 缺 cover | 提醒用户补充封面图（可用 `/daily-write` 重新生成），或询问是否使用默认封面 |
