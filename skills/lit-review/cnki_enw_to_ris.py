#!/usr/bin/env python3
"""
cnki_enw_to_ris.py — CNKI EndNote (.enw) → 标准 RIS 格式转换

将中国知网导出的 EndNote 格式文献转换为标准 RIS 格式，
使其能无缝接入现有的 /lit-review → /lit-tag → /lit-pool 管线。

用法:
    python3 cnki_enw_to_ris.py --input data.enw --output data.ris
    python3 cnki_enw_to_ris.py --input data.enw --output data.ris --skip-newspaper
    python3 cnki_enw_to_ris.py --input data.enw --output data.ris --dry-run

功能:
    - 字段映射: %0→TY, %A→AU, %T→TI, %J→T2, %K→KW, %X→AB, 等
    - 年份提取: 从 %8(日期)、%R(DOI)、%U(URL) 中尽量推断出版年
    - 关键词拆分: 分号分隔的关键词拆分为逐行 KW
    - 页码拆分: "1-15" → SP + EP
    - 报纸过滤: --skip-newspaper 跳过 Newspaper Article 类型
    - 中文作者保持原样（拼音转换在 pool_prepare.py 阶段处理）
"""

import argparse
import re
import sys
from pathlib import Path


# ── CNKI ENW → RIS 类型映射 ──────────────────────────────────────────────────
TYPE_MAP = {
    "Journal Article": "JOUR",
    "Newspaper Article": "NEWS",
    "Thesis": "THES",
    "Dissertation": "THES",
    "Conference Proceedings": "CONF",
    "Conference Paper": "CONF",
    "Book": "BOOK",
    "Book Section": "CHAP",
    "Report": "RPRT",
    "Patent": "PAT",
}


def parse_enw(text: str) -> list[dict]:
    """解析 ENW 文件，返回记录列表。每条记录为 {tag: [values]} 字典。"""
    records = []
    current = {}
    current_tag = None

    for line in text.splitlines():
        # 空行 = 记录分隔符
        if not line.strip():
            if current:
                records.append(current)
                current = {}
                current_tag = None
            continue

        # ENW 标签行: %X value（%后跟单个字符：字母、数字或特殊符号）
        match = re.match(r"^(%[A-Za-z0-9@+#*!?~])\s+(.*)$", line)
        if match:
            tag = match.group(1)
            value = match.group(2).strip()
            current_tag = tag
            current.setdefault(tag, []).append(value)
        else:
            # 续行（摘要等长文本可能换行，但 CNKI 导出一般不换行）
            if current_tag and current.get(current_tag):
                current[current_tag][-1] += " " + line.strip()

    # 文件末尾没有空行的情况
    if current:
        records.append(current)

    return records


def extract_year(record: dict) -> str | None:
    """从记录中尽量提取出版年份。优先级: %D > %8 > URL > DOI。"""

    # %D 日期字段（CNKI 通常不导出，但以防万一）
    if "%D" in record:
        m = re.search(r"(\d{4})", record["%D"][0])
        if m:
            return m.group(1)

    # %8 日期字段（报纸类有）
    if "%8" in record:
        m = re.search(r"(\d{4})", record["%8"][0])
        if m:
            return m.group(1)

    # 从 URL 提取（CNKI URL 中常含年份信息）
    if "%U" in record:
        url = record["%U"][0]
        # 模式1: urlid/XX.XXXX.X.20260402... → 2026
        m = re.search(r"\.(\d{4})\d{4}\.\d+\.\d+$", url)
        if m:
            return m.group(1)
        # 模式2: doi URL 中可能含年份
        m = re.search(r"/(\d{4})\d+\.\d+", url)
        if m:
            year_candidate = m.group(1)
            if 1900 <= int(year_candidate) <= 2100:
                return year_candidate

    # 从 DOI 提取
    if "%R" in record:
        doi = record["%R"][0]
        m = re.search(r"\.(\d{4})\d*\.", doi)
        if m:
            year_candidate = m.group(1)
            if 1900 <= int(year_candidate) <= 2100:
                return year_candidate

    return None


