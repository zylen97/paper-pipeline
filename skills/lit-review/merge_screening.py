#!/usr/bin/env python3
"""
merge_screening.py — 文献筛选合并脚本（步骤 2）

从 _batch/ 目录下的 markdown（或旧版 JSON）文件中读取各 subAgent 的筛选结果，
按方向合并、配额截断、跨方向去重，生成方向报告和汇总报告。

支持两种 batch 格式（优先 .md）：
  - .md：subAgent 输出的 markdown 表格（新格式）
  - .json：旧版 JSON 格式（向后兼容）

用法:
    python3 merge_screening.py \
        --batch-dir structure/2_literature/_batch/ \
        --plan-file structure/2_literature/literature_search_plan.md \
        --output-dir structure/2_literature/
"""

import argparse
import json
import os
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def normalize(s: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace."""
    s = s.lower().strip()
    s = unicodedata.normalize("NFKD", s)
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def dedup_key(paper: dict) -> str:
    """Cross-direction dedup key: first_author(lower) + year + title[:40](normalized)."""
    fa = paper.get("first_author", "").split(",")[0].split(";")[0].strip().lower()
    yr = str(paper.get("year", ""))
    ti = normalize(paper.get("title", ""))[:40]
    return f"{fa}|{yr}|{ti}"


TIER_ORDER = {"core": 0, "important": 1, "backup": 2}


def _is_cnki_paper(paper: dict) -> bool:
    """Detect CNKI origin by checking for CJK characters in title/author/journal."""
    for field in ("title", "first_author", "journal"):
        val = paper.get(field, "")
        if any('\u4e00' <= c <= '\u9fff' for c in val):
            return True
    return False


def _truncate_by_tier(papers: list[dict], quota: int) -> list[dict]:
    """Truncate a sorted paper list to quota with tier-level caps."""
    core_cap = max(1, int(quota * 0.25))
    imp_cap = max(1, int(quota * 0.40))
    bak_cap = max(1, int(quota * 0.35))

    result = []
    counts = {"core": 0, "important": 0, "backup": 0}
    caps = {"core": core_cap, "important": imp_cap, "backup": bak_cap}

    for p in papers:
        tier = p.get("tier", "backup")
        if counts[tier] < caps[tier] and len(result) < quota:
            result.append(p)
            counts[tier] += 1

    return result

# Direction name maps are built dynamically from batch JSON data.
# No hardcoded project-specific names.
DIR_FULLNAME_MAP: dict[int, str] = {}  # populated in main() from batch data


def dir_shortname(fullname: str) -> str:
    """Generate a filesystem-safe short name from direction full name.
    Takes first 6 non-space CJK/ASCII chars, replaces problematic chars."""
    import re as _re
    # Remove parentheses content and special chars
    short = _re.sub(r"[（(][^）)]*[）)]", "", fullname)
    short = _re.sub(r"[/\\:*?\"<>|]", "_", short)
    # Take first 10 chars (enough to be recognizable)
    short = short.strip()[:10].strip()
    if not short:
        short = "unknown"
    return short


# ---------------------------------------------------------------------------
# parse quotas from literature_search_plan.md
# ---------------------------------------------------------------------------

def parse_quotas(plan_path: str) -> dict[int, int]:
    """Extract per-direction quotas from the search plan summary table."""
    quotas = {}
    try:
        with open(plan_path, encoding="utf-8") as f:
            content = f.read()
        # Match rows like: | 1 | 方向名 | 标签 | P1 | 49篇 |
        for m in re.finditer(r"\|\s*D?(\d+)\s*\|[^|]+\|[^|]+\|[^|]+\|\s*(\d+)篇\s*\|", content):
            d = int(m.group(1))
            q = int(m.group(2))
            quotas[d] = q
    except Exception as e:
        print(f"WARNING: Could not parse quotas from {plan_path}: {e}", file=sys.stderr)
    return quotas


# ---------------------------------------------------------------------------
# parse markdown batch file
# ---------------------------------------------------------------------------

def parse_batch_md(filepath: Path) -> dict:
    """Parse a markdown batch file into the same dict structure as JSON batches.

    Expected format:
        > direction: N
        > direction_name: ...
        > batch_id: d{N}_batch{M}
        > total_items: X

        ## 核心文献（Core）
        | # | 第一作者 | 标题 | 年份 | 期刊 | 入选理由 |
        | 1 | Author  | Title | 2024 | J    | Reason   |

        ## 重要文献（Important）
        ...
    """
    text = filepath.read_text(encoding="utf-8")

    # 1. Extract blockquote metadata
    meta = {}
    for m in re.finditer(r"^>\s*(\w[\w_]*):\s*(.+)$", text, re.MULTILINE):
        meta[m.group(1).strip()] = m.group(2).strip()

    direction = int(meta.get("direction", 0))
    direction_name = meta.get("direction_name", "")
    batch_id = meta.get("batch_id", filepath.stem)
    total_items = int(meta.get("total_items", 0))

    # Fallback: bullet format (- key: value)
    if direction == 0:
        for m in re.finditer(r"^[-*]\s*(\w[\w_]*):\s*(.+)$", text, re.MULTILINE):
            key = m.group(1).strip()
            val = m.group(2).strip()
            if key not in meta:
                meta[key] = val
        direction = int(meta.get("direction", 0))
        direction_name = meta.get("direction_name", "")
        batch_id = meta.get("batch_id", filepath.stem)
        total_items = int(meta.get("total_items", 0))

    # Fallback: infer direction from filename if metadata missing
    if direction == 0:
        fname_m = re.match(r"d(\d+)_batch(\d+)", filepath.stem)
        if fname_m:
            direction = int(fname_m.group(1))

    # 2. Parse tables with tier state machine
    current_tier = None
    selected = []

    for line in text.split("\n"):
        # Detect tier headings
        if re.match(r"^##\s.*(核心文献|Core)", line, re.IGNORECASE):
            current_tier = "core"
            continue
        elif re.match(r"^##\s.*(重要文献|Important)", line, re.IGNORECASE):
            current_tier = "important"
            continue
        elif re.match(r"^##\s.*(备选文献|Backup)", line, re.IGNORECASE):
            current_tier = "backup"
            continue
        elif re.match(r"^##\s.*(淘汰文献|方向小结|逐篇处理)", line, re.IGNORECASE):
            current_tier = None
            continue

        if current_tier is None:
            continue

        # Match 6-column table row: | # | author | title | year | journal | reason |
        m = re.match(
            r"\|\s*(\d+)\s*\|"   # #
            r"\s*([^|]+)\|"       # author
            r"\s*([^|]+)\|"       # title
            r"\s*(\d{4})\s*\|"    # year
            r"\s*([^|]+)\|"       # journal
            r"\s*([^|]+)\|",      # reason
            line
        )
        if m:
            selected.append({
                "title": m.group(3).strip(),
                "first_author": m.group(2).strip(),
                "year": int(m.group(4)),
                "journal": m.group(5).strip(),
                "tier": current_tier,
                "reason": m.group(6).strip(),
            })

    rejected_count = max(0, total_items - len(selected))

    return {
        "direction": direction,
        "direction_name": direction_name,
        "batch_id": batch_id,
        "total_items": total_items,
        "selected": selected,
        "rejected_count": rejected_count,
        "_source_file": filepath.name,
    }


def parse_batch_json(filepath: Path) -> dict:
    """Parse a legacy JSON batch file with auto-repair for unescaped quotes."""
    text = filepath.read_text(encoding="utf-8")
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # Auto-repair: fix unescaped quotes inside string values
        lines = text.split("\n")
        new_lines = []
        for line in lines:
            match = re.match(
                r'(\s*"(?:reason|title|journal|first_author|direction_name)"\s*:\s*")(.*?)("\s*,?\s*)$',
                line,
            )
            if match:
                prefix, value, suffix = match.groups()
                value = value.replace('\\"', '<<<ESC>>>')
                value = value.replace('"', '\\"')
                value = value.replace('<<<ESC>>>', '\\"')
                line = prefix + value + suffix
            new_lines.append(line)
        text = "\n".join(new_lines)
        try:
            data = json.loads(text)
            print(f"WARNING: Auto-repaired JSON in {filepath.name}", file=sys.stderr)
        except json.JSONDecodeError as e:
            print(f"ERROR: Failed to parse {filepath.name} even after repair: {e}", file=sys.stderr)
            sys.exit(1)
    data["_source_file"] = filepath.name
    return data


# ---------------------------------------------------------------------------
# read batch files (.md preferred, .json as fallback)
# ---------------------------------------------------------------------------

def read_batches(batch_dir: str) -> list[dict]:
    """Read all d*_batch*.{md,json} files from batch_dir.
    Prefers .md over .json when both exist for the same batch."""
    batch_path = Path(batch_dir)
    if not batch_path.exists():
        print(f"ERROR: Batch directory not found: {batch_dir}", file=sys.stderr)
        sys.exit(1)

    md_files = {fp.stem: fp for fp in sorted(batch_path.glob("d*_batch*.md")) if "_raw" not in fp.stem}
    json_files = {fp.stem: fp for fp in sorted(batch_path.glob("d*_batch*.json"))}

    # Merge: .md takes priority
    all_stems = sorted(set(md_files.keys()) | set(json_files.keys()))

    batches = []
    for stem in all_stems:
        if stem in md_files:
            batches.append(parse_batch_md(md_files[stem]))
        else:
            batches.append(parse_batch_json(json_files[stem]))

    return batches


# ---------------------------------------------------------------------------
# merge within direction
# ---------------------------------------------------------------------------

def merge_direction(papers: list[dict], quota: int,
                    wos_quota: int | None = None,
                    cnki_quota: int | None = None) -> list[dict]:
    """Dedup within direction, sort by tier, truncate to quota.

    If wos_quota and cnki_quota are provided (dual-track mode),
    WoS and CNKI papers are truncated independently within their
    own pools, then concatenated.
    """
    # Dedup: keep higher-tier version on collision
    seen = {}
    for p in papers:
        key = dedup_key(p)
        if key not in seen or TIER_ORDER.get(p.get("tier", "backup"), 2) < TIER_ORDER.get(seen[key].get("tier", "backup"), 2):
            seen[key] = p
    unique = sorted(seen.values(),
                    key=lambda x: TIER_ORDER.get(x.get("tier", "backup"), 2))

    # Tag CNKI origin
    for p in unique:
        p["is_cnki"] = _is_cnki_paper(p)

    # Dual-track: truncate WoS and CNKI pools independently
    if wos_quota is not None and cnki_quota is not None and cnki_quota > 0:
        wos_papers = [p for p in unique if not p["is_cnki"]]
        cnki_papers = [p for p in unique if p["is_cnki"]]
        return _truncate_by_tier(wos_papers, wos_quota) + \
               _truncate_by_tier(cnki_papers, cnki_quota)

    # WoS-only mode (backward compatible)
    return _truncate_by_tier(unique, quota)


# ---------------------------------------------------------------------------
# cross-direction dedup
# ---------------------------------------------------------------------------

def cross_dedup(all_papers: dict[int, list[dict]]) -> tuple[dict[int, list[dict]], int]:
    """Identify papers appearing in multiple directions. Keep all but count duplicates."""
    global_seen = {}  # dedup_key -> set of directions
    for d, papers in all_papers.items():
        for p in papers:
            key = dedup_key(p)
            if key not in global_seen:
                global_seen[key] = set()
            global_seen[key].add(d)

    dup_count = sum(len(dirs) - 1 for dirs in global_seen.values() if len(dirs) > 1)
    unique_count = len(global_seen)
    return all_papers, dup_count, unique_count


# ---------------------------------------------------------------------------
# generate direction report markdown
# ---------------------------------------------------------------------------

def generate_direction_report(d: int, papers: list[dict], total_items: int) -> str:
    """Generate markdown report for one direction."""
    core = [p for p in papers if p.get("tier") == "core"]
    important = [p for p in papers if p.get("tier") == "important"]
    backup = [p for p in papers if p.get("tier") == "backup"]

    lines = []
    lines.append(f"# 方向{d}：{DIR_FULLNAME_MAP.get(d, '')} 文献筛选报告\n")
    lines.append(f"> **日期**: {__import__('datetime').date.today().isoformat()}")
    lines.append(f"> **检索平台**: Web of Science Core Collection")
    lines.append(f"> **检索结果**: {total_items}篇")
    lines.append(f"> **最终入选**: {len(papers)}篇（核心{len(core)}篇 + 重要{len(important)}篇 + 备选{len(backup)}篇）\n")

    for tier_name, tier_key, tier_papers in [
        ("核心文献（Core）", "core", core),
        ("重要文献（Important）", "important", important),
        ("备选文献（Backup）", "backup", backup),
    ]:
        lines.append(f"## {tier_name}\n")
        if not tier_papers:
            lines.append("（无）\n")
            continue
        lines.append("| # | 作者 | 标题 | 年份 | 期刊 | 入选理由 |")
        lines.append("|:--|:-----|:-----|:----:|:-----|:---------|")
        for i, p in enumerate(tier_papers, 1):
            author = p.get("first_author", "").replace("|", "/")
            title = p.get("title", "").replace("|", "/")
            year = p.get("year", "")
            journal = p.get("journal", "").replace("|", "/")
            reason = p.get("reason", "").replace("|", "/").replace("\n", " ")
            lines.append(f"| {i} | {author} | {title} | {year} | {journal} | {reason} |")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# generate screening summary report
# ---------------------------------------------------------------------------

def generate_summary(all_papers: dict[int, list[dict]], dup_count: int,
                     unique_count: int, total_items_map: dict[int, int]) -> str:
    lines = []
    lines.append("# 文献筛选汇总报告\n")
    lines.append(f"> **日期**: {__import__('datetime').date.today().isoformat()}")
    lines.append("> **检索平台**: Web of Science Core Collection")
    lines.append("> **筛选方式**: 多Agent并行筛选 + Python脚本合并去重\n")

    lines.append("## 各方向入选统计\n")
    lines.append("| 方向 | 名称 | 检索数 | 核心 | 重要 | 备选 | 入选合计 |")
    lines.append("|:----:|:-----|:------:|:----:|:----:|:----:|:--------:|")

    total_core = total_imp = total_bak = total_sel = 0
    for d in sorted(all_papers.keys()):
        papers = all_papers[d]
        c = sum(1 for p in papers if p.get("tier") == "core")
        i = sum(1 for p in papers if p.get("tier") == "important")
        b = sum(1 for p in papers if p.get("tier") == "backup")
        s = len(papers)
        ti = total_items_map.get(d, "?")
        lines.append(f"| D{d} | {DIR_FULLNAME_MAP.get(d, '')} | {ti} | {c} | {i} | {b} | {s} |")
        total_core += c
        total_imp += i
        total_bak += b
        total_sel += s
    lines.append(f"| **合计** | - | - | **{total_core}** | **{total_imp}** | **{total_bak}** | **{total_sel}** |\n")

    lines.append("## 去重统计\n")
    lines.append(f"- **各方向入选合计（含重复）**: {total_sel}篇")
    lines.append(f"- **跨方向重复文献**: {dup_count}篇")
    lines.append(f"- **去重后独立文献总数**: {unique_count}篇\n")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Merge screening batch files (markdown or JSON)")
    parser.add_argument("--batch-dir", required=True, help="Directory containing d*_batch*.json files")
    parser.add_argument("--plan-file", required=True, help="literature_search_plan.md path")
    parser.add_argument("--output-dir", required=True, help="Directory for output reports")
    parser.add_argument("--budget", type=int, default=0, help="Total budget (0 = no limit)")
    args = parser.parse_args()

    # 1. Parse quotas
    quotas = parse_quotas(args.plan_file)
    if not quotas:
        print("WARNING: No quotas parsed, using unlimited", file=sys.stderr)

    # 2. Read batch files
    batches = read_batches(args.batch_dir)
    if not batches:
        print("ERROR: No batch files found", file=sys.stderr)
        sys.exit(1)

    expected_count = len(batches)

    # 3. Group by direction and build name map dynamically
    global DIR_FULLNAME_MAP
    dir_papers: dict[int, list[dict]] = defaultdict(list)
    dir_total_items: dict[int, int] = defaultdict(int)
    for batch in batches:
        d = batch.get("direction", 0)
        dir_papers[d].extend(batch.get("selected", []))
        dir_total_items[d] += batch.get("total_items", 0)
        # Build fullname map from first batch that has this direction
        if d not in DIR_FULLNAME_MAP and batch.get("direction_name"):
            DIR_FULLNAME_MAP[d] = batch["direction_name"]

    # 4. Try to load dual-track quotas from _quota_result.json
    dual_quotas: dict[int, dict] = {}
    qr_path = os.path.join(os.path.dirname(args.plan_file), "_quota_result.json")
    if os.path.exists(qr_path):
        try:
            with open(qr_path, encoding="utf-8") as f:
                qr = json.load(f)
            if qr.get("dual_mode"):
                for d_entry in qr["directions"]:
                    dual_quotas[d_entry["id"]] = {
                        "wos_quota": d_entry["wos_quota"],
                        "cnki_quota": d_entry.get("cnki_quota", 0),
                    }
                print(f"INFO: Loaded dual-track quotas from {qr_path}", file=sys.stderr)
        except Exception as e:
            print(f"WARNING: Could not parse {qr_path}: {e}", file=sys.stderr)

    # 5. Merge within each direction
    merged_papers: dict[int, list[dict]] = {}
    for d in sorted(dir_papers.keys()):
        quota = quotas.get(d, 999)
        if d in dual_quotas:
            merged_papers[d] = merge_direction(
                dir_papers[d], quota,
                wos_quota=dual_quotas[d]["wos_quota"],
                cnki_quota=dual_quotas[d]["cnki_quota"])
        else:
            merged_papers[d] = merge_direction(dir_papers[d], quota)

    # 6. Cross-direction dedup (count only, keep all)
    merged_papers, dup_count, unique_count = cross_dedup(merged_papers)

    # 7. Budget check
    total_selected = sum(len(ps) for ps in merged_papers.values())
    budget = args.budget if args.budget > 0 else 99999
    budget_status = "PASS" if total_selected <= budget else "FAIL"

    # 8. Generate direction reports
    output_dir = Path(args.output_dir)
    for d, papers in merged_papers.items():
        fullname = DIR_FULLNAME_MAP.get(d, f"方向{d}")
        short = dir_shortname(fullname)
        report = generate_direction_report(d, papers, dir_total_items[d])
        report_path = output_dir / f"direction{d}_{short}_report.md"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)

    # 9. Generate summary report
    summary = generate_summary(merged_papers, dup_count, unique_count, dir_total_items)
    with open(output_dir / "screening_summary_report.md", "w", encoding="utf-8") as f:
        f.write(summary)

    # 10. Generate merged JSON
    merged_json = {
        "directions": {},
        "cross_direction_duplicates": dup_count,
        "unique_count": unique_count,
    }
    for d, papers in merged_papers.items():
        merged_json["directions"][str(d)] = papers
    with open(output_dir / "_screening_merged.json", "w", encoding="utf-8") as f:
        json.dump(merged_json, f, ensure_ascii=False, indent=2)

    # 11. Stdout summary for main agent validation
    print("=== MERGE SUMMARY ===")
    print(f"Batch files parsed: {expected_count}/{expected_count}")
    for d in sorted(merged_papers.keys()):
        ps = merged_papers[d]
        c = sum(1 for p in ps if p.get("tier") == "core")
        i = sum(1 for p in ps if p.get("tier") == "important")
        b = sum(1 for p in ps if p.get("tier") == "backup")
        print(f"D{d}: {len(ps)} selected (core={c}, important={i}, backup={b})")
    print(f"Cross-direction duplicates: {dup_count}")
    print(f"Final unique: {unique_count}")
    print(f"Budget: {total_selected}/{budget} → {budget_status}")
    print("=== END SUMMARY ===")

    if budget_status == "FAIL":
        sys.exit(2)


if __name__ == "__main__":
    main()
