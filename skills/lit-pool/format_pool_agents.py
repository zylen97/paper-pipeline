#!/usr/bin/env python3
"""
format_pool_agents.py — 将 Agent 输出的 key-value 块格式转换为 pool_merge.py 所需的标准表格格式

设计原理（模板填空 + 结构分离）：
- Agent 只输出条目级 key-value 块（照模板格式填空），每条自带「标签」字段
- 本脚本按「标签」字段分组，确定性生成 `# TAG` section headers + 标准表格
- Agent 不写任何 `#` headers — section 结构完全由本脚本控制

用法:
    python3 format_pool_agents.py \\
        --input-dir structure/2_literature/ \\
        [--prepare-json _pool_prepare.json]
"""

import argparse
import re
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# 分级映射（中英文 → 标准中文）
# ---------------------------------------------------------------------------

GRADE_MAP = {
    "核心": "核心",
    "core": "核心",
    "重要": "重要",
    "important": "重要",
    "备选": "备选",
    "backup": "备选",
}


def normalize_grade(raw: str) -> str:
    """归一化分级值。"""
    key = raw.strip().lower()
    return GRADE_MAP.get(key, raw.strip())


# ---------------------------------------------------------------------------
# key-value 块解析
# ---------------------------------------------------------------------------

KV_RE = re.compile(r"^[-*]?\s*(\S+?)\s*[：:]\s*(.+)$")

FIELD_ALIASES = {
    "citation_key": "citation_key",
    "citationkey": "citation_key",
    "citation key": "citation_key",
    "key": "citation_key",
    "分级": "分级",
    "grade": "分级",
    "级别": "分级",
    "作者": "作者",
    "author": "作者",
    "authors": "作者",
    "年份": "年份",
    "year": "年份",
    "引用场景": "引用场景",
    "场景": "引用场景",
    "scenario": "引用场景",
    "期刊": "期刊",
    "journal": "期刊",
    "标签": "标签",
    "tag": "标签",
    "tags": "标签",
}

# 允许但忽略的字段
SKIP_FIELDS = {"doi", "link", "url", "链接"}


def normalize_field(raw: str) -> str | None:
    """归一化字段名，返回标准字段名或 None。"""
    key = raw.strip().lower().replace(" ", "").replace("_", "_")
    if key in FIELD_ALIASES:
        return FIELD_ALIASES[key]
    key_with_space = raw.strip().lower()
    if key_with_space in FIELD_ALIASES:
        return FIELD_ALIASES[key_with_space]
    if key in SKIP_FIELDS:
        return None
    return None


def parse_kv_block(lines: list[str]) -> dict[str, str] | None:
    """从一组行中解析 key-value 对，返回标准字段字典。"""
    fields: dict[str, str] = {}
    for line in lines:
        clean = re.sub(r"\*\*", "", line.strip())
        m = KV_RE.match(clean)
        if not m:
            continue
        raw_key, raw_val = m.group(1), m.group(2).strip()
        if "{{" in raw_val:
            continue
        std_key = normalize_field(raw_key)
        if std_key:
            fields[std_key] = raw_val

    if "citation_key" not in fields:
        return None
    return fields


def fields_to_row(fields: dict[str, str]) -> str:
    """将字段字典转为标准表格行。"""
    grade = normalize_grade(fields.get("分级", "备选"))
    author = fields.get("作者", "—").replace("|", "/")
    year = fields.get("年份", "—")
    ckey = fields.get("citation_key", "—")
    scenario = fields.get("引用场景", "—").replace("|", "/")
    journal = fields.get("期刊", "—").replace("|", "/")
    return f"| {grade} | {author} | {year} | {ckey} | {scenario} | {journal} |"


# ---------------------------------------------------------------------------
# 解析所有条目 → 按标签分组 → 生成标准表格
# ---------------------------------------------------------------------------

TABLE_HEADER = (
    "| 分级 | 作者 | 年份 | citation key | 引用场景 | 期刊 |\n"
    "|:----:|:-----|:----:|:------------|:---------|:-----:|"
)