def split_pages(page_str: str) -> tuple[str, str]:
    """将 '1-15' 拆分为 (start, end)。"""
    parts = re.split(r"[-–—]", page_str.strip(), maxsplit=1)
    if len(parts) == 2:
        return parts[0].strip(), parts[1].strip()
    return page_str.strip(), ""


def record_to_ris(record: dict, skip_newspaper: bool = False) -> str | None:
    """将单条 ENW 记录转换为 RIS 格式字符串。返回 None 表示跳过。"""

    # 获取文献类型
    doc_type = record.get("%0", ["Journal Article"])[0]

    if skip_newspaper and doc_type == "Newspaper Article":
        return None

    ris_type = TYPE_MAP.get(doc_type, "GEN")

    lines = [f"TY  - {ris_type}"]

    # 作者（每个 %A 一行）
    for author in record.get("%A", []):
        author = author.strip()
        if author:
            lines.append(f"AU  - {author}")

    # 标题
    for title in record.get("%T", []):
        lines.append(f"TI  - {title}")

    # 期刊
    for journal in record.get("%J", []):
        lines.append(f"T2  - {journal}")

    # 年份
    year = extract_year(record)
    if year:
        lines.append(f"PY  - {year}")

    # 摘要
    for abstract in record.get("%X", []):
        lines.append(f"AB  - {abstract}")

    # 关键词（分号分隔 → 逐行）
    for kw_line in record.get("%K", []):
        for kw in re.split(r"[;；]", kw_line):
            kw = kw.strip()
            if kw:
                lines.append(f"KW  - {kw}")

    # 页码
    for pages in record.get("%P", []):
        sp, ep = split_pages(pages)
        if sp:
            lines.append(f"SP  - {sp}")
        if ep:
            lines.append(f"EP  - {ep}")

    # ISSN
    for issn in record.get("%@", []):
        lines.append(f"SN  - {issn}")

    # DOI
    for doi in record.get("%R", []):
        lines.append(f"DO  - {doi}")

    # URL
    for url in record.get("%U", []):
        lines.append(f"UR  - {url}")

    # 机构
    for inst in record.get("%+", []):
        lines.append(f"AD  - {inst}")

    # 出版商
    for pub in record.get("%I", []):
        lines.append(f"PB  - {pub}")

    # 数据源标记（保留，方便后续识别 CNKI 来源）
    for ds in record.get("%W", []):
        lines.append(f"N1  - DS:{ds}")

    # 中国刊号（保留为自定义字段）
    for cn in record.get("%L", []):
        lines.append(f"N1  - CN:{cn}")

    # 语言（如果有）
    # CNKI ENW 格式没有单独的语言字段，但可以从内容推断
    # 这里标记为中文，后续管线可据此区分
    lines.append("N1  - LA:zh")

    lines.append("ER  - ")

    return "\n".join(lines)


def convert(input_path: Path, output_path: Path, skip_newspaper: bool = False,
            dry_run: bool = False) -> tuple[dict, list[str]]:
    """执行单文件转换，返回 (统计信息dict, 警告列表)。供外部调用。"""

    text = input_path.read_text(encoding="utf-8")
    records = parse_enw(text)

    stats = {
        "total_parsed": len(records),
        "converted": 0,
        "skipped_newspaper": 0,
        "year_missing": 0,
        "year_extracted": 0,
        "types": {},
    }

    ris_blocks = []
    warnings = []

    for i, record in enumerate(records, 1):
        doc_type = record.get("%0", ["Unknown"])[0]
        stats["types"][doc_type] = stats["types"].get(doc_type, 0) + 1

        ris = record_to_ris(record, skip_newspaper=skip_newspaper)

        if ris is None:
            stats["skipped_newspaper"] += 1
            continue

        # 检查年份
        year = extract_year(record)
        title = record.get("%T", ["(无标题)"])[0]
        if year:
            stats["year_extracted"] += 1
        else:
            stats["year_missing"] += 1
            warnings.append(f"  ⚠ 第{i}条 年份缺失: {title[:50]}")

        ris_blocks.append(ris)
        stats["converted"] += 1

    # 输出
    if not dry_run:
        output_path.write_text("\n\n".join(ris_blocks) + "\n", encoding="utf-8")

    return stats, warnings


