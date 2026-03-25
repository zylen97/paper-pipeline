#!/usr/bin/env python3
"""
dispatch_plan.py — SubAgent 调度计划生成器（共用）

扫描文件 → 计数条目 → 按 AGENT_ITEM_LIMIT 拆分 → 生成调度表。
供 lit-review / lit-tag / lit-pool 三个 skill 共用。

模式:
    ris     — 扫描 RIS 文件，计数 TY 行（lit-review 用）
    report  — 扫描 direction reports，计数入选文献行（lit-tag 用）
    pool    — 读取 pool_prepare.py 输出的 JSON（备用模式，lit-pool 默认由 pool_prepare.py 内部调度）

用法:
    # lit-review: 扫描 RIS 文件
    python3 dispatch_plan.py --mode ris \
        --input-dir structure/2_literature/ \
        --plan-file structure/2_literature/literature_search_plan.md \
        --limit 30

    # lit-tag: 扫描 direction reports
    python3 dispatch_plan.py --mode report \
        --input-dir structure/2_literature/ \
        --limit 30

    # lit-pool: 读取 pool JSON
    python3 dispatch_plan.py --mode pool \
        --pool-json structure/2_literature/_pool_prepare.json \
        --limit 30

输出:
    stdout — 调度表 markdown + 校验摘要
    JSON — dispatch_plan.json（供主 Agent 读取调度信息）
"""

import argparse
import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path


AGENT_ITEM_LIMIT = 30
MAX_CONCURRENT = 8


# ---------------------------------------------------------------------------
# Mode: ris — 扫描 RIS 文件
# ---------------------------------------------------------------------------

def scan_ris(input_dir: str, plan_file: str | None, directions_filter: list[int] | None) -> list[dict]:
    """扫描 RIS 文件，返回每个方向的信息。"""
    ris_dir = Path(input_dir)
    items = []

    # 读取 plan 文件提取配额（如有）
    quotas = {}
    if plan_file:
        try:
            with open(plan_file, encoding="utf-8") as f:
                content = f.read()
            for m in re.finditer(r"\|\s*D?(\d+)\s*\|[^|]+\|[^|]+\|[^|]+\|\s*(\d+)篇\s*\|", content):
                quotas[int(m.group(1))] = int(m.group(2))
        except Exception:
            pass

    for fp in sorted(ris_dir.glob("*.ris")):
        # 从文件名提取方向编号（如 1_xxx.ris 或 1-xxx.ris）
        m = re.match(r"(\d+)[_\-]", fp.name)
        if not m:
            continue
        d = int(m.group(1))
        if directions_filter and d not in directions_filter:
            continue

        # 计数 TY 行
        try:
            with open(fp, encoding="utf-8-sig") as f:
                content = f.read()
            count = len(re.findall(r"^TY  - ", content, re.MULTILINE))
        except Exception:
            count = 0

        items.append({
            "direction": d,
            "source_file": fp.name,
            "item_count": count,
            "quota": quotas.get(d, 0),
        })

    return items


# ---------------------------------------------------------------------------
# Mode: report — 扫描 direction reports
# ---------------------------------------------------------------------------

def scan_reports(input_dir: str, directions_filter: list[int] | None) -> list[dict]:
    """扫描 direction reports，计数入选文献。"""
    report_dir = Path(input_dir)
    items = []

    for fp in sorted(report_dir.glob("direction*_report.md")):
        # 提取方向编号
        m = re.match(r"direction(\d+)", fp.name)
        if not m:
            continue
        d = int(m.group(1))
        if directions_filter and d not in directions_filter:
            continue

        try:
            with open(fp, encoding="utf-8") as f:
                content = f.read()
        except Exception:
            continue

        # 计数表格行（| 数字 | 开头的行 = 文献条目）
        count = len(re.findall(r"^\|\s*\d+\s*\|", content, re.MULTILINE))

        items.append({
            "direction": d,
            "source_file": fp.name,
            "item_count": count,
        })

    return items


# ---------------------------------------------------------------------------
# Mode: pool — 读取 pool_prepare.py 输出
# ---------------------------------------------------------------------------

