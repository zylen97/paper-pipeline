---
description: "从UTD24/FT50顶刊扫描最新论文，翻译摘要后推送到Idea Scout App供手动筛选（Idea Scout）"
---

# Idea Scout — 顶刊 Idea 迁移雷达

> Scanner scripts: [idea-scout/pipeline](https://github.com/zylen97/idea-scout)

从 25 本 UTD24/FT50 顶级期刊中，扫描最新论文摘要，批量翻译为中文，推送到 Idea Scout App（GitHub Pages PWA）供用户在手机上浏览、筛选。

**核心逻辑**：Skill = 数据管线（获取+翻译+推送），App = 浏览器/选择器（用户手动筛选）。

**输入** `$ARGUMENTS`：格式灵活，示例：
- `/idea-scout` — 交互式选择
- `/idea-scout scan` — 扫描全部 25 本期刊
- `/idea-scout scan MS,OR,MSOM` — 只扫描指定期刊
- `/idea-scout scan A` — 只扫描 A 类（Ops & IS）
- `/idea-scout 博弈` — 关键词定向搜索
- `/idea-scout status` — 查看扫描记录

---

## 步骤 0：加载配置

### 0.1 读取期刊注册表和扫描记录

```bash
cat ~/.claude/skills/idea-scout/journals.json
cat ~/.claude/skills/idea-scout/scout_log.json 2>/dev/null || echo "{}"
```

从 `journals.json` 中读取 `openalex_mailto` 用于 polite pool。

### 0.2 解析 `$ARGUMENTS` 路由

| 输入 | 路由 |
|:-----|:-----|
| 空 / 无参数 | → 交互式菜单 |
| `status` / `记录` | → Route S（查看扫描记录） |
| `scan` + 可选期刊ID/类别(A/B/C) | → Route A（批量扫描最新论文） |
| 关键词如 `博弈` `优化` `网络` | → Route B（关键词定向搜索） |

### 0.3 交互式菜单（无参数时）

AskUserQuestion：
```
🔭 顶刊 Idea 迁移雷达

25 本 UTD24/FT50 期刊（9+4+12）：

A - Ops & IS（运营与信息系统，9本）：
  MS · OR · MSOM · POM · JOM · JSCM · DS · ISR · MISQ

B - Econ & Strategy（经济与战略，4本）：
  AER · SMJ · RP · JIBS

C - Org & Management（组织与管理，12本）：
  AMJ · AMR · ASQ · OS · JMS · JBE · JBV · OBHDP · OrgStudies · JAP · HR · JOM2

(1) 扫描全部 25 本（默认最近 5 天）
(2) 按类别 — 输入 "A" 或 "A,B"
(3) 指定期刊 — 输入 "MS,OR,MSOM"
(4) 关键词搜索 — 输入如 "博弈" "contract"
(5) 查看扫描记录

选择：
```

---

## Route S：查看扫描记录

读取 `scout_log.json`，格式化输出。

---

## Route A：批量扫描最新论文

### 1. 确定目标期刊和时间范围

根据用户选择确定 `target_journals`，默认最近 5 天（自动扫描脚本使用 `-v-5d`）。手动执行时可指定更长时间范围。

### 2. 调用扫描器

使用 scanner 脚本批量拉取 + 翻译：

```bash
cd ~/Library/CloudStorage/Dropbox/04-Coding/idea_scout
source ~/.claude/scheduled/email-config.sh
export CHATANYWHERE_API_KEY

python3 ~/Library/CloudStorage/Dropbox/04-Coding/idea_scout/pipeline/scanners/openalex_scanner.py \
    --config ~/.claude/skills/idea-scout/journals.json \
    --from "{start_date}" --to "{end_date}" \
    --output data/latest.json
```

scanner 自动处理：OpenAlex API 拉取 → 摘要重建 → ChatAnywhere 并发翻译（50线程）→ 输出 JSON。

### 4. 保存数据

将论文数据保存为 JSON：

```bash
# 保存到 Dropbox（归档）
cp data.json ~/Library/CloudStorage/Dropbox/02-Research/papers/idea_scout/scout_{YYYY-MM-DD}_data.json

# 保存到 App 仓库（用于部署）
cp data.json ~/Library/CloudStorage/Dropbox/04-Coding/idea_scout/data/latest.json
```

### 5. 推送到 GitHub → App 自动更新

Flutter App 已预构建并部署在 gh-pages 分支，交互式扫描只需更新数据文件，不需要重建 App。

```bash
cd ~/Library/CloudStorage/Dropbox/04-Coding/idea_scout

# 提交数据到 main 分支
git add data/latest.json data/papers.json data/seen_dois.json
git commit -m "scout: {date} - {N} papers from {journals}"
git push origin main

# 部署到 gh-pages（只更新数据，不重建 Flutter）
mkdir -p /tmp/idea_scout_all_data
cp data/*.json /tmp/idea_scout_all_data/
git checkout gh-pages
cp /tmp/idea_scout_all_data/*.json data/
git add data/
git commit -m "data: ft50 {date}"
git push origin gh-pages
git checkout main
rm -rf /tmp/idea_scout_all_data
```

**推送完成后，App 会在 1-2 分钟内自动加载最新数据。**

### 6. 更新扫描记录

将本次扫描结果写入 `~/.claude/skills/idea-scout/scout_log.json`。

### 7. 完成提示

```
✅ 扫描完成

📊 本次扫描:
  期刊: {N} 本 | 论文: {M} 篇 | 已翻译
  时间范围: {start} ~ {end}

📱 App 已更新: https://zylen97.github.io/idea-scout/
  打开 App → 浏览/筛选 → 勾选感兴趣的 → Export

📂 数据归档: ~/...idea_scout/scout_{date}_data.json

💡 后续:
  1. 在 App 中筛选，Export 选中论文的 JSON
  2. 将 JSON 保存到 idea_scout/selected.json
  3. 运行 /idea-mine 对选中论文做迁移分析
```

---

## Route B：关键词定向搜索

### 1. 解析关键词

中文自动映射为英文搜索词：

| 中文 | 英文搜索词 |
|:-----|:---------|
| 博弈 | game theory, mechanism design, contract, incentive |
| 优化 | optimization, scheduling, resource allocation |
| 网络 | network, graph, centrality, community |
| 供应链 | supply chain, procurement, logistics |
| ESG/可持续 | ESG, sustainability, corporate social responsibility |
| 平台 | platform, two-sided market, matching |
| 韧性 | resilience, disruption, robustness |
| 合同 | contract, principal-agent, incentive |

### 2. OpenAlex 搜索

```bash
curl -s "https://api.openalex.org/works?filter=primary_location.source.id:{id1}|{id2}|...,from_publication_date:{start}&search={keywords}&per_page=50&mailto=zylenw97@usts.edu.cn"
```

默认搜索最近 1 年。

### 3. 翻译 + 推送

同 Route A 步骤 3-6。

---

## 数据流架构

```
/idea-scout (Claude Code)                    App (手机/电脑)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OpenAlex 获取论文 ─┐
                   ├→ data/latest.json ──→ 加载显示
ChatAnywhere 翻译 ─┘
                                            浏览/搜索/筛选
git push → GitHub Pages                     勾选论文 → Export
                                                ↓
                                            selected.json
                                                ↓
                                         /idea-mine 迁移分析
```

### App 仓库
- GitHub: `zylen97/idea-scout`
- 本地: `~/Library/CloudStorage/Dropbox/04-Coding/idea_scout/`
- Pages URL: `https://zylen97.github.io/idea-scout/`
- 数据文件: FT50 `data/latest.json` + `papers.json`，CE/PM `data/cepm_*.json`，CNKI `data/cnki_latest.json`

### 数据存储
- **实时数据**: `~/Library/CloudStorage/Dropbox/04-Coding/idea_scout/data/latest.json` → 推送到 GitHub → App 加载
- **归档数据**: `~/Library/CloudStorage/Dropbox/02-Research/papers/idea_scout/scout_{date}_data.json`
- **用户选择**: App 中勾选 → Export JSON → 保存为 `idea_scout/selected.json`
- **扫描记录**: `~/.claude/skills/idea-scout/scout_log.json`

---

## OpenAlex API 技术细节

### Base URL
```
https://api.openalex.org/works
```

### 常用 filter 参数
```
primary_location.source.id:{source_id}     # 期刊
from_publication_date:{YYYY-MM-DD}          # 起始日期
type:article                                # 只要论文
```

### 多期刊查询
```
primary_location.source.id:S33323087|S125775545|S81410195
```

### 分页
```
per_page=50&cursor=*              # 首页
per_page=50&cursor={next_cursor}  # 后续页
```

### Polite Pool
所有请求带 `&mailto=zylenw97@usts.edu.cn`。

### 速率控制
- 请求间隔 ≥ 0.3 秒
- 单次最多 per_page=200（建议 50）

---

## 全局约束

### 职责分离
- **Skill 只做数据管线**：获取 → 翻译 → 推送。不做 AI 评估、不筛选、不排序。
- **App 只做浏览/选择**：加载数据 → 搜索/筛选 → 用户勾选 → 导出。
- **用户自己决定**哪些论文有迁移潜力，不替代用户的学术判断。

### 不越界
- 不自动下载非 OA 论文
- 不修改任何项目文件
- API Key 只在 Skill 端使用，不暴露到 App 前端

### 跨 Skill 关系
- `/idea-scout` 输出 → 用户在 App 筛选 → Export `selected.json` → `/idea-mine` 深度挖掘
- `/idea-scout` 的期刊库是 idea 来源（顶刊），`/idea-mine` 的期刊库是发表目标（领域刊）
- 扫描已通过 launchd 自动化（每日 9:00 触发 `idea-scout-daily.sh`），无需手动调度
