#!/usr/bin/env python3
"""
tag_aggregate.py — 标签聚合统计（lit-tag §2）

从打完标签的 direction reports 中解析标签数据，计算全局标签统计、
达标率、均衡性预警，生成 tag_report.md。

替代主 Agent 的手动计数和百分比计算。

用法:
    python3 tag_aggregate.py \
        --report-dir structure/2_literature/ \
        --output structure/2_literature/tag_report.md

输出:
    1. stdout 结构化摘要 + 校验结果
    2. tag_report.md 文件
    3. _tag_aggregate.json（结构化数据供后续使用）
"""

import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path


# ---------------------------------------------------------------------------
# 标签 Pool 目标（常量，与 lit-plan 一致）
# ---------------------------------------------------------------------------

TAG_POOL_TARGETS = {
    "BG": 50,
    "LR": 150,
    "GAP": 75,    # GAP-RQx 总和
    "METHOD": 60,  # METHOD-基础 + METHOD-先例
    "DISC": 65,    # DISC-RQx 总和
}


def normalize_tag_group(tag: str) -> str:
    """归一化标签到大组用于达标率计算。"""
    tag = tag.strip()
    if tag.startswith("BG"):
        return "BG"
    if tag.startswith("GAP"):
        return "GAP"
    if tag.startswith("DISC"):
        return "DISC"
    if tag.startswith("METHOD"):
        return "METHOD"
    return tag


# ---------------------------------------------------------------------------
# 解析 direction report
# ---------------------------------------------------------------------------

