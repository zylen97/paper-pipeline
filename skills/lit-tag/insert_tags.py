#!/usr/bin/env python3
"""
insert_tags.py — 将 Agent 输出的标签列表插入 direction reports（lit-tag §2.1）

读取 _tags/d*_tags.md（编号→标签 列表），
读取对应的 direction report（6列表格），
在"入选理由"列前插入"功能标签"列，生成7列表格，覆写回 report。

设计原理：表格插列是纯机械操作，不应由 LLM 执行。
Agent 只负责判断标签，本脚本负责格式操作。

用法:
    python3 insert_tags.py \
        --tags-dir structure/2_literature/_tags/ \
        --report-dir structure/2_literature/
"""

import argparse
import re
import sys
from pathlib import Path


VALID_TAGS = {
    "BG", "LR", "COMP",
    "METHOD-基础", "METHOD-先例",
    "GAP-RQ1", "GAP-RQ2", "GAP-RQ3", "GAP-RQ4", "GAP-RQ5",
    "DISC-RQ1", "DISC-RQ2", "DISC-RQ3", "DISC-RQ4", "DISC-RQ5",
}


# ---------------------------------------------------------------------------
# parse tag files
# ---------------------------------------------------------------------------

def parse_tag_file(filepath: Path) -> dict:
    """Parse a tag file into {tier: {row_num: tags_string}}."""
    text = filepath.read_text(encoding="utf-8")

    # Extract direction number
    d_match = re.search(r"direction:\s*(\d+)", text)
    direction = int(d_match.group(1)) if d_match else 0

    if direction == 0:
        fname_m = re.match(r"d(\d+)_tags", filepath.stem)
        if fname_m:
            direction = int(fname_m.group(1))

    result = {"direction": direction, "tiers": {}}
    current_tier = None

    for line in text.split("\n"):
        stripped = line.strip()

        # Detect tier (match section headers starting with ##)
        if re.match(r"^##\s.*(核心文献|Core)", stripped, re.IGNORECASE):
            current_tier = "core"
            result["tiers"][current_tier] = {}
            continue
        elif re.match(r"^##\s.*(重要文献|Important)", stripped, re.IGNORECASE):
            current_tier = "important"
            result["tiers"][current_tier] = {}
            continue
        elif re.match(r"^##\s.*(备选文献|Backup)", stripped, re.IGNORECASE):
            current_tier = "backup"
            result["tiers"][current_tier] = {}
            continue

        if current_tier is None:
            continue

        # Parse tag lines — support both formats:
        #   New: "N → TAG1+TAG2+..."  (template fill-in mode)
        #   Old: "N: TAG1+TAG2+..."   (backward compat)
        m = re.match(r"(\d+)\s*(?:→|[:：])\s*(.+)$", stripped)
        if m:
            row_num = int(m.group(1))
            raw_tags = m.group(2).strip()

            # Clean: strip annotation text after — or --(em dash or double hyphen)
            raw_tags = re.split(r"\s*[—–]\s", raw_tags)[0].strip()

            # Normalize separators: accept +, comma, 、 as tag delimiters
            tag_parts = re.split(r"[+,、]\s*", raw_tags)

            # Only keep valid tag names, discard annotation fragments
            valid_tags = []
            for t in tag_parts:
                t = t.strip()
                # Normalize BG variants: BG(2024-2026), BG(2025-2027) etc. → BG
                if re.match(r"^BG\s*\(", t):
                    t = "BG"
                if t in VALID_TAGS:
                    valid_tags.append(t)

            tags = "+".join(valid_tags) if valid_tags else "LR"
            result["tiers"][current_tier][row_num] = tags

    return result


# ---------------------------------------------------------------------------
# modify direction report
# ---------------------------------------------------------------------------


def validate_tags(tags_str: str) -> list[str]:
    """Validate and clean a tag string."""
    tags = [t.strip() for t in re.split(r"[+,、/]", tags_str) if t.strip()]
    warnings = []
    for t in tags:
        if t not in VALID_TAGS:
            warnings.append(f"unknown tag '{t}'")
    return warnings