def scan_pool(pool_json: str) -> list[dict]:
    """读取 pool_prepare.py 的输出 JSON，按标签分组。"""
    try:
        with open(pool_json, encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"ERROR: Cannot read {pool_json}: {e}", file=sys.stderr)
        sys.exit(1)

    items = []
    for tag_group in data.get("tag_groups", []):
        items.append({
            "tag": tag_group["tag"],
            "item_count": tag_group["count"],
            "source_directions": tag_group.get("source_directions", []),
        })

    return items


# ---------------------------------------------------------------------------
# 通用：拆分 + 贪心合并
# ---------------------------------------------------------------------------

def split_items(items: list[dict], limit: int) -> list[dict]:
    """对每个 item 按 limit 拆分，返回 agent 任务列表。"""
    agents = []
    agent_id = 1

    for item in items:
        count = item["item_count"]
        if count == 0:
            continue

        n_agents = math.ceil(count / limit)
        per_agent = math.ceil(count / n_agents)

        for i in range(n_agents):
            start = i * per_agent + 1
            end = min((i + 1) * per_agent, count)
            actual = end - start + 1

            agent = {
                "agent_id": agent_id,
                "item_range": f"{start}-{end}",
                "item_count": actual,
                "split_info": f"{i + 1}/{n_agents}" if n_agents > 1 else "独立",
            }
            # 复制 item 的元信息
            for key in ["direction", "source_file", "quota", "tag", "source_directions"]:
                if key in item:
                    agent[key] = item[key]

            # 按比例分配配额（如有）
            if "quota" in item and item["quota"] > 0:
                agent["quota_share"] = math.ceil(item["quota"] / n_agents)

            agents.append(agent)
            agent_id += 1

    return agents