def parse_report(filepath: Path) -> list[dict]:
    """从一个 direction report 中提取所有入选文献及其标签。"""
    try:
        with open(filepath, encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        print(f"WARNING: Cannot read {filepath}: {e}", file=sys.stderr)
        return []

    # 提取方向编号
    d_match = re.match(r"direction(\d+)", filepath.name)
    direction = int(d_match.group(1)) if d_match else 0

    papers = []
    current_tier = None

    for line in content.split("\n"):
        # 检测分级区块（只匹配 ## 开头的 section header，避免匹配论文标题中的 Core/Important 等词）
        if re.match(r"^##\s.*(核心文献|Core)", line, re.IGNORECASE):
            current_tier = "core"
        elif re.match(r"^##\s.*(重要文献|Important)", line, re.IGNORECASE):
            current_tier = "important"
        elif re.match(r"^##\s.*(备选文献|Backup)", line, re.IGNORECASE):
            current_tier = "backup"

        # 解析表格行（| 序号 | 作者 | 标题 | 年份 | 期刊 | 功能标签 | 入选理由 |）
        # 带标签版本：7列
        m7 = re.match(
            r"\|\s*(\d+)\s*\|"    # #
            r"\s*([^|]+)\|"        # 作者
            r"\s*([^|]+)\|"        # 标题
            r"\s*(\d{4})\s*\|"     # 年份
            r"\s*([^|]+)\|"        # 期刊
            r"\s*([^|]+)\|"        # 功能标签
            r"\s*([^|]+)\|",       # 入选理由
            line
        )
        # 无标签版本：6列（兼容未打标签的report）
        m6 = re.match(
            r"\|\s*(\d+)\s*\|"
            r"\s*([^|]+)\|"
            r"\s*([^|]+)\|"
            r"\s*(\d{4})\s*\|"
            r"\s*([^|]+)\|"
            r"\s*([^|]+)\|",
            line
        ) if not m7 else None

        if m7:
            tags_raw = m7.group(6).strip()
            # 解析标签（支持多种分隔符：+, ,, 、, /, ;, \|, |）
            # 先去掉反引号包裹
            tags_raw = tags_raw.replace("`", "")
            # 统一分隔符：\| → ;
            tags_raw = tags_raw.replace("\\|", ";")
            tags_raw = tags_raw.replace("\\", "")  # 去掉残留反斜杠
            # 过滤占位符
            if tags_raw.strip() in ("—", "-", "N/A", ""):
                tags = []
            else:
                # Valid tag prefixes
                VALID_PREFIXES = ("BG", "LR", "GAP", "METHOD", "DISC", "COMP")
                raw_tags = [t.strip().rstrip("\\").strip() for t in re.split(r"[+,、/;|]", tags_raw) if t.strip().rstrip("\\").strip()]
                tags = [t for t in raw_tags if any(t.startswith(p) for p in VALID_PREFIXES)]
            papers.append({
                "direction": direction,
                "author": m7.group(2).strip(),
                "title": m7.group(3).strip(),
                "year": int(m7.group(4)),
                "journal": m7.group(5).strip(),
                "tags": tags,
                "tier": current_tier or "backup",
                "reason": m7.group(7).strip(),
            })
        elif m6:
            # 无标签列的 report
            papers.append({
                "direction": direction,
                "author": m6.group(2).strip(),
                "title": m6.group(3).strip(),
                "year": int(m6.group(4)),
                "journal": m6.group(5).strip(),
                "tags": [],
                "tier": current_tier or "backup",
                "reason": m6.group(6).strip(),
            })

    return papers


# ---------------------------------------------------------------------------
# 统计
# ---------------------------------------------------------------------------

def compute_stats(all_papers: list[dict]) -> dict:
    """计算全局标签统计。"""
    # 按精确标签统计
    tag_tier_count: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    # 按方向×标签统计
    dir_tag_count: dict[int, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    no_tag_count = 0

    for p in all_papers:
        if not p["tags"]:
            no_tag_count += 1
            continue
        for tag in p["tags"]:
            tag_tier_count[tag][p["tier"]] += 1
            dir_tag_count[p["direction"]][tag] += 1

    # 按归一化大组汇总（用于达标率）
    group_count: dict[str, int] = defaultdict(int)
    for tag, tiers in tag_tier_count.items():
        group = normalize_tag_group(tag)
        group_count[group] += sum(tiers.values())

    # 达标率
    adequacy = {}
    for group, target in TAG_POOL_TARGETS.items():
        actual = group_count.get(group, 0)
        rate = round(actual / target * 100, 1) if target > 0 else 0
        if rate >= 80:
            status = "✅"
        elif rate >= 50:
            status = "⚠️"
        else:
            status = "❌"
        adequacy[group] = {
            "target": target,
            "actual": actual,
            "rate": rate,
            "status": status,
        }

    return {
        "tag_tier_count": {k: dict(v) for k, v in tag_tier_count.items()},
        "dir_tag_count": {k: dict(v) for k, v in dir_tag_count.items()},
        "group_count": dict(group_count),
        "adequacy": adequacy,
        "no_tag_count": no_tag_count,
        "total_papers": len(all_papers),
    }


# ---------------------------------------------------------------------------
# 生成 tag_report.md
# ---------------------------------------------------------------------------

def generate_report(stats: dict, all_papers: list[dict]) -> str:
    """生成 tag_report.md 内容。"""
    lines = []
    lines.append("# 标签统计报告\n")
    lines.append(f"> **日期**: {date.today().isoformat()}")
    lines.append(f"> **入选文献总量**: {stats['total_papers']}篇")
    if stats["no_tag_count"] > 0:
        lines.append(f"> **⚠️ 无标签文献**: {stats['no_tag_count']}篇")
    lines.append("")

    # 标签分布表
    lines.append("## 标签分布\n")
    lines.append("| 标签 | 核心 | 重要 | 备选 | 合计 |")
    lines.append("|:-----|:----:|:----:|:----:|:----:|")
    for tag in sorted(stats["tag_tier_count"].keys()):
        tiers = stats["tag_tier_count"][tag]
        c = tiers.get("core", 0)
        i = tiers.get("important", 0)
        b = tiers.get("backup", 0)
        total = c + i + b
        lines.append(f"| {tag} | {c} | {i} | {b} | {total} |")
    lines.append("")

    # 均衡性预警表
    lines.append("## 均衡性预警\n")
    lines.append("| 标签 | Pool目标 | 实际入选 | 达标率 | 状态 |")
    lines.append("|:-----|:-------:|:-------:|:-----:|:----:|")
    for group in ["BG", "LR", "GAP", "METHOD", "DISC"]:
        a = stats["adequacy"].get(group, {})
        lines.append(f"| {group} | {a.get('target', 0)} | {a.get('actual', 0)} | {a.get('rate', 0)}% | {a.get('status', '?')} |")
    lines.append("")

    # 各方向标签贡献表
    directions = sorted(stats["dir_tag_count"].keys())
    if directions:
        # 收集所有出现过的标签大组
        all_groups = sorted(set(normalize_tag_group(t) for t in stats["tag_tier_count"]))

        lines.append("## 各方向标签贡献\n")
        header = "| 方向 | " + " | ".join(all_groups) + " |"
        sep = "|:-----|" + "|".join(":--:" for _ in all_groups) + "|"
        lines.append(header)
        lines.append(sep)
        for d in directions:
            dtags = stats["dir_tag_count"][d]
            # 归一化后汇总
            group_sums: dict[str, int] = defaultdict(int)
            for tag, cnt in dtags.items():
                group_sums[normalize_tag_group(tag)] += cnt
            cols = [str(group_sums.get(g, 0)) for g in all_groups]
            lines.append(f"| D{d} | " + " | ".join(cols) + " |")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 校验
# ---------------------------------------------------------------------------

def verify(stats: dict, report_content: str) -> list[str]:
    """内建校验。"""
    errors = []

    # 1. 无标签文献检查
    if stats["no_tag_count"] > 0:
        errors.append(f"NO_TAGS: {stats['no_tag_count']}篇文献没有功能标签")

    # 2. 回读报告验证表格行数
    table_rows = len(re.findall(r"^\|\s*[A-Z]", report_content, re.MULTILINE))
    expected_rows = len(stats["tag_tier_count"])
    if table_rows < expected_rows:
        errors.append(f"ROW_MISMATCH: 标签分布表应有{expected_rows}行, 实际{table_rows}行")

    # 3. 达标率数学验证
    for group, a in stats["adequacy"].items():
        expected_rate = round(a["actual"] / a["target"] * 100, 1) if a["target"] > 0 else 0
        if abs(expected_rate - a["rate"]) > 0.1:
            errors.append(f"RATE_ERROR: {group} 达标率计算错误 expected={expected_rate}%, got={a['rate']}%")

    # 4. 各标签计数一致性（精确标签之和 ≥ 归一化大组之和，因为一篇多标签）
    for group, actual in stats["group_count"].items():
        tag_sum = 0
        for tag, tiers in stats["tag_tier_count"].items():
            if normalize_tag_group(tag) == group:
                tag_sum += sum(tiers.values())
        if tag_sum != actual:
            errors.append(f"COUNT_INCONSISTENCY: {group} group_count={actual}, tag_sum={tag_sum}")

    return errors


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Aggregate tags from direction reports")
    parser.add_argument("--report-dir", required=True,
                        help="Directory containing direction*_report.md files")
    parser.add_argument("--output", default=None,
                        help="Output tag_report.md path")
    args = parser.parse_args()

    report_dir = Path(args.report_dir)
    output_path = args.output or str(report_dir / "tag_report.md")
    json_path = str(report_dir / "_tag_aggregate.json")

    # 1. 扫描所有 direction reports
    report_files = sorted(report_dir.glob("direction*_report.md"))
    if not report_files:
        print("ERROR: No direction reports found", file=sys.stderr)
        sys.exit(1)

    # 2. 解析
    all_papers = []
    for fp in report_files:
        papers = parse_report(fp)
        all_papers.extend(papers)
        print(f"  Parsed {fp.name}: {len(papers)} papers", file=sys.stderr)

    if not all_papers:
        print("ERROR: No papers found in reports", file=sys.stderr)
        sys.exit(1)

    # 3. 统计
    stats = compute_stats(all_papers)

    # 4. 生成报告
    report_content = generate_report(stats, all_papers)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report_content)

    # 5. 写 JSON
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

    # 6. 校验
    errors = verify(stats, report_content)

    # ===== stdout 结构化摘要 =====
    print(f"=== TAG AGGREGATE ===")
    print(f"Reports parsed: {len(report_files)}")
    print(f"Total papers: {stats['total_papers']}")
    if stats["no_tag_count"] > 0:
        print(f"⚠️ Papers without tags: {stats['no_tag_count']}")
    print()

    # 标签分布
    print("Tag distribution:")
    for tag in sorted(stats["tag_tier_count"]):
        tiers = stats["tag_tier_count"][tag]
        total = sum(tiers.values())
        print(f"  {tag}: {total} (core={tiers.get('core', 0)}, important={tiers.get('important', 0)}, backup={tiers.get('backup', 0)})")
    print()

    # 达标率
    print("Adequacy check:")
    for group in ["BG", "LR", "GAP", "METHOD", "DISC"]:
        a = stats["adequacy"].get(group, {})
        print(f"  {group}: {a.get('actual', 0)}/{a.get('target', 0)} = {a.get('rate', 0)}% {a.get('status', '?')}")
    print()

    # 校验结果
    if errors:
        print("=== VERIFY: FAIL ===")
        for e in errors:
            print(f"  ❌ {e}")
        sys.exit(1)
    else:
        print("=== VERIFY: PASS ===")
        print(f"Report: {output_path}")
        print(f"JSON: {json_path}")


if __name__ == "__main__":
    main()
