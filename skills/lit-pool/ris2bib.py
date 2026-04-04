#!/usr/bin/env python3
"""
ris2bib.py — RIS → BibTeX 批量转换（lit-pool §8）

读取 RIS 文件 + citation key 映射表，匹配后输出 master.bib。
处理多作者、特殊字符、UTF-8 BOM 等边界情况。

替代主 Agent 的手动格式转换。

用法:
    python3 ris2bib.py \
        --ris-dir structure/2_literature/ \
        --prepare-json structure/2_literature/_pool_prepare.json \
        --output structure/2_literature/citation_pool/master.bib

输出:
    1. stdout 结构化摘要 + 校验结果
    2. master.bib 文件
"""

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path


# ---------------------------------------------------------------------------
# RIS 解析
# ---------------------------------------------------------------------------

def parse_all_ris(ris_dir: Path) -> list[dict]:
    """解析目录下所有 RIS 文件的条目。"""
    all_entries = []

    for fp in sorted(ris_dir.glob("*.ris")):
        try:
            with open(fp, encoding="utf-8-sig") as f:
                content = f.read()
        except Exception as e:
            print(f"WARNING: Cannot read {fp}: {e}", file=sys.stderr)
            continue

        # 按 TY 分割
        raw_entries = re.split(r"(?=^TY  - )", content, flags=re.MULTILINE)
        for raw in raw_entries:
            if not raw.strip().startswith("TY  -"):
                continue

            entry = {"_raw": raw, "_source": fp.name}

            # 解析字段（支持 RIS 多行续行：续行以空格开头，无 XX  - 前缀）
            current_tag = None
            current_val = None
            for line in raw.split("\n"):
                m = re.match(r"^([A-Z][A-Z0-9])  - (.*)$", line)
                if m:
                    # 先保存上一个字段
                    if current_tag is not None:
                        val = current_val.strip()
                        if current_tag == "AU":
                            entry.setdefault("AU", []).append(val)
                        elif current_tag in entry:
                            if isinstance(entry[current_tag], list):
                                entry[current_tag].append(val)
                            else:
                                entry[current_tag] = [entry[current_tag], val]
                        else:
                            entry[current_tag] = val
                    current_tag = m.group(1)
                    current_val = m.group(2)
                elif current_tag and line.startswith("      "):
                    # RIS 续行（6个空格缩进）
                    current_val += " " + line.strip()
                elif current_tag and line.startswith(" "):
                    # 宽松续行匹配（任意空格开头）
                    current_val += " " + line.strip()
            # 保存最后一个字段
            if current_tag is not None:
                val = current_val.strip()
                if current_tag == "AU":
                    entry.setdefault("AU", []).append(val)
                elif current_tag in entry:
                    if isinstance(entry[current_tag], list):
                        entry[current_tag].append(val)
                    else:
                        entry[current_tag] = [entry[current_tag], val]
                else:
                    entry[current_tag] = val

            all_entries.append(entry)

    return all_entries


def normalize_for_match(s: str) -> str:
    """用于标题匹配的归一化。"""
    s = s.lower().strip()
    s = unicodedata.normalize("NFKD", s)
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


# ---------------------------------------------------------------------------
# 匹配 citation key → RIS 条目
# ---------------------------------------------------------------------------

def match_papers(papers: list[dict], ris_entries: list[dict]) -> list[tuple[dict, dict | None]]:
    """将 citation key 映射表中的文献与 RIS 条目匹配。"""
    # 建立 RIS 索引
    # key = (first_author_lower, year)
    ris_by_author_year: dict[str, list[dict]] = {}
    for entry in ris_entries:
        authors = entry.get("AU", [])
        fa = authors[0].split(",")[0].strip().lower() if authors else ""
        year = entry.get("PY", "")[:4]
        key = f"{fa}|{year}"
        ris_by_author_year.setdefault(key, []).append(entry)

    results = []
    for paper in papers:
        fa = paper["author"].split(",")[0].split(";")[0].strip().lower()
        year = str(paper["year"])
        key = f"{fa}|{year}"

        candidates = ris_by_author_year.get(key, [])
        matched = None

        if len(candidates) == 1:
            matched = candidates[0]
        elif len(candidates) > 1:
            # 用标题区分
            paper_ti = normalize_for_match(paper["title"])
            best_score = 0
            for cand in candidates:
                cand_ti = normalize_for_match(cand.get("TI", ""))
                # 前缀匹配
                min_len = min(len(paper_ti), len(cand_ti), 40)
                if paper_ti[:min_len] == cand_ti[:min_len]:
                    score = min_len
                    if score > best_score:
                        best_score = score
                        matched = cand

        results.append((paper, matched))

    return results