def greedy_merge_small(agents: list[dict], limit: int) -> list[dict]:
    """贪心合并小任务（仅用于 pool 模式）。
    将 item_count ≤ limit/2 的 agent 尝试合并到一个 agent 中。"""
    small = [a for a in agents if a["item_count"] <= limit // 2]
    large = [a for a in agents if a["item_count"] > limit // 2]

    if not small:
        return agents

    # 按 item_count 降序排列，贪心装箱
    small.sort(key=lambda x: x["item_count"], reverse=True)
    bins: list[list[dict]] = []
    bin_sums: list[int] = []

    for item in small:
        placed = False
        for i, s in enumerate(bin_sums):
            if s + item["item_count"] <= limit:
                bins[i].append(item)
                bin_sums[i] += item["item_count"]
                placed = True
                break
        if not placed:
            bins.append([item])
            bin_sums.append(item["item_count"])

    # 将合并的 bins 转为 merged agents
    merged = list(large)
    agent_id = max((a["agent_id"] for a in agents), default=0) + 1

    for bin_items in bins:
        if len(bin_items) == 1:
            merged.append(bin_items[0])
        else:
            tags = []
            total = 0
            dirs = []
            for item in bin_items:
                if "tag" in item:
                    tags.append(item["tag"])
                total += item["item_count"]
                if "source_directions" in item:
                    dirs.extend(item["source_directions"])
            merged.append({
                "agent_id": agent_id,
                "tag": "+".join(tags),
                "item_count": total,
                "split_info": "合并",
                "source_directions": sorted(set(dirs)),
                "merged_from": [i["agent_id"] for i in bin_items],
            })
            agent_id += 1

    # 重新编号
    for i, a in enumerate(merged, 1):
        a["agent_id"] = i

    return merged


# ---------------------------------------------------------------------------
# 校验
# ---------------------------------------------------------------------------

def verify(items: list[dict], agents: list[dict], limit: int) -> list[str]:
    """内建校验。"""
    errors = []

    # 1. 每个 agent 不超过 limit
    for a in agents:
        if a["item_count"] > limit:
            errors.append(f"OVER_LIMIT: Agent#{a['agent_id']} has {a['item_count']} items > {limit}")

    # 2. 总条目数一致（非合并模式）
    total_items_input = sum(i["item_count"] for i in items)
    total_items_agents = sum(a["item_count"] for a in agents)
    if total_items_agents != total_items_input:
        errors.append(f"COUNT_MISMATCH: input={total_items_input}, agents={total_items_agents}")

    # 3. 每个方向/标签至少 1 个 agent
    # (对 ris/report 模式检查方向，对 pool 模式检查标签)
    input_keys = set()
    agent_keys = set()
    for i in items:
        if i["item_count"] > 0:
            key = i.get("direction") or i.get("tag")
            if key:
                input_keys.add(str(key))
    for a in agents:
        key = a.get("direction") or a.get("tag", "")
        for k in str(key).split("+"):
            agent_keys.add(k)
    missing = input_keys - agent_keys
    if missing:
        errors.append(f"MISSING_COVERAGE: {missing} not assigned to any agent")

    return errors


# ---------------------------------------------------------------------------
# 模板生成（模板填空 + 结构分离）
# ---------------------------------------------------------------------------

# 模板内容：Agent 只需在下方按格式添加条目，不写任何标题行或元数据。
# Python 负责结构（section headers、元数据、淘汰摘要）。

TEMPLATE_RIS = """\
（逐条添加入选文献，严格按以下格式。无入选则只写"无"。不要添加任何 ## 标题行、元数据行或淘汰记录。）

### 入选1
- 级别: {{核心/重要/备选}}
- 作者: {{第一作者姓}}
- 标题: {{完整英文标题}}
- 年份: {{4位数字}}
- 期刊: {{从RIS文件原样复制完整期刊名，不要缩写}}
- 理由: {{中文，含摘要具体信息}}
"""

TEMPLATE_TAG = """\
（在每行 → 后填写标签，用+分隔多标签，如 LR+GAP-RQ1。不要修改序号和 → 前的内容。）

{sections}"""


def _count_tiers_in_report(report_path: Path) -> dict[str, int]:
    """从 direction report 中统计每个 tier 的文献行数。"""
    if not report_path.exists():
        return {}
    try:
        content = report_path.read_text(encoding="utf-8")
    except Exception:
        return {}

    tier_counts: dict[str, int] = {}
    current_tier = None

    for line in content.split("\n"):
        if re.match(r"^##\s.*核心文献", line):
            current_tier = "核心文献"
            tier_counts[current_tier] = 0
        elif re.match(r"^##\s.*重要文献", line):
            current_tier = "重要文献"
            tier_counts[current_tier] = 0
        elif re.match(r"^##\s.*备选文献", line):
            current_tier = "备选文献"
            tier_counts[current_tier] = 0
        elif re.match(r"^##\s.*淘汰", line):
            current_tier = None
        elif current_tier and re.match(r"^\|\s*\d+\s*\|", line):
            tier_counts[current_tier] = tier_counts.get(current_tier, 0) + 1

    return tier_counts


def generate_templates(agents: list[dict], template_dir: str, mode: str):
    """为每个 agent 生成模板文件。"""
    tpl_dir = Path(template_dir)
    tpl_dir.mkdir(parents=True, exist_ok=True)

    count = 0
    skipped = 0
    if mode == "ris":
        for a in agents:
            d = a.get("direction", 0)
            batch = a["split_info"].split("/")[0] if "/" in a.get("split_info", "") else "1"
            filename = f"d{d}_batch{batch}_raw.md"
            filepath = tpl_dir / filename
            # Safety: skip if file exists and contains agent output (not just template)
            if filepath.exists():
                existing = filepath.read_text(encoding="utf-8")
                if "### 入选" in existing and "- 级别:" in existing:
                    skipped += 1
                    continue
            filepath.write_text(TEMPLATE_RIS, encoding="utf-8")
            count += 1

    elif mode == "report":
        # lit-tag: 从 direction report 提取每个 tier 的文献数量，生成带序号的模板
        # 需要读取 source_file（direction report）解析 tier 结构
        for a in agents:
            d = a.get("direction", 0)
            batch = a["split_info"].split("/")[0] if "/" in a.get("split_info", "") else "1"
            source = a.get("source_file", "")

            # 尝试从 report 文件读取 tier 结构
            tier_counts = _count_tiers_in_report(tpl_dir.parent / source) if source else {}

            # 生成模板
            sections = []
            for tier_name in ["核心文献（Core）", "重要文献（Important）", "备选文献（Backup）"]:
                tier_key = tier_name.split("（")[0].strip()  # 核心文献/重要文献/备选文献
                n = tier_counts.get(tier_key, 0)
                sections.append(f"## {tier_name}")
                if n > 0:
                    for i in range(1, n + 1):
                        sections.append(f"{i} → ")
                else:
                    sections.append("（无）")
                sections.append("")

            content = "（在每行 → 后填写标签，用+分隔多标签，如 LR+GAP-RQ1。不要修改序号和 → 前的内容。）\n\n"
            content += "\n".join(sections)

            filename = f"d{d}_tags.md"
            filepath = tpl_dir / filename
            # Safety: skip if file exists and contains filled tags (not just template)
            if filepath.exists():
                existing = filepath.read_text(encoding="utf-8")
                if re.search(r"\d+\s*→\s*\S+", existing):
                    skipped += 1
                    continue
            filepath.write_text(content, encoding="utf-8")
            count += 1

    if skipped:
        print(f"Templates generated: {count} files, skipped {skipped} (existing agent output) in {tpl_dir}", file=sys.stderr)
    else:
        print(f"Templates generated: {count} files in {tpl_dir}", file=sys.stderr)


def split_ris_chunks(items_summary: list[dict], agents: list[dict],
                     input_dir: str, template_dir: str):
    """Split RIS files into per-agent chunk files under _chunks/."""
    chunks_dir = Path(template_dir) / "_chunks"
    chunks_dir.mkdir(parents=True, exist_ok=True)

    # group agents by direction
    dir_agents: dict[int, list[dict]] = defaultdict(list)
    for a in agents:
        dir_agents[a["direction"]].append(a)

    count = 0
    errors = []
    for item in items_summary:
        d = item["direction"]
        ris_path = Path(input_dir) / item["source_file"]
        content = ris_path.read_text(encoding="utf-8-sig")
        entries = re.split(r"(?=^TY  - )", content, flags=re.MULTILINE)
        entries = [e for e in entries if e.strip() and e.strip().startswith("TY  -")]

        for a in dir_agents.get(d, []):
            start, end = map(int, a["item_range"].split("-"))
            chunk = entries[start - 1:end]
            batch_num = a["split_info"].split("/")[0]
            chunk_path = chunks_dir / f"d{d}_batch{batch_num}.ris"
            chunk_path.write_text("\n".join(chunk), encoding="utf-8")
            count += 1

            # verify chunk entry count
            actual = sum(1 for line in chunk_path.read_text(encoding="utf-8").split("\n")
                         if line.startswith("TY  - "))
            if actual != a["item_count"]:
                errors.append(f"d{d}_batch{batch_num}: expected {a['item_count']}, got {actual}")

    if errors:
        print(f"Chunks generated: {count} files (with {len(errors)} ERRORS)", file=sys.stderr)
        for e in errors:
            print(f"  ❌ {e}", file=sys.stderr)
    else:
        print(f"Chunks generated: {count} files in {chunks_dir}", file=sys.stderr)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Generate SubAgent dispatch plan")
    parser.add_argument("--mode", required=True, choices=["ris", "report", "pool"],
                        help="Scan mode")
    parser.add_argument("--input-dir", default=None,
                        help="Directory to scan (ris/report modes)")
    parser.add_argument("--plan-file", default=None,
                        help="literature_search_plan.md path (ris mode)")
    parser.add_argument("--pool-json", default=None,
                        help="pool_prepare.py output JSON (pool mode)")
    parser.add_argument("--limit", type=int, default=AGENT_ITEM_LIMIT,
                        help=f"Agent item limit (default: {AGENT_ITEM_LIMIT})")
    parser.add_argument("--directions", default=None,
                        help="Comma-separated direction numbers to process (e.g., 1,3,5)")
    parser.add_argument("--merge-small", action="store_true",
                        help="Greedy-merge small tasks (pool mode)")
    parser.add_argument("--output", default=None,
                        help="Output JSON path")
    parser.add_argument("--template-dir", default=None,
                        help="Generate entry-only template files for agents (ris/report modes)")
    args = parser.parse_args()

    # 解析方向过滤
    dir_filter = None
    if args.directions:
        dir_filter = [int(x.strip()) for x in args.directions.split(",")]

    # 扫描
    if args.mode == "ris":
        if not args.input_dir:
            print("ERROR: --input-dir required for ris mode", file=sys.stderr)
            sys.exit(1)
        items = scan_ris(args.input_dir, args.plan_file, dir_filter)
    elif args.mode == "report":
        if not args.input_dir:
            print("ERROR: --input-dir required for report mode", file=sys.stderr)
            sys.exit(1)
        items = scan_reports(args.input_dir, dir_filter)
    elif args.mode == "pool":
        if not args.pool_json:
            print("ERROR: --pool-json required for pool mode", file=sys.stderr)
            sys.exit(1)
        items = scan_pool(args.pool_json)

    if not items:
        print("ERROR: No items found to dispatch", file=sys.stderr)
        sys.exit(1)

    # 拆分（report 模式不拆分，每方向1个 agent——模板按方向生成，拆分会导致多 agent 写同一文件）
    if args.mode == "report":
        effective_limit = max(i["item_count"] for i in items) + 1
    else:
        effective_limit = args.limit
    agents = split_items(items, effective_limit)

    # 贪心合并（仅 pool 模式）
    if args.merge_small and args.mode == "pool":
        agents = greedy_merge_small(agents, args.limit)

    # 校验（report 模式用 effective_limit，避免误报 OVER_LIMIT）
    errors = verify(items, agents, effective_limit)

    # 输出 JSON
    output_path = args.output
    if not output_path:
        if args.input_dir:
            output_path = str(Path(args.input_dir) / "_dispatch_plan.json")
        elif args.pool_json:
            output_path = str(Path(args.pool_json).parent / "_dispatch_plan.json")
        else:
            output_path = "_dispatch_plan.json"

    output_data = {
        "mode": args.mode,
        "agent_item_limit": args.limit,
        "max_concurrent": MAX_CONCURRENT,
        "total_items": sum(i["item_count"] for i in items),
        "total_agents": len(agents),
        "items_summary": items,
        "agents": agents,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    # ===== 生成模板文件（如指定） =====
    if args.template_dir:
        generate_templates(agents, args.template_dir, args.mode)

    # ===== RIS chunk 拆分（ris 模式 + 有 template-dir 时自动执行） =====
    if args.mode == "ris" and args.template_dir and args.input_dir:
        split_ris_chunks(items, agents, args.input_dir, args.template_dir)

    # ===== stdout 结构化摘要 =====
    print(f"=== DISPATCH PLAN ({args.mode.upper()}) ===")
    print(f"Items scanned: {len(items)}")
    print(f"Total entries: {sum(i['item_count'] for i in items)}")
    print(f"Agent limit: {args.limit}")
    print(f"Total agents: {len(agents)}")
    print(f"Max concurrent: {MAX_CONCURRENT}")
    print()

    # 输入摘要
    print("Input summary:")
    for item in items:
        label = f"D{item['direction']}" if "direction" in item else item.get("tag", "?")
        extra = f" (quota: {item['quota']})" if item.get("quota") else ""
        print(f"  {label}: {item['item_count']} items{extra}")
    print()

    # 调度表
    if args.mode in ("ris", "report"):
        print("| Agent# | 方向 | 条目范围 | 条目数 | 拆分 |")
        print("|:------:|:-----|:---------|:------:|:----:|")
        for a in agents:
            print(f"| {a['agent_id']} | D{a.get('direction', '?')} | {a.get('item_range', '-')} | {a['item_count']} | {a['split_info']} |")
    else:
        print("| Agent# | 标签 | 条目数 | 拆分 |")
        print("|:------:|:-----|:------:|:----:|")
        for a in agents:
            print(f"| {a['agent_id']} | {a.get('tag', '?')} | {a['item_count']} | {a['split_info']} |")
    print()

    # 校验结果
    if errors:
        print("=== VERIFY: FAIL ===")
        for e in errors:
            print(f"  ❌ {e}")
        sys.exit(1)
    else:
        print("=== VERIFY: PASS ===")
        print(f"Output: {output_path}")


if __name__ == "__main__":
    main()
