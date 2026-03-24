#!/usr/bin/env python3
"""
pool_merge.py — 合并 SubAgent 临时文件为 citation_pool/ 目录（lit-pool §4）

读取 SubAgent 产出的临时 markdown 文件，按标签组装 citation_pool/ 下的
BG.md / LR.md / GAP.md / METHOD.md / DISC.md / COMP.md。

替代主 Agent 的 bash 拼接，避免 header 重复和数据丢失。

用法:
    python3 pool_merge.py \
        --tmp-dir structure/2_literature/ \
        --output-dir structure/2_literature/citation_pool/ \
        --prepare-json structure/2_literature/_pool_prepare.json

输出:
    1. stdout 结构化摘要 + 校验结果
    2. citation_pool/ 下的标签文件
"""

import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path


# ---------------------------------------------------------------------------
# 标签 → 文件映射
# ---------------------------------------------------------------------------

TAG_FILE_MAP = {
    "BG": "BG.md",
    "LR": "LR.md",
    "METHOD-基础": "METHOD.md",
    "METHOD-先例": "METHOD.md",
    "COMP": "COMP.md",
}
# GAP-RQx → GAP.md, DISC-RQx → DISC.md 动态处理

TAG_FULL_NAMES = {
    "BG": "Background",
    "LR": "Literature Review",
    "GAP": "Gap Support",
    "METHOD": "Methodology",
    "DISC": "Discussion",
    "COMP": "Competitor",
}

TAG_CHAPTER_MAP = {
    "BG": "Introduction [主]",
    "LR": "Literature Review [主]",
    "GAP": "Introduction + Literature Review",
    "METHOD": "Methodology [主]",
    "DISC": "Discussion [主]",
    "COMP": "跨章节",
}

TAG_CITE_PREF = {
    "BG": "优先近3年高质量期刊",
    "LR": "优先高引经典 + 理论脉络文献",
    "GAP": "优先同主题不同视角的文献",
    "METHOD": "优先方法论原始文献 + 应用先例",
    "DISC": "优先可对话的实证结果",
    "COMP": "优先高度相似的研究",
}


def get_target_file(tag: str) -> str:
    """标签 → 目标文件名。"""
    if tag in TAG_FILE_MAP:
        return TAG_FILE_MAP[tag]
    if tag.startswith("GAP"):
        return "GAP.md"
    if tag.startswith("DISC"):
        return "DISC.md"
    if tag.startswith("METHOD"):
        return "METHOD.md"
    return f"{tag}.md"


def get_tag_group(tag: str) -> str:
    """标签 → 大组名。"""
    if tag.startswith("GAP"):
        return "GAP"
    if tag.startswith("DISC"):
        return "DISC"
    if tag.startswith("METHOD"):
        return "METHOD"
    return tag


# ---------------------------------------------------------------------------
# 解析临时文件
# ---------------------------------------------------------------------------

