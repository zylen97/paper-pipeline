#!/usr/bin/env python3
"""
format_batches.py — Agent 输出格式标准化（lit-review §2.2）

设计原理（模板填空 + 结构分离）：
- Agent 只输出条目级 key-value 块（照模板格式填空），不写任何 section headers
- 本脚本从 _dispatch_plan.json 读取元数据，从 raw.md 读取条目
- 按「级别」字段分组为 core/important/backup
- Section headers、元数据行、表格结构全部由本脚本确定性生成

支持的输入格式（唯一）：
    ### 入选1
    - 级别: 核心
    - 作者: Author Name
    - 标题: Paper Title
    - 年份: 2024
    - 期刊: Journal Name
    - 理由: 入选理由

用法:
    python3 format_batches.py \
        --batch-dir structure/2_literature/_batch/ \
        --plan-json structure/2_literature/_dispatch_plan.json

输出:
    1. 标准化的 d*_batch*.md 文件
    2. stdout 结构化摘要 + VERIFY: PASS|FAIL
"""

import argparse
import json
import re
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# 级别映射
# ---------------------------------------------------------------------------

TIER_MAP = {
    "核心": "core", "core": "core",
    "重要": "important", "important": "important",
    "备选": "backup", "backup": "backup",
    "peripheral": "backup", "alternative": "backup",
}

FIELD_MAP = {
    "级别": "tier", "tier": "tier",
    "作者": "author", "author": "author", "authors": "author",
    "标题": "title", "title": "title",
    "年份": "year", "year": "year",
    "期刊": "journal", "journal": "journal",
    "理由": "reason", "reason": "reason",
}

# 允许但忽略的字段
SKIP_FIELDS = {"doi", "doi:", "链接", "link", "url"}


def extract_year(s: str) -> str:
    """Extract 4-digit year from string."""
    m = re.search(r"((?:19|20)\d{2})", s)
    return m.group(1) if m else ""


# ---------------------------------------------------------------------------
# 解析条目（唯一入口）
# ---------------------------------------------------------------------------

def parse_entries(text: str) -> list[dict]:
    """解析 raw.md 中的所有入选条目。

    只认 ### 入选N 开头的块 + 6 行 key-value。
    支持字段名中英文、有无 bold **标记**。
    """
    entries = []
    current = None

    for line in text.split("\n"):
        stripped = line.strip()

        # 新条目开始：### 入选N 或 ### paperN 或 ### N 或 ### Author Year
        if re.match(r"^###\s+", stripped):
            if current:
                entries.append(current)
            current = {}
            continue

        # 跳过非条目区域
        if current is None:
            continue

        # 清除 bold 标记
        clean = re.sub(r"\*\*", "", stripped)

        # 解析 key-value: - key: value
        kv = re.match(r"^[-*]?\s*(\S+?)\s*[：:]\s*(.+)$", clean)
        if not kv:
            continue

        raw_key = kv.group(1).strip().lower()
        raw_val = kv.group(2).strip()

        # 跳过无关字段
        if raw_key in SKIP_FIELDS:
            continue

        std_key = FIELD_MAP.get(raw_key)
        if std_key:
            current[std_key] = raw_val

    # 最后一个条目
    if current:
        entries.append(current)

    return entries


# ---------------------------------------------------------------------------
# 分组 + 生成标准输出
# ---------------------------------------------------------------------------

def group_by_tier(entries: list[dict]) -> dict[str, list[dict]]:
    """按级别字段分组。"""
    groups = {"core": [], "important": [], "backup": []}
    for e in entries:
        tier_raw = e.get("tier", "备选").strip().lower()
        tier = TIER_MAP.get(tier_raw, "backup")
        groups[tier].append(e)
    return groups


def generate_standard_batch(meta: dict, groups: dict[str, list[dict]],
                            total_items: int) -> str:
    """生成标准 markdown batch 文件（所有结构由 Python 确定性生成）。"""
    d = meta.get("direction", "0")
    batch_id = meta.get("batch_id", "")
    direction_name = meta.get("direction_name", f"方向{d}")

    total_selected = sum(len(v) for v in groups.values())
    total_rejected = max(0, total_items - total_selected)

    lines = []
    lines.append(f"# 方向{d} Batch{meta.get('batch_num', '1')} 筛选结果\n")
    lines.append(f"> direction: {d}")
    lines.append(f"> direction_name: {direction_name}")
    lines.append(f"> batch_id: {batch_id}")
    lines.append(f"> total_items: {total_items}\n")

    for tier_label, tier_key in [("核心文献（Core）", "core"),
                                   ("重要文献（Important）", "important"),
                                   ("备选文献（Backup）", "backup")]:
        lines.append(f"## {tier_label}\n")
        lines.append("| # | 第一作者 | 标题 | 年份 | 期刊 | 入选理由 |")
        lines.append("|:--|:---------|:-----|:----:|:-----|:---------|")
        for i, p in enumerate(groups[tier_key], 1):
            author = p.get("author", "Unknown").replace("|", "/")
            title = p.get("title", "").replace("|", "/")
            year = extract_year(str(p.get("year", ""))) or "0000"
            journal = p.get("journal", "Unknown").replace("|", "/")
            reason = p.get("reason", "").replace("|", "/").replace("\n", " ")
            lines.append(f"| {i} | {author} | {title} | {year} | {journal} | {reason} |")
        lines.append("")

    lines.append("## 淘汰文献摘要\n")
    lines.append(f"淘汰{total_rejected}篇。")

    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# 从 dispatch plan JSON 读取元数据
