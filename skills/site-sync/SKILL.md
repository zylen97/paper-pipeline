---
description: "扫描科研项目 CLAUDE.md，自动同步 Academic Site 的 projects.md 项目索引（含 Obsidian 副本）"
---

# Site-Sync — 项目索引自动同步

扫描所有科研项目的 CLAUDE.md，与 Academic Site 的 `projects.md` 合并，更新项目状态和元数据。

**输入**：无参数，直接运行 `/site-sync`

---

## 步骤 1：扫描项目

```bash
python3 ~/.claude/skills/site-sync/scan_projects.py
```

脚本扫描以下目录中的 CLAUDE.md：
- `/02-Research/papers/` 下所有 `zy*` 项目
- `/02-Research/papers/_done/` 下的已完成项目
- `/_GYM group dropbox/_gym paper/` 下所有 `dj*`、`zz*`、`xq*` 项目及 `_done/`

输出 JSON 包含 `projects`（元数据列表）和 `count`（总数）。

每个项目包含：`id`、`title`、`method`、`journal`、`status`、`_category`

`_category` 映射规则：
- `_done/` 目录 → `published`
- `submitted` / `revision-R*` → `under_review`
- `foundation` / `drafting` → `in_progress`

## 步骤 2：读取现有 projects.md

读取：`/Users/zylen/Library/CloudStorage/Dropbox/04-Coding/academic-site/src/data/projects.md`

解析三个表格（已发表 / 投稿中 / 撰写中），提取每行的：标题、方法、期刊、身份、年份（仅已发表）、公开

## 步骤 3：合并

对比扫描结果与现有 projects.md，执行合并：

| 情况 | 处理 |
|:-----|:-----|
| CLAUDE.md 有，projects.md 没有 | **新增**：标题/方法/期刊取 CLAUDE.md，身份默认"一作"，公开默认 ❌ |
| 两边都有（按标题匹配） | **更新**：标题/方法/期刊/状态取 CLAUDE.md，身份/年份/公开保留 projects.md |
| projects.md 有，CLAUDE.md 没有 | **保留**：老项目无 CLAUDE.md，原样保留 |
| 状态类别变化（如 in_progress → under_review） | **移动**：条目移到新类别表格 |

## 步骤 4：展示 Diff

向用户展示变更摘要：

```
## 项目索引同步预览

### 新增项目
- {标题} → {类别}

### 状态变化
- {标题}: {旧类别} → {新类别}

### 元数据更新
- {标题}: 方法 "{旧}" → "{新}"

### 统计
| 类别 | 当前 | 同步后 |
|:-----|:----:|:-----:|
| 已发表 | X | Y |
| 投稿中 | X | Y |
| 撰写中 | X | Y |
```

**用户确认后才写入。**

## 步骤 5：写入

1. 生成新的 `projects.md` 内容，保持原有格式：

```markdown
## 已发表

| 标题 | 方法 | 期刊 | 身份 | 年份 | DOI | 公开 |
|------|------|------|------|------|-----|------|
| ... |

## 投稿中

| 标题 | 方法 | 目标期刊 | 身份 | 公开 |
|------|------|---------|------|------|
| ... |

## 撰写中

| 标题 | 方法 | 目标期刊 | 身份 | 公开 |
|------|------|---------|------|------|
| ... |
```

2. 写入 Academic Site：
   `/Users/zylen/Library/CloudStorage/Dropbox/04-Coding/academic-site/src/data/projects.md`

3. 同步 Obsidian 副本：
   `/Users/zylen/Library/CloudStorage/Dropbox/Apps/Zylen's Obsidian/02-working/1-科研&横向课题/研究项目索引.md`

## 步骤 6：部署（可选）

询问用户是否部署到 GitHub Pages：

```bash
cd /Users/zylen/Library/CloudStorage/Dropbox/04-Coding/academic-site
npm run build
git add -A && git commit -m "sync: update project index"
git push
```

---

## 边界条件

| 情况 | 处理 |
|:-----|:-----|
| CLAUDE.md 缺少字段（如无标题） | 跳过该项目，在报告中警告 |
| 标题匹配不上（CLAUDE.md 改了标题） | 当作新项目新增，旧条目保留，提醒用户手动去重 |
| projects.md 不存在 | 从零生成 |
| Obsidian 副本路径不存在 | 跳过同步，警告 |
