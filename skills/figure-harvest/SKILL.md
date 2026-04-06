---
description: "定期从目标 Elsevier 期刊批量采集论文图片（Graphical Abstract + 正文 Figure），充实 Eagle 风格参考库（Figure Harvest）"
---

# Figure Harvest — 期刊论文图片批量采集

从 ScienceDirect 期刊批量下载最新论文的高清图片（Graphical Abstract + 正文 Figure），供用户筛选后导入 Eagle 素材库，作为 `/figure` skill 的风格参考源。

**输入** `$ARGUMENTS`：格式灵活，示例：
- `/figure-harvest` — 交互式选择
- `/figure-harvest 建工` — 采集所有 #建工 标签的期刊
- `/figure-harvest AIC` — 只采集 Automation in Construction
- `/figure-harvest status` — 查看采集记录
- `/figure-harvest --all` — 采集全部 21 本期刊（增量，只采新卷期）

---

## 步骤 0：加载配置

### 0.1 读取期刊注册表和采集记录

```bash
cat ~/.claude/skills/figure-harvest/journals.json
cat ~/.claude/skills/figure-harvest/harvest_log.json
```

### 0.2 解析 `$ARGUMENTS` 路由

| 输入 | 路由 |
|:-----|:-----|
| 空 / 无参数 | → 交互式菜单 |
| `status` / `记录` / `查看` | → Route S（查看采集记录） |
| 标签名如 `建工` `智能化` | → 筛选该标签下的期刊，进入 Route H |
| 期刊 ID 如 `AIC` 或逗号分隔 `AIC,AEI` | → 指定期刊，进入 Route H |
| `--all` | → 全部期刊，进入 Route H |

### 0.3 交互式菜单（无参数时）

AskUserQuestion：
```
📚 Elsevier 期刊图片采集

共 21 本 ScienceDirect 期刊可选：

按标签：
  #建工(7)  #智能化(6)  #城市(6)  #可持续(9)
  #工业工程(6)  #项目管理(2)  #创新(3)  #应急(3)

(1) 按标签筛选 — 输入标签如 "建工"
(2) 指定期刊 — 输入 ID 如 "AIC" 或 "AIC,AEI,BAE"
(3) 全部 21 本（增量采集，只采新卷期）
(4) 查看采集记录

选择：
```

---

## Route S：查看采集记录

读取 `harvest_log.json`，格式化输出：

```
📋 采集记录

| 期刊 | 最近采集卷期 | 采集日期 | 论文数 | 图片数 |
|:-----|:------------|:---------|:------|:------|
| AIC  | Vol187_Jul2026 | 2026-04-06 | 25 | 187 |
| AEI  | Vol65_Apr2026  | 2026-04-06 | 18 | 142 |
| ...  | — 未采集 —     |            |    |     |

共采集 X 本期刊 Y 个卷期 Z 张图片
```

---

## Route H：采集流程

### 1. 确定目标期刊列表

根据路由结果确定 `target_journals`（期刊 ID 列表）。

展示确认：
```
📚 本次采集目标（{N} 本期刊）：

1. Advanced Engineering Informatics (AEI)
2. Automation in Construction (AIC)
...

确认开始？
```

### 2. 检查 CDP 环境

```bash
bash ~/.claude/skills/web-access/scripts/check-deps.sh
```

未通过 → 引导用户完成 Chrome CDP 设置。

### 3. 分批并行采集

**节奏控制**：每批最多 **3 本期刊**并行（子 Agent），批间间隔适当，避免触发 ScienceDirect 反爬。

对每一批：启动子 Agent 并行处理，每个子 Agent 负责一本期刊的完整采集流程。

