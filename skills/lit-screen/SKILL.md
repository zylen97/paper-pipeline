---
description: "WoS 文献批量筛选：XR2026 新锐分区过滤 + LLM 相关性筛选，/lit-plan 和 /lit-review 之间的预处理步骤"
argument-hint: "<RIS文件路径> <研究方向>"
allowed-tools: Bash(python3 *) Bash(source *) Bash(mv *) Read
---

# lit-screen — 文献批量筛选

## 核心使命

对 WoS 导出的 RIS 文件进行两步筛选：
1. **XR2026 新锐分区过滤**（零成本，自动执行）：按 ISSN 匹配大类分区，过滤低区期刊
2. **LLM 相关性筛选**（有 API 成本，用户决定）：用 gpt-4o-mini 逐篇判断是否与研究方向相关

位于 `/lit-plan`（生成检索式）和 `/lit-review`（生成方向报告）之间。

## 输入

- `$ARGUMENTS` 格式：`<RIS文件路径> <研究方向>`
- 研究方向可以从项目 `idea.md` 中提取（如果用户在项目目录下运行且未指定）

## 执行流程

### Step 0: 解析参数

从 `$ARGUMENTS` 中提取：
- **ris_path**：RIS 文件的绝对路径
- **direction**：研究方向关键词（如 "博弈论"、"供应链韧性"）

如果用户只给了 RIS 路径没给方向，从当前项目的 `idea.md` 提取研究主题。
如果都没给，AskUserQuestion 询问。

### Step 1: XR2026 新锐分区过滤（自动执行）

运行脚本：

```bash
python3 ~/.claude/skills/lit-screen/screen_xr.py "<ris_path>" --zone 2
```

脚本输出 JSON 到 stdout，包含：
- `original`：原始文献总数
- `zone_distribution`：各分区数量（1区/2区/3区/4区/未匹配）
- `kept`：匹配到的 1-2 区文献数
- `unmatched`：ISSN 未匹配数（默认保留）
- `kept_with_unmatched`：保留总数（匹配 + 未匹配）
- `removed`：被过滤的文献数
- `output_path`：筛选后 RIS 文件路径

**向用户汇报（必须包含以下信息）：**

```
XR2026 新锐分区筛选结果：

| 分区 | 数量 |
|------|------|
| 1 区 | xxx  |
| 2 区 | xxx  |
| 3 区 | xxx  |
| 4 区 | xxx  |
| 未匹配 | xxx |
| **合计** | **xxx** |

保留 1-2 区 + 未匹配 → xxx 篇
过滤掉 3-4 区 → xxx 篇
筛选后 RIS：<output_path>
```

### Step 2: 用户决策

展示 Step 1 结果后，AskUserQuestion **一次性**询问用户：

> XR2026 分区筛选结果如上。请决定：
> 1. **分区筛选**：应用（保留 1-2 区）还是跳过（保留全部）？
> 2. **LLM 相关性筛选**：是否继续？（预估成本：每 1000 篇约 $0.075，用 gpt-4o-mini）

根据用户回答确定 **后续输入 RIS**：
- 应用分区 → 后续以 `_zone2.ris` 为基础
- 跳过分区 → 后续以原始 RIS 为基础
- 不跑 LLM → **仍需进入 Step 4 归档**（若用户应用了分区，`_zone2.ris` 与原始 `.ris` 共存会导致 /lit-review glob 冲突；只有"跳过分区 + 不跑 LLM"才无冲突可直接结束）
- 跑 LLM → 进入 Step 3，输入为上面确定的 RIS

### Step 3: LLM 相关性筛选（用户确认后执行）

读取 API Key：

```bash
source ~/Library/CloudStorage/Dropbox/Apps/secrets-vault/email-config.sh && echo $CHATANYWHERE_API_KEY
```

运行脚本：

```bash
# <INPUT_RIS> = Step 2 用户决策后确定的输入 RIS（应用分区→*_zone2.ris；跳过分区→原始.ris）
source ~/Library/CloudStorage/Dropbox/Apps/secrets-vault/email-config.sh && \
python3 ~/.claude/skills/lit-screen/screen_llm.py "<INPUT_RIS>" \
  --direction "<direction>" \
  --api-key "$CHATANYWHERE_API_KEY" \
  --threads 20
```

脚本输出 JSON 到 stdout，包含：
- `input`：输入文献数
- `relevant`：相关文献数
- `irrelevant`：不相关文献数
- `errors`：API 调用失败数
- `output_path`：筛选后 RIS 文件路径
- `removed_titles`：被移除的论文标题列表（最多 30 篇）