# ---------------------------------------------------------------------------
# RIS → BibTeX 转换
# ---------------------------------------------------------------------------

def escape_bibtex(s: str) -> str:
    """转义 BibTeX 特殊字符。"""
    # 保留花括号内的内容
    s = s.replace("&", r"\&")
    s = s.replace("%", r"\%")
    s = s.replace("#", r"\#")
    s = s.replace("_", r"\_")
    return s


def ris_to_bibtex(paper: dict, ris: dict) -> str:
    """将一条 RIS 条目转为 BibTeX 格式。"""
    ck = paper["citation_key"]

    # 文献类型
    ty = ris.get("TY", "JOUR")
    if ty in ("JOUR", "ABST"):
        bib_type = "article"
    elif ty in ("CONF", "CPAPER"):
        bib_type = "inproceedings"
    elif ty in ("BOOK", "EDITED"):
        bib_type = "book"
    elif ty in ("CHAP", "CHAPT"):
        bib_type = "incollection"
    elif ty in ("THES", "DISS"):
        bib_type = "phdthesis"
    elif ty == "RPRT":
        bib_type = "techreport"
    else:
        bib_type = "article"

    # 作者
    authors = ris.get("AU", [])
    if isinstance(authors, str):
        authors = [authors]
    author_str = " and ".join(authors) if authors else paper["author"]
    author_str = escape_bibtex(author_str)

    # 标题
    title = ris.get("TI", paper["title"])
    title = escape_bibtex(title)
    # 用花括号保护大写
    title = f"{{{title}}}"

    # 期刊
    journal = ris.get("T2", ris.get("JO", ris.get("JF", paper.get("journal", ""))))
    journal = escape_bibtex(journal) if journal else ""

    # 年份
    year = ris.get("PY", str(paper["year"]))[:4]

    # 卷期页
    volume = ris.get("VL", "")
    number = ris.get("IS", "")
    sp = ris.get("SP", "")
    ep = ris.get("EP", "")
    pages = f"{sp}--{ep}" if sp and ep else sp

    # DOI
    doi = ris.get("DO", ris.get("DI", ""))

    # 构建 BibTeX
    lines = [f"@{bib_type}{{{ck},"]
    lines.append(f"  author = {{{author_str}}},")
    lines.append(f"  title = {title},")
    if journal:
        field = "journal" if bib_type == "article" else "booktitle"
        lines.append(f"  {field} = {{{journal}}},")
    lines.append(f"  year = {{{year}}},")
    if volume:
        lines.append(f"  volume = {{{volume}}},")
    if number:
        lines.append(f"  number = {{{number}}},")
    if pages:
        lines.append(f"  pages = {{{pages}}},")
    if doi:
        lines.append(f"  doi = {{{doi}}},")

    # 检测中文文献标记（由 cnki_enw_to_ris.py 转换时添加 N1  - LA:zh）
    n1_vals = ris.get("N1", [])
    if isinstance(n1_vals, str):
        n1_vals = [n1_vals]
    if any("LA:zh" in v for v in n1_vals):
        lines.append(f"  language = {{chinese}},")

    lines.append("}")

    return "\n".join(lines)


