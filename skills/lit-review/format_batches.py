#!/usr/bin/env python3
"""
format_batches.py — Agent 输出格式标准化（lit-review §2.2）

将 Agent 输出的 key-value 块格式（*_raw.md）转换为
merge_screening.py 所需的标准 markdown 表格格式（*.md）。

设计原理：LLM 擅长分析判断，但不擅长产出精确的 markdown 表格。
Agent 只需输出 key-value 块（几乎不可能出格式错误），
本脚本负责确定性地转换为标准格式。

支持的输入格式：
1. key-value 块（新格式，推荐）：
   ### 入选1
   - 作者: Author Name
   - 标题: Paper Title
   - 年份: 2024
   - 期刊: Journal Name
   - 理由: 入选理由

2. markdown 表格（旧格式，兼容）：
   | # | 第一作者 | 标题 | 年份 | 期刊 | 入选理由 |

3. 混合格式（容错）

用法:
    python3 format_batches.py --batch-dir structure/2_literature/_batch/

输出:
    1. 标准化的 d*_batch*.md 文件
    2. stdout 结构化摘要 + VERIFY: PASS|FAIL
"""

import argparse
import re
import sys
import unicodedata
from pathlib import Path


# ---------------------------------------------------------------------------
# metadata extraction
# ---------------------------------------------------------------------------

# No hardcoded direction names — extract from metadata or filename only.
# Fallback: "方向{N}" if direction_name not found in file metadata.
DIR_NAMES: dict[str, str] = {}  # populated dynamically from batch metadata


def extract_metadata(text: str, filename: str) -> dict:
    """Extract metadata from various formats."""
    meta = {}

    # Try blockquote: > key: value
    for m in re.finditer(r"^>\s*(\w[\w_]*):\s*(.+)$", text, re.MULTILINE):
        meta[m.group(1).strip()] = m.group(2).strip()

    # Try bullet: - key: value (top-level metadata, not inside ### blocks)
    if "direction" not in meta:
        # Only match bullets before the first ### heading
        header_pos = text.find("### ")
        search_area = text[:header_pos] if header_pos > 0 else text[:500]
        for m in re.finditer(r"^[-*]\s*(\w[\w_]*):\s*(.+)$", search_area, re.MULTILINE):
            meta[m.group(1).strip()] = m.group(2).strip()

    # Try HTML comment: <!-- meta ... -->
    if "direction" not in meta:
        comment = re.search(r"<!--\s*meta\s*\n(.*?)-->", text, re.DOTALL)
        if comment:
            for m in re.finditer(r"(\w[\w_]*):\s*(.+)", comment.group(1)):
                meta[m.group(1).strip()] = m.group(2).strip()

    # Fallback: infer from filename
    fname_m = re.match(r"d(\d+)_batch(\d+)", filename.replace("_raw", ""))
    if fname_m:
        if "direction" not in meta:
            meta["direction"] = fname_m.group(1)
        if "batch_id" not in meta:
            meta["batch_id"] = f"d{fname_m.group(1)}_batch{fname_m.group(2)}"

    d = str(meta.get("direction", "0"))
    if "direction_name" not in meta:
        meta["direction_name"] = DIR_NAMES.get(d, f"方向{d}")
    if "total_items" not in meta:
        meta["total_items"] = "30"

    # Clean total_items
    ti_match = re.search(r"(\d+)", str(meta.get("total_items", "30")))
    meta["total_items"] = ti_match.group(1) if ti_match else "30"

    return meta


# ---------------------------------------------------------------------------
# key-value block parsing
# ---------------------------------------------------------------------------

