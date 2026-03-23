#!/usr/bin/env python3
"""
format_pool_agents.py — 将 Agent 输出的 key-value 块格式转换为 pool_merge.py 所需的标准表格格式

读取 _tmp_pool_agent*_raw.md 文件（key-value 块格式），转换为标准 6 列表格，
输出为 _tmp_pool_agent*.md（去掉 _raw 后缀）。

如果输入文件已经是表格格式（fallback），直接复制不转换。

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

# 兼容 `- key: value` / `key: value` / `- key：value` / `key：value`
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
}


def normalize_field(raw: str) -> str | None:
    """归一化字段名，返回标准字段名或 None。"""
    key = raw.strip().lower().replace(" ", "").replace("_", "_")
    # 先精确匹配
    if key in FIELD_ALIASES:
        return FIELD_ALIASES[key]
    # 尝试带空格的原始形式
    key_with_space = raw.strip().lower()
    if key_with_space in FIELD_ALIASES:
        return FIELD_ALIASES[key_with_space]
    return None


def parse_kv_block(lines: list[str]) -> dict[str, str] | None:
    """从一组行中解析 key-value 对，返回标准字段字典。"""
    fields: dict[str, str] = {}
    for line in lines:
        m = KV_RE.match(line.strip())
        if not m:
            continue
        raw_key, raw_val = m.group(1), m.group(2).strip()
        std_key = normalize_field(raw_key)
        if std_key:
            fields[std_key] = raw_val

    # 最少需要 citation_key
    if "citation_key" not in fields:
        return None
    return fields


def fields_to_row(fields: dict[str, str]) -> str:
    """将字段字典转为标准表格行。"""
    grade = normalize_grade(fields.get("分级", "备选"))
    author = fields.get("作者", "—")
    year = fields.get("年份", "—")
    ckey = fields.get("citation_key", "—")
    scenario = fields.get("引用场景", "—")
    journal = fields.get("期刊", "—")
    return f"| {grade} | {author} | {year} | {ckey} | {scenario} | {journal} |"


# ---------------------------------------------------------------------------
# 文件级解析与转换
# ---------------------------------------------------------------------------

def is_table_format(content: str) -> bool:
    """检测文件是否已经是表格格式（含 | 开头的数据行）。"""
    data_lines = 0
    for line in content.split("\n"):
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        # 跳过表头分隔线
        if re.match(r"\|[\s:-]+\|", stripped):
            continue
        # 跳过表头行
        if re.search(r"分级|作者|citation|引用场景|期刊", stripped, re.IGNORECASE):
            continue
        if re.match(r"\|\s*\S", stripped):
            data_lines += 1
    return data_lines >= 1


TABLE_HEADER = (
    "| 分级 | 作者 | 年份 | citation key | 引用场景 | 期刊 |\n"
    "|:----:|:-----|:----:|:------------|:---------|:-----:|"
)


def convert_kv_to_table(content: str) -> tuple[str, int, int]:
    """
    将 key-value 块格式转换为表格格式。

    返回: (converted_content, paper_count, section_count)
    """
    output_lines: list[str] = []
    paper_count = 0
    section_count = 0

    current_section: str | None = None
    current_block_lines: list[str] = []
    section_rows: list[str] = []
    in_block = False

    def flush_block():
        nonlocal paper_count
        if not current_block_lines:
            return
        fields = parse_kv_block(current_block_lines)
        if fields:
            section_rows.append(fields_to_row(fields))
            paper_count += 1

    def flush_section():
        nonlocal section_count
        if current_section is not None and section_rows:
            output_lines.append(f"# {current_section}\n")
            output_lines.append(TABLE_HEADER)
            for row in section_rows:
                output_lines.append(row)
            output_lines.append("")
            section_count += 1
        elif current_section is not None:
            # section without papers — still emit header
            output_lines.append(f"# {current_section}\n")
            output_lines.append(TABLE_HEADER)
            output_lines.append("")
            section_count += 1

    for line in content.split("\n"):
        stripped = line.strip()

        # 检测 section header: `# TAG` 或 `# TAG(xxx)`
        section_match = re.match(r"^#\s+([A-Z][\w().-]*(?:-[A-Z]\w*)?)", stripped)
        if section_match:
            # flush previous
            flush_block()
            flush_section()
            current_block_lines = []
            section_rows = []
            in_block = False
            current_section = section_match.group(1).strip()
            # 归一化 BG(xxx) → BG
            if current_section.startswith("BG"):
                current_section = "BG"
            continue

        # 检测 paper 块开始: `### paperN` 或 `### N` 或 `### xxx`
        if re.match(r"^#{2,3}\s+", stripped):
            flush_block()
            current_block_lines = []
            in_block = True
            continue

        # 在块内收集 key-value 行
        if in_block and stripped:
            current_block_lines.append(stripped)

    # flush last block & section
    flush_block()
    flush_section()

    return "\n".join(output_lines), paper_count, section_count


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

    # Fallback: 已经是表格格式 → 直接复制
    if is_table_format(content):
        output_path.write_text(content, encoding="utf-8")
        # 计数数据行
        data_lines = 0
        for line in content.split("\n"):
            s = line.strip()
            if s.startswith("|") and not re.match(r"\|[\s:-]+\|", s) \
               and not re.search(r"分级|作者|citation|引用场景|期刊", s, re.IGNORECASE) \
               and re.match(r"\|\s*\S", s):
                data_lines += 1
        return {"status": "COPY", "msg": "Already table format, copied as-is",
                "papers": data_lines}

    # 转换 key-value → table
    converted, paper_count, section_count = convert_kv_to_table(content)

    if paper_count == 0:
        return {"status": "WARN", "msg": "No papers parsed from key-value blocks",
                "papers": 0}

    output_path.write_text(converted, encoding="utf-8")
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

    # 收集 _raw.md 文件
    raw_files = sorted(input_dir.glob("_tmp_pool_agent*_raw.md"))

    # 也收集不带 _raw 但已有的（非目标覆盖检查）
    if not raw_files:
        print("WARNING: No _tmp_pool_agent*_raw.md files found.", file=sys.stderr)
        # fallback: 尝试直接处理已有的 _tmp_pool_agent*.md
        fallback_files = sorted(input_dir.glob("_tmp_pool_agent*.md"))
        if not fallback_files:
            print("ERROR: No input files found at all.", file=sys.stderr)
            sys.exit(1)
        raw_files = fallback_files

    print("=== FORMAT POOL AGENTS ===")
    if args.prepare_json:
        print(f"Prepare JSON: {args.prepare_json}")
    print(f"Input dir: {input_dir}")
    print(f"Files found: {len(raw_files)}")
    print()

    total_papers = 0
    all_pass = True

    for fp in raw_files:
        # 确定输出路径：去掉 _raw
        if "_raw" in fp.name:
            out_name = fp.name.replace("_raw", "")
        else:
            out_name = fp.name  # fallback: 覆盖原文件
        output_path = input_dir / out_name

        result = process_file(fp, output_path)

        status_icon = {
            "OK": "OK",
            "COPY": "OK(copy)",
            "WARN": "WARN",
            "ERROR": "FAIL",
            "SKIP": "SKIP",
        }.get(result["status"], result["status"])

        print(f"  {fp.name} -> {out_name}: {status_icon} — {result['msg']}")
        total_papers += result["papers"]

        if result["status"] in ("ERROR", "WARN"):
            all_pass = False

    print()
    print(f"Total papers formatted: {total_papers}")

    # 验证：回读输出文件，确认可被 pool_merge.py 解析
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
