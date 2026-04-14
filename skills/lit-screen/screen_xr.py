"""
RIS 解析 + XR2026 新锐分区过滤

用法:
  python3 screen_xr.py <ris_path> [--zone 2] [--output filtered.ris]

输出到 stdout:
  - 原始文献数量
  - 各分区分布
  - 筛选后数量

同时生成:
  - <ris_path>_zone12.ris  (筛选后的 RIS)
"""

import argparse
import csv
import json
import os
import re
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).parent
XR_CSV = SKILL_DIR / "data" / "XR2026-UTF8.csv"


def parse_ris(ris_path: str) -> list[dict]:
    """解析 RIS 文件，返回文献列表。每篇文献是一个 dict，key 为 RIS tag。"""
    records = []
    current = {}
    with open(ris_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            # RIS tag: 两个大写字母/数字 + 两个空格 + dash + 可选空格 + 可选值
            # 兼容 "ER  -" (无尾部空格) 和 "ER  - " (有尾部空格) 两种写法
            match = re.match(r"^([A-Z][A-Z0-9])  -\s?(.*)$", line)
            if match:
                tag, value = match.group(1), match.group(2).strip()
                if tag == "ER":
                    if current:
                        records.append(current)
                    current = {}
                elif tag == "TY":
                    current["TY"] = value
                else:
                    # 同一 tag 可能出现多次 (如 AU, SN, KW)
                    if tag in current:
                        if isinstance(current[tag], list):
                            current[tag].append(value)
                        else:
                            current[tag] = [current[tag], value]
                    else:
                        current[tag] = value
    # 处理末尾没有 ER 的情况
    if current:
        records.append(current)
    return records


def write_ris(records: list[dict], output_path: str):
    """将文献列表写回 RIS 格式。"""
    with open(output_path, "w", encoding="utf-8") as f:
        for rec in records:
            # TY 必须在最前面
            ty = rec.get("TY", "JOUR")
            f.write(f"TY  - {ty}\n")
            for tag, value in rec.items():
                if tag in ("TY",):
                    continue
                if isinstance(value, list):
                    for v in value:
                        f.write(f"{tag}  - {v}\n")
                else:
                    f.write(f"{tag}  - {value}\n")
            f.write("ER  - \n\n")


def load_xr2026() -> tuple[dict, dict]:
    """
    加载 XR2026 新锐分区表。
    返回:
      issn_lookup: {issn: info}  — ISSN/EISSN 双入口
      name_lookup: {journal_name_upper: info}  — 期刊名回退匹配
    """
    issn_lookup = {}
    name_lookup = {}
    with open(XR_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            issn = row.get("ISSN", "").strip()
            eissn = row.get("EISSN", "").strip()
            journal_name = row.get("Journal", "").strip()
            zone_str = row.get("大类新锐分区", "").strip()
            # 提取分区数字: "1 区" → 1
            zone_match = re.match(r"(\d)", zone_str)
            zone_num = int(zone_match.group(1)) if zone_match else 9
            info = {
                "journal": journal_name,
                "zone_num": zone_num,
                "zone_str": zone_str,
                "top": row.get("Top", "").strip(),
                "category": row.get("大类中文名", "").strip(),
                "warning": row.get("预警标记", "").strip(),
            }
            if issn and issn != "-":
                issn_lookup[issn.upper()] = info
            if eissn and eissn != "-":
                issn_lookup[eissn.upper()] = info
            if journal_name:
                name_lookup[journal_name.upper()] = info
    return issn_lookup, name_lookup


def get_issns(record: dict) -> list[str]:
    """从一条 RIS 记录中提取所有 ISSN (SN tag)。"""
    sn = record.get("SN", [])
    if isinstance(sn, str):
        sn = [sn]
    # 清理: 去掉空格，统一大写
    return [s.strip().upper() for s in sn if s.strip()]


def get_journal_name(record: dict) -> str:
    """从 RIS 记录中提取期刊名。优先 T2 (Secondary Title)，其次 J2, JO, JF。"""
    for tag in ("T2", "J2", "JO", "JF"):
        val = record.get(tag, "")
        if isinstance(val, list):
            val = val[0]
        if val.strip():
            return val.strip().upper()
    return ""


def screen(ris_path: str, max_zone: int = 2, output_path: str | None = None):
    """
    主筛选逻辑。

    Args:
        ris_path: RIS 文件路径
        max_zone: 保留的最大分区号 (2 = 保留1区+2区)
        output_path: 输出 RIS 路径，默认自动生成
    """
    # 1. 解析 RIS
    records = parse_ris(ris_path)
    total = len(records)

    # 2. 加载 XR2026（ISSN 索引 + 期刊名索引）
    xr_issn, xr_name = load_xr2026()

    # 3. 匹配 + 分类
    zone_dist = {1: 0, 2: 0, 3: 0, 4: 0}
    unmatched = 0
    kept = []
    removed = []
    unmatched_records = []
    detail_rows = []  # CSV 明细

    for rec in records:
        title = rec.get("TI", rec.get("T1", ""))
        if isinstance(title, list):
            title = " ".join(title)
        journal_in_ris = get_journal_name(rec)

        # 匹配策略：ISSN 优先 → 期刊名回退
        matched_info = None
        match_method = ""

        issns = get_issns(rec)
        for issn in issns:
            if issn in xr_issn:
                matched_info = xr_issn[issn]
                match_method = "ISSN"
                break

        if matched_info is None and journal_in_ris:
            if journal_in_ris in xr_name:
                matched_info = xr_name[journal_in_ris]
                match_method = "期刊名"

        if matched_info is None:
            unmatched += 1
            unmatched_records.append(rec)
            detail_rows.append({
                "标题": title,
                "期刊": journal_in_ris,
                "ISSN": ", ".join(issns) if issns else "",
                "匹配方式": "未匹配",
                "XR2026期刊名": "",
                "大类": "",
                "分区": "",
                "Top": "",
                "结果": "保留（未匹配）",
            })
            continue

        zone = matched_info["zone_num"]
        if zone in zone_dist:
            zone_dist[zone] += 1

        action = "保留" if zone <= max_zone else "过滤"
        if zone <= max_zone:
            kept.append(rec)
        else:
            removed.append(rec)

        detail_rows.append({
            "标题": title,
            "期刊": journal_in_ris,
            "ISSN": ", ".join(issns) if issns else "",
            "匹配方式": match_method,
            "XR2026期刊名": matched_info["journal"],
            "大类": matched_info["category"],
            "分区": matched_info["zone_str"],
            "Top": matched_info["top"],
            "结果": action,
        })

    # 未匹配的也加入保留列表
    kept_with_unmatched = kept + unmatched_records

    # 4. 输出 RIS
    if not output_path:
        base = Path(ris_path)
        output_path = str(base.parent / f"{base.stem}_zone{max_zone}{base.suffix}")

    write_ris(kept_with_unmatched, output_path)

    # 5. 输出 CSV 明细
    base = Path(ris_path)
    csv_path = str(base.parent / f"{base.stem}_screening.csv")
    import pandas as pd
    df = pd.DataFrame(detail_rows)
    df.index = range(1, len(df) + 1)
    df.index.name = "序号"
    df.to_csv(csv_path, encoding="utf-8-sig")

    # 6. 输出统计 JSON 到 stdout
    stats = {
        "original": total,
        "zone_distribution": {
            "1区": zone_dist[1],
            "2区": zone_dist[2],
            "3区": zone_dist[3],
            "4区": zone_dist[4],
            "未匹配": unmatched,
        },
        "max_zone": max_zone,
        "kept": len(kept),
        "kept_with_unmatched": len(kept_with_unmatched),
        "removed": len(removed),
        "unmatched": unmatched,
        "output_path": output_path,
        "csv_path": csv_path,
    }
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    return stats


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RIS + XR2026 新锐分区筛选")
    parser.add_argument("ris_path", help="输入 RIS 文件路径")
    parser.add_argument("--zone", type=int, default=2, help="保留的最大分区 (默认 2 = 保留1区+2区)")
    parser.add_argument("--output", help="输出 RIS 文件路径 (默认自动生成)")
    args = parser.parse_args()
    screen(args.ris_path, args.zone, args.output)