def parse_kv_blocks(text: str) -> dict[str, list[dict]]:
    """Parse key-value block format into papers by tier."""
    papers = {"core": [], "important": [], "backup": []}
    current_tier = None

    # Split into lines
    lines = text.split("\n")
    current_paper = None

    for line in lines:
        stripped = line.strip()

        # Detect tier
        if re.match(r"^##\s.*(核心文献|Core)", stripped, re.IGNORECASE):
            current_tier = "core"
            continue
        elif re.match(r"^##\s.*(重要文献|Important)", stripped, re.IGNORECASE):
            current_tier = "important"
            continue
        elif re.match(r"^##\s.*(备选文献|Backup)", stripped, re.IGNORECASE):
            current_tier = "backup"
            continue
        elif re.match(r"^##\s.*(淘汰文献|淘汰摘要)", stripped, re.IGNORECASE):
            # Save last paper before entering rejection section
            if current_paper and current_tier:
                papers[current_tier].append(current_paper)
                current_paper = None
            current_tier = None
            continue

        if current_tier is None:
            continue

        # Detect new paper block: ### 入选N or ### N or ### Paper N
        if re.match(r"^###\s+", stripped):
            if current_paper:
                papers[current_tier].append(current_paper)
            current_paper = {}
            continue

        # Parse key-value lines: - key: value or key: value
        kv_match = re.match(r"^[-*]?\s*(作者|标题|年份|期刊|理由|author|title|year|journal|reason)\s*[:：]\s*(.+)$",
                           stripped, re.IGNORECASE)
        if kv_match and current_paper is not None:
            key = kv_match.group(1).strip().lower()
            value = kv_match.group(2).strip()

            # Normalize key names
            key_map = {
                "作者": "author", "author": "author",
                "标题": "title", "title": "title",
                "年份": "year", "year": "year",
                "期刊": "journal", "journal": "journal",
                "理由": "reason", "reason": "reason",
            }
            normalized_key = key_map.get(key, key)
            current_paper[normalized_key] = value
            continue

    # Save last paper
    if current_paper and current_tier:
        papers[current_tier].append(current_paper)

    return papers


# ---------------------------------------------------------------------------
# markdown table parsing (fallback for old format)
# ---------------------------------------------------------------------------

def extract_year(s: str) -> str:
    """Extract 4-digit year from string."""
    m = re.search(r"((?:19|20)\d{2})", s)
    return m.group(1) if m else ""