# ---------------------------------------------------------------------------

def load_agent_metadata(plan_json_path: str) -> dict[str, dict]:
    """从 _dispatch_plan.json 读取每个 agent 的元数据。

    返回 {batch_id: {direction, batch_num, direction_name, total_items, ...}}
    """
    meta_map = {}
    try:
        with open(plan_json_path, encoding="utf-8") as f:
            plan = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return meta_map

    # 从 items_summary 构建 direction_name 映射（如有）
    dir_names = {}
    for item in plan.get("items_summary", []):
        d = item.get("direction")
        # 尝试从 source_file 提取方向名
        if d and "source_file" in item:
            name = re.sub(r"^\d+[-_]", "", item["source_file"])
            name = re.sub(r"\.(ris|md)$", "", name)
            name = re.sub(r"WOS_\d+_\d+$", "", name).strip("_").strip()
            if name:
                dir_names[d] = name

    for agent in plan.get("agents", []):
        d = agent.get("direction", 0)
        split = agent.get("split_info", "1/1")
        batch_num = split.split("/")[0] if "/" in split else "1"
        batch_id = f"d{d}_batch{batch_num}"

        meta_map[batch_id] = {
            "direction": str(d),
            "batch_num": batch_num,
            "batch_id": batch_id,
            "direction_name": dir_names.get(d, f"方向{d}"),
            "total_items": agent.get("item_count", 30),
        }

    return meta_map


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Normalize batch files to standard format")
    parser.add_argument("--batch-dir", required=True, help="Directory containing batch files")
    parser.add_argument("--plan-json", default=None,
                        help="Path to _dispatch_plan.json (for metadata)")
    args = parser.parse_args()

    batch_dir = Path(args.batch_dir)

    # 加载元数据
    plan_json = args.plan_json
    if not plan_json:
        # 自动查找
        candidate = batch_dir.parent / "_dispatch_plan.json"
        if candidate.exists():
            plan_json = str(candidate)
    meta_map = load_agent_metadata(plan_json) if plan_json else {}

    # 查找 raw 文件
    raw_files = sorted(batch_dir.glob("d*_batch*_raw.md"))
    if not raw_files:
        print("ERROR: No batch files found", file=sys.stderr)
        sys.exit(1)

    total_ok = 0
    total_warn = 0
    total_papers = 0
    errors = []

    for fp in raw_files:
        try:
            text = fp.read_text(encoding="utf-8")
            stem = fp.stem.replace("_raw", "")

            # 获取元数据（优先从 JSON，回退从文件名推断）
            meta = meta_map.get(stem, {})
            if not meta:
                fname_m = re.match(r"d(\d+)_batch(\d+)", stem)
                if fname_m:
                    meta = {
                        "direction": fname_m.group(1),
                        "batch_num": fname_m.group(2),
                        "batch_id": stem,
                        "direction_name": f"方向{fname_m.group(1)}",
                        "total_items": 30,
                    }

            # 检查是否是"无入选"
            if text.strip() in ("无", "无入选文献", ""):
                entries = []
            else:
                entries = parse_entries(text)

            # 分组
            groups = group_by_tier(entries)
            paper_count = sum(len(v) for v in groups.values())
            total_papers += paper_count

            # 校验
            file_errors = []
            for tier, tier_entries in groups.items():
                for i, p in enumerate(tier_entries):
                    if not p.get("title"):
                        file_errors.append(f"{tier}[{i}]: missing title")
                    if not extract_year(str(p.get("year", ""))):
                        file_errors.append(f"{tier}[{i}]: missing/invalid year")
                    if not p.get("tier"):
                        file_errors.append(f"{tier}[{i}]: missing 级别 field")

            # 生成标准输出
            total_items = meta.get("total_items", 30)
            output = generate_standard_batch(meta, groups, total_items)
            out_path = batch_dir / f"{stem}.md"
            out_path.write_text(output, encoding="utf-8")

            if file_errors:
                total_warn += 1
                errors.append(f"{stem}: {paper_count} papers, {len(file_errors)} errors: {file_errors[:3]}")
                print(f"  ⚠ {stem}: {paper_count} papers ({', '.join(file_errors[:2])})")
            else:
                total_ok += 1
                print(f"  ✓ {stem}: {paper_count} papers")

        except Exception as e:
            total_warn += 1
            errors.append(f"{fp.name}: {e}")
            print(f"  ✗ {fp.name}: {e}", file=sys.stderr)

    print(f"\nTotal: {len(raw_files)} files, {total_papers} papers")
    print(f"OK: {total_ok}, Warnings: {total_warn}")

    if errors:
        print("\n=== VERIFY: FAIL ===")
        for e in errors:
            print(f"  ❌ {e}")
        if total_ok == 0:
            sys.exit(1)
    else:
        print("\n=== VERIFY: PASS ===")


if __name__ == "__main__":
    main()
