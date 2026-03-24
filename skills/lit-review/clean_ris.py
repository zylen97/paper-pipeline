#!/usr/bin/env python3
"""
clean_ris.py — RIS 文件清理脚本（步骤 5）

根据 _screening_merged.json 中的入选文献列表，
从各方向 RIS 文件中过滤掉淘汰条目，仅保留入选文献。

用法:
    # Dry-run（仅预览，不写文件）
    python3 clean_ris.py \
        --merged-json structure/2_literature/_screening_merged.json \
        --ris-dir structure/2_literature/ \
        --dry-run

    # 正式执行
    python3 clean_ris.py \
        --merged-json structure/2_literature/_screening_merged.json \
        --ris-dir structure/2_literature/
"""

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path


def normalize(s: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace."""
    s = s.lower().strip()
    s = unicodedata.normalize("NFKD", s)
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def parse_ris_entries(content: str) -> list[dict]:
    """Split RIS content into entries, each with raw text and parsed TI/AU/PY fields."""
    entries = re.split(r"(?=^TY  - )", content, flags=re.MULTILINE)
    entries = [e for e in entries if e.strip().startswith("TY  -")]

    parsed = []
    for raw in entries:
        ti_match = re.search(r"^TI  - (.+?)$", raw, re.MULTILINE)
        au_matches = re.findall(r"^AU  - (.+?)$", raw, re.MULTILINE)
        py_match = re.search(r"^PY  - (\d{4})", raw, re.MULTILINE)

        title = ti_match.group(1).strip() if ti_match else ""
        first_author = au_matches[0].strip().split(",")[0].strip() if au_matches else ""
        year = py_match.group(1) if py_match else ""

        parsed.append({
            "raw": raw,
            "title": title,
            "title_norm": normalize(title),
            "first_author": first_author.lower(),
            "year": year,
        })
    return parsed


def match_paper(entry: dict, selected_papers: list[dict]) -> bool:
    """Try to match a RIS entry against selected papers for THIS direction only.

    Strategy 1: Full normalized title match (strict)
    Strategy 2: Normalized title prefix match (first 60 chars) + same year
    Strategy 3: first_author + year + title overlap (≥20 chars)
    """
    ti_norm = entry["title_norm"]
    entry_au = entry["first_author"]
    entry_yr = entry["year"]

    for sel in selected_papers:
        sel_ti = sel["title_norm"]
        sel_au = sel["first_author"]
        sel_yr = sel["year"]

        # Strategy 1: full normalized title match
        if ti_norm and sel_ti and ti_norm == sel_ti:
            return True

        # Strategy 2: title prefix (60 chars) + same year
        if (ti_norm and sel_ti and entry_yr and sel_yr
                and entry_yr == sel_yr
                and len(ti_norm) >= 30 and len(sel_ti) >= 30
                and ti_norm[:60] == sel_ti[:60]):
            return True

        # Strategy 3: author + year + title overlap
        if (entry_au and sel_au and entry_yr and sel_yr
                and entry_au == sel_au and entry_yr == sel_yr):
            # Require at least 20 chars of title prefix match to avoid
            # matching different papers by the same author in the same year
            if len(ti_norm) >= 20 and len(sel_ti) >= 20 and ti_norm[:20] == sel_ti[:20]:
                return True

    return False


def find_ris_file(ris_dir: Path, direction: int) -> Path | None:
    """Find the RIS file for a given direction number."""
    for fp in ris_dir.glob("*.ris"):
        if fp.name.startswith(f"{direction}-") or fp.name.startswith(f"{direction}_"):
            return fp
    return None


def main():
    parser = argparse.ArgumentParser(description="Clean RIS files based on screening results")
    parser.add_argument("--merged-json", required=True, help="Path to _screening_merged.json")
    parser.add_argument("--ris-dir", required=True, help="Directory containing RIS files")
    parser.add_argument("--dry-run", action="store_true", help="Preview only, don't write files")
    args = parser.parse_args()

    # 1. Load merged JSON
    try:
        with open(args.merged_json, encoding="utf-8") as f:
            merged = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"ERROR: Cannot read {args.merged_json}: {e}", file=sys.stderr)
        sys.exit(1)

    ris_dir = Path(args.ris_dir)
    mode_label = "PREVIEW" if args.dry_run else "CLEAN"

    total_before = 0
    total_after = 0
    total_unmatched = 0
    unmatched_details = []

    print(f"=== CLEAN {mode_label} ===")

    directions = merged.get("directions", {})

    # Pre-process: build per-direction selected paper list with normalized fields
    dir_selected: dict[int, list[dict]] = {}
    for d_str, papers in directions.items():
        d = int(d_str)
        processed = []
        for p in papers:
            fa = p.get("first_author", "").split(",")[0].split(";")[0].strip().lower()
            yr = str(p.get("year", ""))
            processed.append({
                "title": p.get("title", ""),
                "title_norm": normalize(p.get("title", "")),
                "first_author": fa,
                "year": yr,
            })
        dir_selected[d] = processed

    for d in sorted(dir_selected.keys()):
        papers = dir_selected[d]

        # Find RIS file
        ris_file = find_ris_file(ris_dir, d)
        if not ris_file:
            print(f"D{d}: RIS file not found, skipping")
            continue

        # Parse RIS entries
        with open(ris_file, encoding="utf-8-sig") as f:
            content = f.read()
        entries = parse_ris_entries(content)
        before = len(entries)
        total_before += before

        # Match entries — only against THIS direction's selected papers
        kept = []
        for entry in entries:
            if match_paper(entry, papers):
                kept.append(entry)

        after = len(kept)
        total_after += after
        expected = len(papers)
        unmatched = expected - after
        if unmatched > 0:
            total_unmatched += unmatched
            # Find which selected papers didn't match
            for p in papers:
                found = False
                for e in kept:
                    if e["title_norm"] == p["title_norm"]:
                        found = True
                        break
                    if (e["title_norm"][:60] == p["title_norm"][:60]
                            and e["year"] == p["year"]):
                        found = True
                        break
                if not found:
                    unmatched_details.append(
                        f"  D{d}: {p['first_author']} ({p['year']}) - {p['title'][:60]}"
                    )

        print(f"D{d}: {before} → {after} (matched {after}/{expected}, unmatched {max(0, unmatched)})")

        # Write if not dry-run
        if not args.dry_run:
            if after == 0:
                print(f"  ⚠️ D{d}: 0 entries matched, NOT overwriting (safety check)")
            else:
                with open(ris_file, "w", encoding="utf-8") as f:
                    f.write("\n".join(e["raw"] for e in kept))

    print(f"Total: {total_before} → {total_after}")
    print(f"Unmatched: {total_unmatched}")
    if unmatched_details:
        print("Unmatched papers:")
        for detail in unmatched_details:
            print(detail)
    print(f"=== END {mode_label} ===")

    if total_unmatched > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