def parse_tmp_files(tmp_dir: Path) -> dict[str, list[dict]]:
    """读取所有 _tmp_pool_agent*.md 文件，按标签分组提取表格行。"""
    tag_rows: dict[str, list[str]] = defaultdict(list)

    tmp_files = sorted(tmp_dir.glob("_tmp_pool_agent*.md"))
    if not tmp_files:
        print("ERROR: No _tmp_pool_agent*.md files found", file=sys.stderr)
        sys.exit(1)

    for fp in tmp_files:
        try:
            with open(fp, encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            print(f"WARNING: Cannot read {fp}: {e}", file=sys.stderr)
            continue

        # 检测当前处理的标签（通过 section header）
        current_tags: list[str] = []
        for line in content.split("\n"):
            # 匹配 section header（如 "# BG" "# LR, BG, DISC-RQ1" "## GAP-RQ1"）
            tag_match = re.match(r"#{1,3}\s+(.+)", line)
            if tag_match:
                header_text = tag_match.group(1).strip()
                # 按逗号拆分，支持组合标签
                candidate_tags = [t.strip() for t in header_text.split(",")]
                valid_tags = []
                for potential_tag in candidate_tags:
                    # 归一化：BG(2024-2026) → BG
                    if potential_tag.startswith("BG"):
                        potential_tag = "BG"
                    # 验证是否是有效标签
                    if (potential_tag in TAG_FILE_MAP or
                        potential_tag.startswith("GAP-RQ") or
                        potential_tag.startswith("DISC-RQ") or
                        potential_tag in ("BG", "LR", "COMP") or
                        potential_tag.startswith("METHOD")):
                        valid_tags.append(potential_tag)
                if valid_tags:
                    current_tags = valid_tags

            # 收集表格行（排除 header 行和分隔线）
            if current_tags and line.startswith("|"):
                # 跳过分隔线
                if re.match(r"\|[\s:-]+\|", line):
                    continue
                # 跳过表头行：检查第一个 cell 是否为表头关键词（不用 re.search 避免误匹配数据行）
                cells = [c.strip() for c in line.split("|") if c.strip()]
                if cells and cells[0] in ("分级", "#", "Tier", "Grade", "标签"):
                    continue
                # 有实质内容的表格行 → 分配到所有当前标签
                if re.match(r"\|\s*\S", line):
                    for tag in current_tags:
                        tag_rows[tag].append(line)

    return {tag: rows for tag, rows in tag_rows.items()}


# ---------------------------------------------------------------------------
# 组装标签文件
# ---------------------------------------------------------------------------

TABLE_HEADER_NORMAL = (
    "| 分级 | 作者 | 年份 | citation key | 引用场景 | 期刊 |\n"
    "|:----:|:-----|:----:|:------------|:---------|:-----|\n"
)

TABLE_HEADER_COMP = (
    "| 分级 | 作者 | 年份 | citation key | 引用场景 | 与本研究的关键差异 | 期刊 |\n"
    "|:----:|:-----|:----:|:------------|:---------|:------------------|:-----|\n"
)


def assemble_files(tag_rows: dict[str, list[str]], output_dir: Path) -> dict[str, int]:
    """按标签组装文件，返回每个文件的行数。"""
    output_dir.mkdir(parents=True, exist_ok=True)

    # 按目标文件分组
    file_sections: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    for tag, rows in tag_rows.items():
        target = get_target_file(tag)
        file_sections[target][tag] = rows

    file_counts = {}

    for filename, sections in file_sections.items():
        group = get_tag_group(list(sections.keys())[0])
        full_name = TAG_FULL_NAMES.get(group, group)
        chapter = TAG_CHAPTER_MAP.get(group, "")
        cite_pref = TAG_CITE_PREF.get(group, "")

        total_rows = sum(len(rows) for rows in sections.values())

        lines = []
        lines.append(f"# {group} — {full_name}（{total_rows}篇）\n")
        lines.append(f"> **生成日期**: {date.today().isoformat()}")
        lines.append(f"> **引用偏好**: {cite_pref}")
        lines.append(f"> **服务章节**: {chapter}")
        lines.append("")

        # 如果有多个子标签（如 GAP-RQ1, GAP-RQ2），按子section组织
        if len(sections) > 1:
            for tag in sorted(sections.keys()):
                rows = sections[tag]
                lines.append(f"## {tag}（{len(rows)}篇）\n")
                header = TABLE_HEADER_COMP if group == "COMP" else TABLE_HEADER_NORMAL
                lines.append(header)
                for row in rows:
                    lines.append(row)
                lines.append("")
        else:
            tag = list(sections.keys())[0]
            rows = sections[tag]
            header = TABLE_HEADER_COMP if group == "COMP" else TABLE_HEADER_NORMAL
            lines.append(header)
            for row in rows:
                lines.append(row)
            lines.append("")

        content = "\n".join(lines)
        filepath = output_dir / filename
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        file_counts[filename] = total_rows

    return file_counts


# ---------------------------------------------------------------------------
# 校验
# ---------------------------------------------------------------------------

def verify(tag_rows: dict[str, list[str]], file_counts: dict[str, int],
           output_dir: Path, prepare_json: str | None) -> list[str]:
    """内建校验。"""
    errors = []

    # 1. 输入行数 vs 输出行数
    total_input = sum(len(rows) for rows in tag_rows.values())
    total_output = sum(file_counts.values())
    if total_input != total_output:
        errors.append(f"ROW_MISMATCH: input={total_input} rows, output={total_output} rows")

    # 2. 回读输出文件，验证行数
    for filename, expected in file_counts.items():
        filepath = output_dir / filename
        if not filepath.exists():
            errors.append(f"FILE_MISSING: {filename} not created")
            continue
        with open(filepath, encoding="utf-8") as f:
            content = f.read()
        # 计数实质表格行
        actual = len([
            line for line in content.split("\n")
            if line.startswith("|") and not re.match(r"\|[\s:-]+\|", line)
            and not (line.split("|")[1].strip() if len(line.split("|")) > 1 else "") in ("分级", "#", "Tier", "Grade", "标签")
            and re.match(r"\|\s*\S", line)
        ])
        if actual != expected:
            errors.append(f"FILE_ROW_MISMATCH: {filename} expected={expected}, actual={actual}")

    # 3. 每个文件只有 1 个一级 header
    for filename in file_counts:
        filepath = output_dir / filename
        if not filepath.exists():
            continue
        with open(filepath, encoding="utf-8") as f:
            content = f.read()
        h1_count = len(re.findall(r"^# ", content, re.MULTILINE))
        if h1_count != 1:
            errors.append(f"HEADER_COUNT: {filename} has {h1_count} H1 headers (expected 1)")

    # 4. 与 prepare JSON 交叉校验（如有）
    # pool_prepare 的 tag_groups 可能含复合标签组名（如 "LR METHOD-先例"），
    # 而 subAgent 输出的 section 是拆分后的个体标签（如 "LR"、"METHOD-先例"）。
    # 验证时需把复合标签拆成个体再比较。
    if prepare_json:
        try:
            with open(prepare_json, encoding="utf-8") as f:
                prep = json.load(f)
            # 拆分复合标签为个体标签集合，并归一化
            expected_individual = set()
            for tg in prep.get("tag_groups", []):
                if tg["count"] > 0:
                    # "LR METHOD-先例" → {"LR", "METHOD-先例"}
                    for t in re.split(r"\s+", tg["tag"]):
                        t = t.strip()
                        if t:
                            # 归一化：BG(2024-2026) → BG
                            if t.startswith("BG"):
                                t = "BG"
                            expected_individual.add(t)
            actual_tags = set(tag_rows.keys())
            missing = expected_individual - actual_tags
            if missing:
                errors.append(f"TAGS_MISSING: expected from prepare but not in tmp files: {missing}")
        except Exception:
            pass  # prepare JSON is optional

    return errors


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Merge tmp pool files into citation_pool/")
    parser.add_argument("--tmp-dir", required=True,
                        help="Directory containing _tmp_pool_agent*.md files")
    parser.add_argument("--output-dir", required=True,
                        help="Output directory (citation_pool/)")
    parser.add_argument("--prepare-json", default=None,
                        help="Path to _pool_prepare.json for cross-validation")
    parser.add_argument("--clean-tmp", action="store_true",
                        help="Delete tmp files after successful merge")
    args = parser.parse_args()

    tmp_dir = Path(args.tmp_dir)
    output_dir = Path(args.output_dir)

    # 1. 解析临时文件
    tag_rows = parse_tmp_files(tmp_dir)

    # 2. 组装文件
    file_counts = assemble_files(tag_rows, output_dir)

    # 3. 校验
    errors = verify(tag_rows, file_counts, output_dir, args.prepare_json)

    # 4. 清理临时文件
    if args.clean_tmp and not errors:
        for fp in tmp_dir.glob("_tmp_pool_agent*.md"):
            fp.unlink()
        print("Cleaned tmp files.", file=sys.stderr)

    # ===== stdout 结构化摘要 =====
    print("=== POOL MERGE ===")
    print(f"Tmp files parsed: {len(list(tmp_dir.glob('_tmp_pool_agent*.md')))}")
    print(f"Tags found: {', '.join(sorted(tag_rows.keys()))}")
    print(f"Total rows: {sum(len(r) for r in tag_rows.values())}")
    print()

    print("Output files:")
    for filename, count in sorted(file_counts.items()):
        print(f"  {filename}: {count} entries")
    print()

    if errors:
        print("=== VERIFY: FAIL ===")
        for e in errors:
            print(f"  ❌ {e}")
        sys.exit(1)
    else:
        print("=== VERIFY: PASS ===")
        print(f"Output directory: {output_dir}")


if __name__ == "__main__":
    main()