def parse_table_rows(text: str) -> dict[str, list[dict]]:
    """Parse markdown table format into papers by tier."""
    papers = {"core": [], "important": [], "backup": []}
    current_tier = None

    for line in text.split("\n"):
        stripped = line.strip()

        # Detect tier
        if re.match(r"^##\s.*(核心文献|Core)", stripped, re.IGNORECASE):
            current_tier = "core"
            continue
        elif re.match(r"^##\s.*(重要文献|Important)", stripped, re.IGNORECASE):
            current_tier = "important"
            continue
        elif re.match(r"^##\s.*(备选文献|Backup)", stripped, re.IGNORECASE):
            current_tier = "backup"
            continue
        elif re.match(r"^##\s.*(淘汰文献|淘汰摘要)", stripped, re.IGNORECASE):
            current_tier = None
            continue

        if current_tier is None:
            continue

        # Skip header/separator rows
        if not stripped.startswith("|"):
            continue
        if re.match(r"^\|[\s:|-]+\|$", stripped):
            continue

        cells = [c.strip() for c in stripped.split("|")]
        cells = [c for c in cells if c]  # remove empty

        if len(cells) < 3:
            continue

        # Skip header rows
        header_words = {"#", "第一作者", "标题", "年份", "期刊", "入选理由",
                       "作者", "citation", "key", "级别", "等级"}
        if any(c.lower().strip() in header_words for c in cells[:3]):
            continue

        # Try to extract year from any cell
        year = ""
        for c in cells:
            y = extract_year(c)
            if y:
                year = y
                break

        if not year:
            continue

        # Find title (longest English cell)
        title = ""
        title_idx = -1
        for i, c in enumerate(cells):
            clean = c.strip().strip("`")
            if len(clean) > 20 and re.search(r"[A-Za-z]{3,}", clean):
                chinese_ratio = len(re.findall(r"[\u4e00-\u9fff]", clean)) / max(len(clean), 1)
                if chinese_ratio < 0.3 and len(clean) > len(title):
                    title = clean
                    title_idx = i

        # Find author
        author = ""
        for i, c in enumerate(cells):
            if i == title_idx:
                continue
            clean = c.strip().strip("`")
            if re.match(r"^[A-Z][a-zà-ü]+", clean) and len(clean) < 80:
                if not re.search(r"(Journal|Review|Research|Science|Management|IEEE)", clean):
                    author = clean.split(",")[0].split("&")[0].split("et al")[0].strip()
                    break
            # Try "Author (Year)" format
            am = re.match(r"([A-Z][a-zà-ü]+(?:\s+(?:et\s+al|&\s+[A-Z][a-zà-ü]+))?)\s*[\(/]?\s*\d{4}", clean)
            if am:
                author = am.group(1).strip()
                break

        if not author:
            # Try extracting from citation key like "genin2021s"
            for c in cells:
                ck_match = re.match(r"^`?([a-z]+)\d{4}[a-z]?`?$", c.strip())
                if ck_match:
                    author = ck_match.group(1).capitalize()
                    break

        # Find journal
        journal = ""
        journal_kws = ["Journal", "Review", "Research", "Science", "Management",
                      "IEEE", "Policy", "Studies", "Networks", "Technovation",
                      "Organization", "Strategic", "ECAM", "JCEM", "JME"]
        for i, c in enumerate(cells):
            if i == title_idx:
                continue
            for kw in journal_kws:
                if kw.lower() in c.lower():
                    journal = re.sub(r"\s*/?\s*\d{4}\s*$", "", c).strip()
                    journal = re.sub(r"^\d{4}\s*/?\s*", "", journal).strip()
                    break
            if journal:
                break

        # Find reason (Chinese text)
        reason = ""
        for c in cells:
            if len(re.findall(r"[\u4e00-\u9fff]", c)) > 5:
                reason = c.strip()
                break
        if not reason:
            reason = cells[-1].strip() if cells else ""

        papers[current_tier].append({
            "author": author or "Unknown",
            "title": title,
            "year": year,
            "journal": journal or "Unknown",
            "reason": reason,
        })

    return papers


# ---------------------------------------------------------------------------
# unified parser
# ---------------------------------------------------------------------------

def parse_batch(text: str) -> dict[str, list[dict]]:
    """Parse batch file using key-value blocks first, fallback to table."""
    # Try key-value block format first
    kv_papers = parse_kv_blocks(text)
    kv_total = sum(len(v) for v in kv_papers.values())

    # Try table format
    table_papers = parse_table_rows(text)
    table_total = sum(len(v) for v in table_papers.values())

    # Use whichever found more papers
    if kv_total >= table_total:
        return kv_papers
    else:
        return table_papers


# ---------------------------------------------------------------------------
# output
# ---------------------------------------------------------------------------