**子 Agent Prompt 模板**：
```
你是期刊图片采集 agent。必须加载 web-access skill 并遵循指引。

任务：从 ScienceDirect 采集期刊 "{journal_name}" 的最新一期论文图片。

期刊 URL: https://www.sciencedirect.com/journal/{slug}

已采集卷期（跳过）：{already_harvested_volumes}

执行步骤：

1. 用 CDP 打开期刊主页，提取最新卷期信息（卷号、期号、月份）
2. 对比已采集记录，如果最新卷期已采集过，报告"无新内容"并结束
3. 提取该卷期所有论文的链接和短标题（用于文件夹命名）
4. 逐篇论文：
   a. 打开论文页面
   b. 滚动到底部触发懒加载
   c. 从 <figure> 元素提取所有图片 URL（els-cdn.com 域名）
   d. 区分 ga（graphical abstract）和 gr（正文 figure）
5. 创建目录结构：
   {output_dir}/{journal_id}/
     {volume_label}/
       paper{NN}_{short_title}/
6. 批量下载图片（curl，使用 _lrg.jpg 高清版）：
   - URL 模式：将 .jpg 替换为 _lrg.jpg（如 gr1.jpg → gr1_lrg.jpg）
   - 如果 _lrg.jpg 返回 404 或文件小于 1KB，回退到 .jpg
7. 完成后关闭所有自己创建的 tab
8. 返回 JSON 格式的采集结果：
   {
     "journal_id": "AIC",
     "volume_label": "Vol187_Jul2026",
     "paper_count": 25,
     "figure_count": 187,
     "papers": [
       {"folder": "paper01_UAV_inspection", "figures": ["ga1.jpg", "gr1.jpg", ...]}
     ]
   }

注意事项：
- 论文短标题：取标题前3-4个有意义的英文单词，snake_case，不超过 40 字符
- paper 编号从 01 开始，按页面出现顺序
- 图片文件名保留原始命名（ga1, gr1, gr2...）
- 每篇论文之间 sleep 1-2 秒，不要太快
- 如果遇到反爬拦截（403/验证码），立即停止并报告
```

### 4. 汇总结果 + 更新记录

所有子 Agent 完成后：

1. **汇总展示**：
```
✅ 采集完成

| 期刊 | 卷期 | 论文数 | 图片数 |
|:-----|:-----|:------|:------|
| AIC  | Vol187_Jul2026 | 25 | 187 |
| AEI  | Vol65_Apr2026  | 18 | 142 |
| ...  |                |    |     |
| 合计  |               | XX | XXX |

📂 图片已保存到: ~/Library/CloudStorage/Dropbox/02-Research/Zylen paper/figure_harvest/
```

2. **更新 `harvest_log.json`**：将每本期刊的新采集记录写入。

3. **提示后续操作**：
```
💡 后续操作：
- 在 Finder 中浏览图片（空格预览），挑选好看的
- 拖入 Eagle 并打标签（如 "框架图""网络图""博弈论""热力图"）
- /figure 创建图时即可从 Eagle 搜索风格参考
```

---

## ScienceDirect 采集技术细节

### URL 规律

| 类型 | URL 模式 |
|:-----|:---------|
| 期刊主页 | `https://www.sciencedirect.com/journal/{slug}` |
| 论文页面 | `https://www.sciencedirect.com/science/article/pii/{PII}` |
| 缩略图 | `https://ars.els-cdn.com/content/image/1-s2.0-{PII}-gr1.sml` |
| 正常图 | `https://ars.els-cdn.com/content/image/1-s2.0-{PII}-gr1.jpg` |
| 高清图 | `https://ars.els-cdn.com/content/image/1-s2.0-{PII}-gr1_lrg.jpg` |
| GA | `https://ars.els-cdn.com/content/image/1-s2.0-{PII}-ga1_lrg.jpg` |

### 页面解析要点

**期刊主页** — 提取论文列表：
```javascript
// 论文链接
document.querySelectorAll('a[href*="article"]')
// 卷期信息
document.querySelector('.js-vol-issue, .issue-item, h2')
```

**论文页面** — 提取图片：
```javascript
// 所有 figure 元素
document.querySelectorAll('figure[id] img')
// 图片 URL 在 els-cdn.com 域名下
// 区分 ga（graphical abstract）和 gr（正文 figure）通过文件名
```

### 反爬注意

- 每篇论文间隔 1-2 秒
- 每批最多 3 本期刊并行
- 批间可适当间隔
- 遇到 403/验证码立即停止，不要重试
- 使用用户 Chrome 的真实 session，天然携带登录态

---

## 全局约束

### 文件规范
- 图片统一存到 `~/Library/CloudStorage/Dropbox/02-Research/Zylen paper/figure_harvest/` 下
- 目录层级：`{期刊ID}/{卷期号}/paper{NN}_{short_title}/`
- 图片文件名保留 ScienceDirect 原始命名（ga1, gr1, gr2...），后缀 .jpg

### 增量采集
- 每次运行前读取 `harvest_log.json`，已采集的卷期跳过
- `harvest_log.json` 是唯一的采集状态记录

### 安全底线
- 遇到反爬拦截立即停止，不做任何绕过
- 不修改 cookies / headers 伪装身份
- 利用用户真实浏览器 session 的合法访问权限

### 跨 Skill 关系
- 采集的图片经用户筛选后导入 Eagle → `/figure` 通过 `eagle_search.py` 搜索风格参考
- 可配合 `/schedule` 设置每周自动运行（增量采集模式）