def insert_tags_into_report(report_path: Path, tag_data: dict) -> tuple[str, list[str]]:
    """Insert tag column into a direction report. Returns (new_content, errors)."""
    text = report_path.read_text(encoding="utf-8")
    lines = text.split("\n")
    new_lines = []
    errors = []

    current_tier = None
    row_counter = 0
    tiers = tag_data.get("tiers", {})

    for line in lines:
        # Detect tier (only match section headers starting with ##, not paper titles)
        tier_detected = None
        if re.match(r"^##\s.*(核心文献|Core)", line, re.IGNORECASE):
            tier_detected = "core"
        elif re.match(r"^##\s.*(重要文献|Important)", line, re.IGNORECASE):
            tier_detected = "important"
        elif re.match(r"^##\s.*(备选文献|Backup)", line, re.IGNORECASE):
            tier_detected = "backup"
        elif re.match(r"^##\s.*(淘汰文献|淘汰摘要)", line, re.IGNORECASE):
            current_tier = None
            row_counter = 0

        if tier_detected:
            current_tier = tier_detected
            row_counter = 0
            new_lines.append(line)
            continue

        # Check if this is a table header row (contains 作者, but first cell is NOT a number)
        # Must exclude data rows like "| 1 | Huisman | ... | Snijders共同作者... |"
        if current_tier and not re.match(r"\|\s*\d+\s*\|", line) and re.search(r"(?:第一作者|作者)", line):
            # Check if tag column already exists
            if "功能标签" in line:
                new_lines.append(line)
                continue
            # Insert "功能标签" column before last column (入选理由)
            cells = line.split("|")
            # cells: ['', ' # ', ' 作者 ', ' 标题 ', ' 年份 ', ' 期刊 ', ' 入选理由 ', '']
            if len(cells) >= 8:  # 6 data columns + 2 empty
                cells.insert(-2, " 功能标签 ")
                new_lines.append("|".join(cells))
            else:
                new_lines.append(line)
            continue

        # Check if this is a separator row (|:--|...)
        if current_tier and re.match(r"\|[\s:|-]+\|$", line.strip()):
            # Check column count
            sep_cells = line.split("|")
            # If 7 columns already (has tag column), skip
            if len(sep_cells) >= 9:
                new_lines.append(line)
                continue
            if len(sep_cells) >= 8:
                sep_cells.insert(-2, ":------")
                new_lines.append("|".join(sep_cells))
            else:
                new_lines.append(line)
            continue

        # Check if this is a data row
        if current_tier and line.strip().startswith("|"):
            # Match data row: | N | ... |
            m = re.match(r"\|\s*(\d+)\s*\|", line)
            if m:
                row_counter += 1
                row_num = int(m.group(1))

                # Get tags for this row
                tier_tags = tiers.get(current_tier, {})
                # Try matching by row_num first, then by counter
                tags = tier_tags.get(row_num, tier_tags.get(row_counter, ""))

                if not tags:
                    errors.append(f"D{tag_data['direction']} {current_tier}[{row_num}]: no tag found")
                    tags = "LR"  # default fallback

                # Validate tags
                tag_warnings = validate_tags(tags)
                for w in tag_warnings:
                    errors.append(f"D{tag_data['direction']} {current_tier}[{row_num}]: {w}")

                # Handle escaped pipes (\|) in existing tag column
                safe_line = line.replace("\\|", "\x00")
                cells = safe_line.split("|")

                if len(cells) >= 9:  # already has tag column — overwrite it
                    cells[-3] = f" {tags} "
                    new_lines.append("|".join(cells).replace("\x00", "\\|"))
                    continue

                # Insert tag before last data column (入选理由)
                if len(cells) >= 8:
                    cells.insert(-2, f" {tags} ")
                    new_lines.append("|".join(cells).replace("\x00", "\\|"))
                else:
                    new_lines.append(line)
                continue

        new_lines.append(line)

    return "\n".join(new_lines), errors


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Insert tags into direction reports")
    parser.add_argument("--tags-dir", required=True, help="Directory containing d*_tags.md files")
    parser.add_argument("--report-dir", required=True, help="Directory containing direction reports")
    args = parser.parse_args()

    tags_dir = Path(args.tags_dir)
    report_dir = Path(args.report_dir)

    tag_files = sorted(tags_dir.glob("d*_tags.md"))
    if not tag_files:
        print("ERROR: No tag files found", file=sys.stderr)
        sys.exit(1)

    all_errors = []
    processed = 0

    for tag_file in tag_files:
        tag_data = parse_tag_file(tag_file)
        d = tag_data["direction"]

        # Find corresponding report
        report_files = list(report_dir.glob(f"direction{d}_*_report.md"))
        if not report_files:
            print(f"  ✗ D{d}: no direction report found", file=sys.stderr)
            all_errors.append(f"D{d}: no direction report found")
            continue

        report_path = report_files[0]

        # Count tags
        total_tags = sum(len(v) for v in tag_data["tiers"].values())

        # Insert tags
        new_content, errors = insert_tags_into_report(report_path, tag_data)
        all_errors.extend(errors)

        # Write back
        report_path.write_text(new_content, encoding="utf-8")
        processed += 1

        status = "⚠" if errors else "✓"
        print(f"  {status} D{d}: {total_tags} tags inserted into {report_path.name}")
        for e in errors[:3]:
            print(f"    → {e}")

    print(f"\nProcessed: {processed}/{len(tag_files)} directions")

    if all_errors:
        # Only FAIL for critical errors (no tags at all)
        critical = [e for e in all_errors if "no tag found" in e or "no direction report" in e]
        if critical:
            print(f"\n=== VERIFY: FAIL ===")
            print(f"Critical errors: {len(critical)}")
            sys.exit(1)
        else:
            print(f"\n=== VERIFY: PASS (with {len(all_errors)} warnings) ===")
    else:
        print(f"\n=== VERIFY: PASS ===")


if __name__ == "__main__":
    main()