def generate_standard_batch(meta: dict, papers: dict[str, list[dict]],
                           rejection_text: str) -> str:
    """Generate standard markdown batch file."""
    d = meta.get("direction", "0")
    fname_m = re.search(r"batch(\d+)", meta.get("batch_id", "batch1"))
    batch_num = fname_m.group(1) if fname_m else "1"
    total_items = meta.get("total_items", "30")

    total_selected = sum(len(v) for v in papers.values())
    total_rejected = max(0, int(total_items) - total_selected)

    lines = []
    lines.append(f"# 方向{d} Batch{batch_num} 筛选结果\n")
    lines.append(f"> direction: {d}")
    lines.append(f"> direction_name: {meta.get('direction_name', '')}")
    lines.append(f"> batch_id: {meta.get('batch_id', '')}")
    lines.append(f"> total_items: {total_items}\n")

    for tier_name, tier_key in [("核心文献（Core）", "core"),
                                 ("重要文献（Important）", "important"),
                                 ("备选文献（Backup）", "backup")]:
        lines.append(f"## {tier_name}\n")
        lines.append("| # | 第一作者 | 标题 | 年份 | 期刊 | 入选理由 |")
        lines.append("|:--|:---------|:-----|:----:|:-----|:---------|")
        for i, p in enumerate(papers[tier_key], 1):
            author = p.get("author", "Unknown").replace("|", "/")
            title = p.get("title", "").replace("|", "/")
            year = extract_year(str(p.get("year", ""))) or "0000"
            journal = p.get("journal", "Unknown").replace("|", "/")
            reason = p.get("reason", "").replace("|", "/").replace("\n", " ")
            lines.append(f"| {i} | {author} | {title} | {year} | {journal} | {reason} |")
        lines.append("")

    lines.append("## 淘汰文献摘要\n")
    if rejection_text:
        lines.append(f"淘汰{total_rejected}篇。\n{rejection_text}")
    else:
        lines.append(f"淘汰{total_rejected}篇。")

    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Normalize batch files to standard format")
    parser.add_argument("--batch-dir", required=True, help="Directory containing batch files")
    args = parser.parse_args()

    batch_dir = Path(args.batch_dir)

    # Find all raw files (new format) and non-raw files (old format)
    raw_files = sorted(batch_dir.glob("d*_batch*_raw.md"))
    old_files = sorted(f for f in batch_dir.glob("d*_batch*.md")
                       if "_raw" not in f.name and "_normalize" not in f.name)

    # Prefer raw files; fall back to old files
    input_files = raw_files if raw_files else old_files
    if not input_files:
        print("ERROR: No batch files found", file=sys.stderr)
        sys.exit(1)

    total_ok = 0
    total_fail = 0
    total_papers = 0
    errors = []

    for fp in input_files:
        try:
            text = fp.read_text(encoding="utf-8")
            stem = fp.stem.replace("_raw", "")
            meta = extract_metadata(text, stem)
            papers = parse_batch(text)

            # Extract rejection text
            rej_match = re.search(r"(?:##\s*淘汰.*?\n)(.*?)$", text, re.DOTALL)
            rejection_text = rej_match.group(1).strip() if rej_match else ""

            paper_count = sum(len(v) for v in papers.values())
            total_papers += paper_count

            # Validate
            file_errors = []
            for tier, tier_papers in papers.items():
                for i, p in enumerate(tier_papers):
                    if not p.get("title"):
                        file_errors.append(f"{tier}[{i}]: missing title")
                    year = extract_year(str(p.get("year", "")))
                    if not year:
                        file_errors.append(f"{tier}[{i}]: missing/invalid year")

            # Generate standard output
            output = generate_standard_batch(meta, papers, rejection_text)
            out_path = batch_dir / f"{stem}.md"
            out_path.write_text(output, encoding="utf-8")

            if file_errors:
                total_fail += 1
                errors.append(f"{stem}: {paper_count} papers, {len(file_errors)} errors: {file_errors[:3]}")
                print(f"  ⚠ {stem}: {paper_count} papers ({', '.join(file_errors[:2])})")
            else:
                total_ok += 1
                print(f"  ✓ {stem}: {paper_count} papers")

        except Exception as e:
            total_fail += 1
            errors.append(f"{fp.name}: {e}")
            print(f"  ✗ {fp.name}: {e}", file=sys.stderr)

    print(f"\nTotal: {len(input_files)} files, {total_papers} papers")
    print(f"OK: {total_ok}, Warnings: {total_fail}")

    if errors:
        print("\n=== VERIFY: FAIL ===")
        for e in errors:
            print(f"  ❌ {e}")
        # Don't exit 1 for warnings, only for fatal errors
        if total_ok == 0:
            sys.exit(1)
    else:
        print("\n=== VERIFY: PASS ===")


if __name__ == "__main__":
    main()