def make_stub_bibtex(paper: dict) -> str:
    """为未匹配到 RIS 的文献生成 stub BibTeX。"""
    ck = paper["citation_key"]
    author = escape_bibtex(paper["author"])
    title = escape_bibtex(paper["title"])
    journal = escape_bibtex(paper.get("journal", ""))
    year = str(paper["year"])

    lines = [f"@article{{{ck},"]
    lines.append(f"  author = {{{author}}},")
    lines.append(f"  title = {{{title}}},")
    if journal:
        lines.append(f"  journal = {{{journal}}},")
    lines.append(f"  year = {{{year}}},")
    lines.append(f"  note = {{TODO: Complete this entry manually}},")
    lines.append("}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 校验
# ---------------------------------------------------------------------------

def verify(bib_content: str, total_papers: int, matched: int,
           unmatched: int, output_path: str) -> list[str]:
    """内建校验。"""
    errors = []

    # 1. 数量一致性
    if matched + unmatched != total_papers:
        errors.append(f"COUNT_MISMATCH: matched({matched}) + unmatched({unmatched}) != total({total_papers})")

    # 2. BibTeX 条目数
    bib_entries = len(re.findall(r"^@\w+\{", bib_content, re.MULTILINE))
    if bib_entries != total_papers:
        errors.append(f"BIB_COUNT: {bib_entries} entries in bib, expected {total_papers}")

    # 3. 括号平衡检查（基础语法）
    brace_depth = 0
    for ch in bib_content:
        if ch == '{':
            brace_depth += 1
        elif ch == '}':
            brace_depth -= 1
        if brace_depth < 0:
            errors.append("BRACE_MISMATCH: unmatched closing brace found")
            break
    if brace_depth != 0:
        errors.append(f"BRACE_MISMATCH: {brace_depth} unclosed braces")

    # 4. 每条必须有 author + title + year
    for m in re.finditer(r"@\w+\{(\w+),\s*(.*?)\n\}", bib_content, re.DOTALL):
        key = m.group(1)
        body = m.group(2)
        for field in ["author", "title", "year"]:
            if f"{field} =" not in body:
                errors.append(f"MISSING_FIELD: {key} lacks '{field}'")

    # 5. 回读文件
    try:
        with open(output_path, encoding="utf-8") as f:
            readback = f.read()
        if readback != bib_content:
            errors.append("READBACK_MISMATCH: written content differs from expected")
    except Exception as e:
        errors.append(f"READBACK_ERROR: {e}")

    return errors


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Convert RIS to BibTeX using citation key mapping")
    parser.add_argument("--ris-dir", required=True,
                        help="Directory containing RIS files")
    parser.add_argument("--prepare-json", required=True,
                        help="Path to _pool_prepare.json (citation key mapping)")
    parser.add_argument("--output", required=True,
                        help="Output .bib file path")
    args = parser.parse_args()

    ris_dir = Path(args.ris_dir)

    # 1. 读取 citation key 映射
    try:
        with open(args.prepare_json, encoding="utf-8") as f:
            prep = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"ERROR: Cannot read {args.prepare_json}: {e}", file=sys.stderr)
        sys.exit(1)

    papers = prep.get("papers", [])
    if not papers:
        print("ERROR: No papers in prepare JSON", file=sys.stderr)
        sys.exit(1)

    # 2. 解析 RIS
    ris_entries = parse_all_ris(ris_dir)
    print(f"  Parsed {len(ris_entries)} RIS entries from {ris_dir}", file=sys.stderr)

    # 3. 匹配
    results = match_papers(papers, ris_entries)

    # 4. 生成 BibTeX
    bib_blocks = []
    matched_count = 0
    unmatched_count = 0
    unmatched_list = []

    for paper, ris in results:
        if ris:
            bib_blocks.append(ris_to_bibtex(paper, ris))
            matched_count += 1
        else:
            bib_blocks.append(make_stub_bibtex(paper))
            unmatched_count += 1
            unmatched_list.append(f"  {paper['citation_key']}: {paper['author']} ({paper['year']}) - {paper['title'][:60]}")

    bib_content = "\n\n".join(bib_blocks) + "\n"

    # 5. 写入
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(bib_content)

    # 6. 校验
    errors = verify(bib_content, len(papers), matched_count, unmatched_count, str(output_path))

    # ===== stdout 结构化摘要 =====
    print("=== RIS2BIB ===")
    print(f"Citation keys: {len(papers)}")
    print(f"RIS entries: {len(ris_entries)}")
    print(f"Matched: {matched_count}")
    print(f"Unmatched: {unmatched_count}")
    if unmatched_list:
        print()
        print("Unmatched papers (stub entries created):")
        for item in unmatched_list:
            print(item)
    print()

    if errors:
        print("=== VERIFY: FAIL ===")
        for e in errors:
            print(f"  ❌ {e}")
        sys.exit(1)
    else:
        print("=== VERIFY: PASS ===")
        print(f"Output: {args.output}")
        print(f"Entries: {len(papers)}")


if __name__ == "__main__":
    main()