**向用户汇报：**

```
LLM 相关性筛选结果（方向：{direction}）：

输入：xxx 篇
相关：xxx 篇 ✓
不相关：xxx 篇 ✗
错误：xxx 篇（已默认保留）

筛选后 RIS：<output_path>
```

如果有被移除的论文，列出前 10 篇的标题供用户快速检查。

### Step 4: 总结 + 归档原始 RIS（建议操作，需用户确认）

**⚠️ 下游保护**：`/lit-review` 的 `dispatch_plan.py` 用 `ris_dir.glob("*.ris")` 扫描方向文件，如果原始 `{stem}.ris` 和筛选后的 `{stem}_zone2.ris` / `{stem}_llm.ris` 共存于同一目录，会被视为不同批次并**重复消费**，造成配额超额与重复打标。

**归档操作**：先执行以下 bash 赋值**计算 `${RIS_DIR}`**（必做，下文命令全部依赖此变量；不硬编码 `structure/2_literature/`——用户可能把 RIS 放在任意位置）：

```bash
# <FINAL_RIS> = 本次筛选链路最终产出的 RIS（跑了 LLM → *_llm.ris；未跑 → *_zone2.ris；两者皆跳 → 原始.ris）
# 注意：必须在同一个 bash 块内使用 ${RIS_DIR} 和 ${STEM}，跨 Bash 工具调用变量会丢失
RIS_DIR=$(dirname "<FINAL_RIS>")
STEM_ORIG=$(basename "<FINAL_RIS>" | sed -E 's/(_zone2|_llm)?\.ris$//')
echo "RIS 所在目录: $RIS_DIR, 原始 stem: $STEM_ORIG"
```

然后 AskUserQuestion 确认：

```
检测到原始 RIS: ${RIS_DIR}/${STEM_ORIG}.ris
与 /lit-review 的 glob *.ris 冲突，建议归档。选择：
  (1) 归档到 ${RIS_DIR}/_raw/（推荐，保留备份）
  (2) 改为 .ris.bak 后缀
  (3) 保留原状（⚠️ /lit-review 会把 ${STEM_ORIG}.ris 和 <FINAL_RIS> 都扫进去，配额/去重逻辑会按两批独立文献处理，实际等于双倍打标）
```

用户选 (1)（同一 bash 块内执行，避免 ${RIS_DIR}/${STEM_ORIG} 丢失）：
```bash
mkdir -p "${RIS_DIR}/_raw" && mv "${RIS_DIR}/${STEM_ORIG}.ris" "${RIS_DIR}/_raw/"
# 若有中间产物 _zone2.ris（非最终），也归档：
[ -f "${RIS_DIR}/${STEM_ORIG}_zone2.ris" ] && [ "<FINAL_RIS>" != "${RIS_DIR}/${STEM_ORIG}_zone2.ris" ] && mv "${RIS_DIR}/${STEM_ORIG}_zone2.ris" "${RIS_DIR}/_raw/"
```

用户选 (2)：
```bash
mv "${RIS_DIR}/${STEM_ORIG}.ris" "${RIS_DIR}/${STEM_ORIG}.ris.bak"
```

用户选 (3)：不动，在完成提示中复述冲突机制：`/lit-review` 对 `${STEM_ORIG}.ris` 和 `<FINAL_RIS>` 会各自消费一遍配额，并造成重复打标。

（`_zone2.ris` 作为中间产物若不再需要，选 (1) 自动一并归档；只保留**最终 RIS**供 /lit-review 消费。）

汇报完整筛选链路：

```
筛选完成：
原始 → xxx 篇
  ↓ XR2026 分区过滤（1-2区）
xxx 篇
  ↓ LLM 相关性筛选（{direction}）
xxx 篇 ← 最终结果

输出文件：<FINAL_RIS>
原始 RIS 已归档至：${RIS_DIR}/_raw/${STEM_ORIG}.ris（用户选 1）或 ${RIS_DIR}/${STEM_ORIG}.ris.bak（用户选 2）；选 3 则原文件保留（⚠️ /lit-review 会重复消费）
可直接用于 /lit-review
```

## 注意事项

- XR2026 中 ISSN 未匹配的论文**默认保留**（可能是新刊、会议论文、或数据库差异）
- LLM 筛选中 API 调用失败的论文**默认保留**（宁可多留不误删）
- LLM prompt 基于六非博 Literature Review Software 7B 改进，支持主题相关和方法相关两种判定
- 不修改原始 RIS 文件，所有输出生成新文件