def parse_entries(content: str) -> list[dict]:
    """解析文件中所有 ### paperN 条目块。"""
    entries = []
    current_lines: list[str] | None = None

    for line in content.split("\n"):
        stripped = line.strip()

        if re.match(r"^#{2,3}\s+", stripped):
            if current_lines is not None:
                fields = parse_kv_block(current_lines)
                if fields:
                    entries.append(fields)
            current_lines = []
            continue

        if current_lines is not None and stripped:
            current_lines.append(stripped)

    # 最后一个块
    if current_lines is not None:
        fields = parse_kv_block(current_lines)
        if fields:
            entries.append(fields)

    return entries


def group_by_tag(entries: list[dict]) -> dict[str, list[str]]:
    """按标签字段分组，返回 {tag: [table_rows]}。"""
    groups: dict[str, list[str]] = {}
    for fields in entries:
        tag = fields.get("标签", "UNKNOWN")
        # 归一化 BG(xxx) → BG
        if tag.startswith("BG"):
            tag = "BG"
        if tag not in groups:
            groups[tag] = []
        groups[tag].append(fields_to_row(fields))
    return groups


def generate_output(groups: dict[str, list[str]]) -> str:
    """生成标准输出：每个标签一个 section + 表格。"""
    lines: list[str] = []
    for tag in sorted(groups.keys()):
        rows = groups[tag]
        lines.append(f"# {tag}\n")
        lines.append(TABLE_HEADER)
        for row in rows:
            lines.append(row)
        lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def process_file(input_path: Path, output_path: Path) -> dict:
    """处理单个文件，返回状态信息。"""
    try:
        content = input_path.read_text(encoding="utf-8")
    except Exception as e:
        return {"status": "ERROR", "msg": f"Cannot read: {e}", "papers": 0}

    if not content.strip():
        return {"status": "SKIP", "msg": "Empty file", "papers": 0}

    entries = parse_entries(content)

    if not entries:
        return {"status": "WARN", "msg": "No papers parsed", "papers": 0}

    groups = group_by_tag(entries)
    output = generate_output(groups)
    output_path.write_text(output, encoding="utf-8")

    paper_count = len(entries)
    section_count = len(groups)
    return {"status": "OK", "msg": f"{section_count} sections, {paper_count} papers",
            "papers": paper_count}


def main():
    parser = argparse.ArgumentParser(
        description="Convert agent raw key-value pool files to standard table format"
    )
    parser.add_argument("--input-dir", required=True,
                        help="Directory containing _tmp_pool_agent*_raw.md files")
    parser.add_argument("--prepare-json", default=None,
                        help="Path to _pool_prepare.json (for logging only)")
    args = parser.parse_args()

    input_dir = Path(args.input_dir)

    raw_files = sorted(input_dir.glob("_tmp_pool_agent*_raw.md"))
    if not raw_files:
        print("ERROR: No _tmp_pool_agent*_raw.md files found.", file=sys.stderr)
        sys.exit(1)

    print("=== FORMAT POOL AGENTS ===")
    if args.prepare_json:
        print(f"Prepare JSON: {args.prepare_json}")
    print(f"Input dir: {input_dir}")
    print(f"Files found: {len(raw_files)}")
    print()

    total_papers = 0
    all_pass = True

    for fp in raw_files:
        out_name = fp.name.replace("_raw", "")
        output_path = input_dir / out_name

        result = process_file(fp, output_path)

        status_icon = {"OK": "OK", "WARN": "WARN", "ERROR": "FAIL", "SKIP": "SKIP"
                        }.get(result["status"], result["status"])

        print(f"  {fp.name} -> {out_name}: {status_icon} — {result['msg']}")
        total_papers += result["papers"]

        if result["status"] in ("ERROR",):
            all_pass = False

    print()
    print(f"Total papers formatted: {total_papers}")
    print()

    if all_pass and total_papers > 0:
        print("VERIFY: PASS")
    elif total_papers > 0:
        print("VERIFY: PASS (with warnings)")
    else:
        print("VERIFY: FAIL — no papers were formatted")
        sys.exit(1)


if __name__ == "__main__":
    main()
