---
description: "从UTD24/FT50顶刊扫描最新论文，翻译摘要后推送到Idea Scout App供手动筛选（Idea Scout）"
---

# Idea Scout — 顶刊 Idea 迁移雷达

从 28 本 UTD24/FT50 顶级期刊中，扫描最新论文摘要，批量翻译为中文，推送到 Idea Scout App（GitHub Pages PWA）供用户在手机上浏览、筛选。

**核心逻辑**：Skill = 数据管线（获取+翻译+推送），App = 浏览器/选择器（用户手动筛选）。

**输入** `$ARGUMENTS`：格式灵活，示例：
- `/idea-scout` — 交互式选择
- `/idea-scout scan` — 扫描全部 28 本期刊
- `/idea-scout scan MS,OR,MSOM` — 只扫描指定期刊
- `/idea-scout scan 1` — 只扫描第一梯队
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
| `scan` + 可选期刊ID/梯队号 | → Route A（批量扫描最新论文） |
| 关键词如 `博弈` `优化` `网络` | → Route B（关键词定向搜索） |

### 0.3 交互式菜单（无参数时）

AskUserQuestion：
```
🔭 顶刊 Idea 迁移雷达

28 本 UTD24/FT50 期刊（7+11+10）：

T1（方法直接可迁移，7本）：
  MS · OR · MSOM · POM · JOM · ISR · MISQ

T2（理论/方法框架可迁移，11本）：
  SMJ · OS · AMJ · RP · JMS · JSCM · JBE · AER · ECMA · JIBS · MKS

T3（特定场景可迁移，10本）：
  AMR · ASQ · DS · JBV · ETP · JOM2 · OBHDP · OrgStudies · JAP · HR

(1) 扫描全部 28 本（默认最近 3 个月）
(2) 按梯队 — 输入 "1" 或 "1,2"
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

根据用户选择确定 `target_journals`，默认最近 3 个月。

### 2. OpenAlex API 批量拉取

对每本目标期刊，调用 OpenAlex API 获取论文列表：

```bash
curl -s "https://api.openalex.org/works?filter=primary_location.source.id:{openalex_id},from_publication_date:{start_date},type:article&sort=publication_date:desc&per_page=50&mailto=zylenw97@usts.edu.cn"
```

**摘要重建**：OpenAlex 用 inverted index 格式存储摘要，需重建：
```python
def rebuild_abstract(inverted_index):
    if not inverted_index:
        return ""
    word_positions = []
    for word, positions in inverted_index.items():
        for pos in positions:
            word_positions.append((pos, word))
    word_positions.sort()
    return ' '.join(w for _, w in word_positions)
```

**分页处理**：如结果超过 50 条（`meta.count > 50`），用 `cursor` 分页继续拉取。每次请求间隔 0.3 秒。

**过滤**：去掉无摘要的论文。

**数据格式**（每篇论文）：
```json
{
    "journal_id": "MS",
    "journal_name": "Management Science",
    "title": "...",
    "doi": "https://doi.org/...",
    "date": "2026-04-01",
    "abstract": "...",
    "topics": ["Topic1", "Topic2"],
    "cited_by": 0,
    "oa": true,            // Paper.fromJson 兼容 "oa" 和 "is_oa"
    "pdf_url": "...",
    "tier": 1,
    "title_cn": "",
    "abstract_cn": ""
}
```

### 3. 批量翻译（ChatAnywhere API）

读取 API 配置：
```bash
cat ~/.claude/projects/-Users-zylen/memory/reference_chatanywhere_api.md
```

用 Python 脚本并发翻译标题和摘要：
- API: `https://api.chatanywhere.tech/v1/chat/completions`
- Model: `gpt-4o-mini`
- 并发数: 50（ThreadPoolExecutor）
- System prompt: `你是学术翻译助手。将以下英文学术文本翻译为中文，保持学术术语准确，语言流畅自然。只返回翻译结果。`
- 先翻译所有标题，再翻译所有摘要

翻译后填充 `title_cn` 和 `abstract_cn` 字段。

### 4. 保存数据

将论文数据保存为 JSON：

```bash
# 保存到 Dropbox（归档）
cp data.json ~/Library/CloudStorage/Dropbox/02-Research/Zylen\ paper/idea_scout/scout_{YYYY-MM-DD}_data.json

# 保存到 App 仓库（用于部署）
cp data.json ~/idea_scout/data/latest.json
```

### 5. 推送到 GitHub → App 自动更新

```bash
cd ~/idea_scout

# 提交数据到 main 分支
git add data/latest.json
git commit -m "scout: {date} - {N} papers from {journals}"
git push origin main

# 重新构建并部署到 gh-pages
export PATH="$HOME/develop/flutter/bin:$PATH"
flutter build web --release --base-href "/idea-scout/"

# 把 data 目录也复制到 build 输出
mkdir -p build/web/data
cp data/latest.json build/web/data/

# 部署到 gh-pages
cp -r build/web /tmp/idea_scout_deploy
git stash
git checkout gh-pages
git rm -rf . > /dev/null 2>&1
cp -r /tmp/idea_scout_deploy/* .
touch .nojekyll
git add -A
git commit -m "deploy: {date} scan data"
git push origin gh-pages --force
git checkout main
git stash pop 2>/dev/null || true
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
- 本地: `~/idea_scout/`
- Pages URL: `https://zylen97.github.io/idea-scout/`
- 数据文件: `data/latest.json`（每次扫描覆盖）

### 数据存储
- **实时数据**: `~/idea_scout/data/latest.json` → 推送到 GitHub → App 加载
- **归档数据**: `~/Library/CloudStorage/Dropbox/02-Research/Zylen paper/idea_scout/scout_{date}_data.json`
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
- 可配合 `/schedule` 每月自动扫描
