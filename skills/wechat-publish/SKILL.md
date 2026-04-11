---
description: "将博客文章适配并推送到微信公众号「夕阳乃常事」草稿箱"
---

# WeChat Publish — 博客 → 公众号草稿

读取 academic-site 的博客 markdown，自动适配微信格式，推送到公众号草稿箱。

**输入**：`/wechat-publish {slug}`（slug 对应 `src/data/blog/{slug}.md`）

---

## 前置条件

### 凭证位置

```bash
# ~/.claude/scheduled/email-config.sh 中存储：
WECHAT_APPID="wxf24058aabe5b9abd"
WECHAT_APPSECRET="..."
```

### IP 白名单

微信 API 要求调用方 IP 在白名单中。如遇 `40164 invalid ip` 错误：
1. 从错误信息中提取 IP
2. 用户到 **微信开发者平台 → 开发接口管理 → IP 白名单** 添加
3. 重试

---

## Step 1：读取博客源文件

读取：`/Users/zylen/Library/CloudStorage/Dropbox/04-Coding/academic-site/src/data/blog/{slug}.md`

解析 frontmatter（title, date, tags, summary, cover）和正文 markdown。

提取所有图片引用：`![alt](/academic-site/blog/{filename}.png)` → 收集文件名列表。

图片文件位于：`/Users/zylen/Library/CloudStorage/Dropbox/04-Coding/academic-site/public/blog/`

> **铁律：正文一个字都不改。** 博客和公众号的正文内容必须完全一致。只允许改标题和摘要。直接从博客 md 文件解析转换为 HTML，禁止手动重写或精简内容。

---

## Step 2：生成公众号版标题和摘要

### 标题（关键坑）

> **个人订阅号 API 标题限制：10 个汉字（30 字节）。** 超过即返回 `45003 title size out of limit`。
> 注意：这比公众号后台手动编辑的标题限制严格得多（后台可输入更长标题）。

规则：
- 从博客原标题出发，提炼 ≤10 字的公众号标题
- 优先：悬念感、提问式、反直觉——抓住手机用户 3 秒注意力
- 展示给用户确认

### 摘要（关键坑）

> **摘要（digest）也有字数限制，约 15 个汉字。** 超过即返回 `45004 description size out of limit`。

规则：
- 从博客 summary 提炼一句话 ≤15 字
- 展示给用户确认

### 示例

| 博客标题 | 公众号标题 | 摘要 |
|:---------|:----------|:-----|
| 任我行：在枷锁中选择你的自由 | 你多久没让自己疯一下 | 自由在于选择闯红灯还是等绿灯 |

---

## Step 3：图片处理

### 3.1 压缩

微信 `uploadimg` 接口限制图片 ≤1MB。DALL-E 生成的 PNG 通常 2-3MB，必须压缩：

```bash
sips -s format jpeg -s formatOptions 60 "{input}.png" --out "/tmp/wechat-upload/{name}.jpg"
```

### 3.2 归档素材

压缩上传完成后，将本篇图片归档到 wechat-assets 项目：

```bash
ASSETS="/Users/zylen/Library/CloudStorage/Dropbox/04-Coding/wechat-assets/blog/{slug}"
mkdir -p "$ASSETS"
cp public/blog/{slug}*.png "$ASSETS/"
```

> **素材归档目录**：`/Users/zylen/Library/CloudStorage/Dropbox/04-Coding/wechat-assets/`
> - `blog/{slug}/` — 每篇文章的原始 PNG（封面 + 插图）
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

在正文最前面插入阅读时间提示（博客 md 和公众号 HTML 都加）：

- 计算方式：统计正文汉字数 ÷ 500（中文平均阅读速度），向上取整
- 博客 md 格式：在 frontmatter 后、正文第一行前插入 `*阅读时间：约 {N} 分钟 · {字数} 字*`
- 公众号 HTML 格式：`<p style="font-size:13px;color:#999;margin:0 0 24px;text-align:center;">阅读时间：约 {N} 分钟 · {字数} 字</p>`

### 4.1 转换规则

微信文章必须使用 **inline CSS**（无外部样式表）。转换规则：

| Markdown | HTML |
|:---------|:-----|
| `## 标题` | `<h2 style="font-size:20px;font-weight:600;color:#191918;margin:32px 0 12px;border-left:4px solid #C9714E;padding-left:12px;">{text}</h2>` |
| `### 标题` | `<h3 style="font-size:17px;font-weight:600;color:#191918;margin:24px 0 8px;">{text}</h3>` |
| 段落 | `<p style="font-size:15px;line-height:2;color:#3b3b3b;margin:12px 0;text-align:justify;">{text}</p>` |
| `> 引用` | `<blockquote style="border-left:3px solid #C9714E;padding:8px 16px;margin:16px 0;color:#888;font-style:italic;font-size:15px;line-height:1.8;">{text}</blockquote>` |
| `**加粗**` | `<strong style="color:#191918;">{text}</strong>` |
| `*斜体*` | `<em>{text}</em>` |
| `- 列表项` | `<ul style="padding-left:1.5em;margin:12px 0;"><li style="font-size:15px;line-height:2;color:#3b3b3b;">{text}</li></ul>` |
| `![](url)` | `<p style="text-align:center;margin:24px 0;"><img src="{wechat_cdn_url}" style="max-width:100%;border-radius:12px;" /></p>` |

注意事项：
- 图片 URL 必须替换为 Step 3 上传后的微信 CDN URL（`mmbiz.qpic.cn` 域名）
- 不支持外部图片链接
- `<p>` 之间的空行由 margin 控制，不需要 `<br>`

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
        "title": "{公众号标题，≤10字}",
        "author": "Zylen",
        "digest": "{摘要，≤15字}",
        "content": "{inline HTML}",
        "thumb_media_id": "{封面图 media_id}",
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

**API 标题**：{公众号标题，≤10字}
**摘要**：{摘要}
**封面**：{封面描述}
**图片**：{N} 张已上传至微信 CDN

→ 请前往公众号后台「内容管理 → 草稿箱」预览和发布
→ 后台中可修改标题（不受 API 10 字限制）

发布后告诉我最终标题，我同步回博客。
```

### 6.2 标题回同步

用户在公众号后台确认/修改标题并发布后，将最终标题同步回博客源文件：

1. 询问用户最终标题（可能与 API 推送时的 ≤10 字标题不同）
2. 更新 `src/data/blog/{slug}.md` 的 frontmatter `title` 字段
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
| 图片 >1MB | uploadimg 报错 | DALL-E PNG 通常 2-3MB，必须 `sips` 压缩为 JPEG quality=60 |
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
| 凭证缺失 | 提示用户检查 `~/.claude/scheduled/email-config.sh` |
| 所有图片上传失败 | 询问用户是否推送无图草稿，或放弃本次推送 |
| 博客 frontmatter 缺字段 | 报错并指出缺少哪个字段（title/cover 为必须） |