def main():
    parser = argparse.ArgumentParser(
        description="CNKI EndNote (.enw) → RIS 格式转换"
    )
    parser.add_argument("--input", "-i", required=True, nargs='+',
                        help="输入 .enw 文件路径（支持多个文件）")
    parser.add_argument("--output", "-o", required=True, help="输出 .ris 文件路径")
    parser.add_argument("--skip-newspaper", action="store_true",
                        help="跳过报纸类文献 (Newspaper Article)")
    parser.add_argument("--dry-run", action="store_true",
                        help="仅预览统计，不写文件")
    args = parser.parse_args()

    output_path = Path(args.output)
    all_stats = {"total_parsed": 0, "converted": 0, "skipped_newspaper": 0,
                 "year_missing": 0, "year_extracted": 0, "types": {}}
    all_warnings = []
    all_ris_blocks = []

    for input_file in args.input:
        input_path = Path(input_file)
        if not input_path.exists():
            print(f"⚠ 跳过不存在的文件: {input_path}", file=sys.stderr)
            continue

        # 一次性解析：收集 RIS 块 + 统计
        text = input_path.read_text(encoding="utf-8")
        records = parse_enw(text)
        all_stats["total_parsed"] += len(records)

        for i, record in enumerate(records, 1):
            doc_type = record.get("%0", ["Unknown"])[0]
            all_stats["types"][doc_type] = all_stats["types"].get(doc_type, 0) + 1

            ris = record_to_ris(record, skip_newspaper=args.skip_newspaper)
            if ris is None:
                all_stats["skipped_newspaper"] += 1
                continue

            year = extract_year(record)
            title = record.get("%T", ["(无标题)"])[0]
            if year:
                all_stats["year_extracted"] += 1
            else:
                all_stats["year_missing"] += 1
                all_warnings.append(f"  ⚠ {input_path.name} 第{i}条 年份缺失: {title[:50]}")

            all_ris_blocks.append(ris)
            all_stats["converted"] += 1

    # 统一写入
    if not args.dry_run and all_ris_blocks:
        output_path.write_text("\n\n".join(all_ris_blocks) + "\n", encoding="utf-8")

    # 打印报告
    print("=" * 60)
    print("CNKI ENW → RIS 转换报告")
    print("=" * 60)
    print(f"输入文件: {', '.join(args.input)}")
    print(f"输出文件: {output_path}" + (" (dry-run, 未写入)" if args.dry_run else ""))
    print(f"解析记录数: {all_stats['total_parsed']}")
    print(f"成功转换: {all_stats['converted']}")
    if all_stats["skipped_newspaper"]:
        print(f"跳过报纸: {all_stats['skipped_newspaper']}")
    print(f"年份提取成功: {all_stats['year_extracted']}")
    print(f"年份缺失: {all_stats['year_missing']}")
    print()
    print("文献类型分布:")
    for t, n in sorted(all_stats["types"].items(), key=lambda x: -x[1]):
        print(f"  {t}: {n}")

    if all_warnings:
        print()
        print("警告:")
        for w in all_warnings:
            print(w)

    print("=" * 60)

    if all_stats["year_missing"] > 0:
        print(f"\n💡 提示: {all_stats['year_missing']}条文献年份缺失，"
              "建议在 RIS 文件中手动补充 PY 字段，或在 /lit-review 筛选时由 LLM 推断。")

    # 退出码: 有年份缺失用 0 (warning), 解析失败用 1
    sys.exit(0)


if __name__ == "__main__":
    main()
