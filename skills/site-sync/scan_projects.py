#!/usr/bin/env python3
"""Scan Zotero (published) + CLAUDE.md (ongoing) for site-sync."""

import os
import re
import json
import glob
import shutil
import sqlite3

PAPERS_DIR = "/Users/zylen/Library/CloudStorage/Dropbox/02-Research/papers"
GYM_DIR = "/Users/zylen/Library/CloudStorage/Dropbox/02-Research/_GYM group dropbox/_gym paper"
ZOTERO_DB = "/Users/zylen/Zotero/zotero.sqlite"
RESEARCH_COLLECTION_ID = 347  # 01-research


# === Zotero: Published papers ===

def scan_zotero_published():
    """Read published papers from Zotero 01-research direct items."""
    tmp_db = "/tmp/zotero_sitesync.sqlite"
    shutil.copy2(ZOTERO_DB, tmp_db)

    conn = sqlite3.connect(tmp_db)
    c = conn.cursor()

    # Get journalArticle items directly in 01-research, with DOI
    c.execute("""
        SELECT ci.itemID
        FROM collectionItems ci
        JOIN items i ON ci.itemID = i.itemID
        JOIN itemTypes it ON i.itemTypeID = it.itemTypeID
        WHERE ci.collectionID = ?
          AND it.typeName = 'journalArticle'
    """, (RESEARCH_COLLECTION_ID,))
    item_ids = [r[0] for r in c.fetchall()]

    papers = []
    for iid in item_ids:
        meta = {"_source": "zotero", "_category": "published"}

        # Get fields: title, publicationTitle (journal), date (year)
        c.execute("""
            SELECT f.fieldName, idv.value
            FROM itemData id
            JOIN fields f ON id.fieldID = f.fieldID
            JOIN itemDataValues idv ON id.valueID = idv.valueID
            WHERE id.itemID = ?
        """, (iid,))
        for fname, fval in c.fetchall():
            if fname == "title":
                meta["title"] = fval
            elif fname == "publicationTitle":
                meta["journal"] = fval
            elif fname == "DOI":
                meta["doi"] = fval
            elif fname == "date":
                m = re.match(r"(\d{4})", fval)
                if m:
                    meta["year"] = int(m.group(1))

        # Filter: must have DOI, must be English (no Chinese chars in title)
        title = meta.get("title", "")
        if not meta.get("doi"):
            continue
        if any("\u4e00" <= ch <= "\u9fff" for ch in title):
            continue

        # Determine role from first author
        c.execute("""
            SELECT c.lastName, c.firstName
            FROM itemCreators ic
            JOIN creators c ON ic.creatorID = c.creatorID
            WHERE ic.itemID = ? AND ic.orderIndex = 0
        """, (iid,))
        first_author = c.fetchone()
        if first_author:
            last, first = first_author
            name = f"{last} {first}".lower().strip()
            # 王子伦 → 一作, 何清华 → 除导师外一作, otherwise → 通讯
            if last.lower() == "wang" and "zilun" in (first or "").lower():
                meta["role"] = "一作"
            elif last.lower() == "he" and "qinghua" in (first or "").lower():
                meta["role"] = "除导师外一作"
            else:
                meta["role"] = "通讯"
        else:
            meta["role"] = "一作"

        if meta.get("title"):
            papers.append(meta)

    # Deduplicate by DOI
    seen_dois = set()
    unique_papers = []
    for p in papers:
        doi = p.get("doi", "")
        if doi and doi in seen_dois:
            continue
        seen_dois.add(doi)
        unique_papers.append(p)
    papers = unique_papers

    conn.close()
    os.remove(tmp_db)
    return papers


# === CLAUDE.md: Ongoing projects ===

def find_claude_md(project_dir):
    """Find CLAUDE.md in a project directory."""
    match = re.match(r"^((?:zy|dj|zz|xq)\d+)", os.path.basename(project_dir))
    if not match:
        return None
    pid = match.group(1)

    for candidate in [
        os.path.join(project_dir, f"{pid}_latexfile", "CLAUDE.md"),
        os.path.join(project_dir, "CLAUDE.md"),
    ]:
        if os.path.exists(candidate):
            return candidate

    matches = glob.glob(os.path.join(project_dir, "*/CLAUDE.md"))
    return matches[0] if matches else None


def parse_claude_md(filepath):
    """Parse metadata from CLAUDE.md."""
    with open(filepath, encoding="utf-8") as f:
        content = f.read()

    fields = {
        "id": r"\*\*项目编号\*\*[：:]\s*(.+)",
        "title": r"\*\*英文标题\*\*[：:]\s*(.+)",
        "method": r"\*\*方法\*\*[：:]\s*(.+)",
        "journal": r"\*\*目标期刊\*\*[：:]\s*(.+)",
        "status": r"\*\*状态\*\*[：:]\s*(\S+)",
    }

    meta = {}
    for key, pattern in fields.items():
        m = re.search(pattern, content)
        if m:
            val = m.group(1).strip()
            if key == "journal":
                val = re.sub(r"\s*\[首选\]", "", val)
                val = re.sub(r"\s*\[备选.*?\]", "", val)
                val = re.sub(r"\s*/\s*.*$", "", val)
                val = val.strip()
            meta[key] = val

    return meta


def scan_claude_md():
    """Scan CLAUDE.md files for ongoing (non-published) projects."""
    projects = []

    for base_dir in [PAPERS_DIR, GYM_DIR]:
        if not os.path.exists(base_dir):
            continue

        for entry in sorted(os.listdir(base_dir)):
            full = os.path.join(base_dir, entry)
            if not os.path.isdir(full) or entry == "_done":
                continue
            if not re.match(r"^(zy|dj|zz|xq)", entry):
                continue

            cm = find_claude_md(full)
            if cm:
                meta = parse_claude_md(cm)
                if not meta.get("id"):
                    continue
                meta["_source"] = "claude_md"
                status = meta.get("status", "")
                if status in ("submitted",) or status.startswith("revision"):
                    meta["_category"] = "under_review"
                else:
                    meta["_category"] = "in_progress"
                projects.append(meta)

    return projects


# === Main ===

def main():
    published = scan_zotero_published()
    ongoing = scan_claude_md()

    # Try to enrich published papers with method from CLAUDE.md
    # Match by title similarity (lowercase, stripped)
    claude_by_title = {}
    for p in ongoing:
        t = p.get("title", "").lower().strip()
        if t:
            claude_by_title[t] = p

    for p in published:
        t = p.get("title", "").lower().strip()
        match = claude_by_title.get(t)
        if match and match.get("method"):
            p["method"] = match["method"]

    result = {
        "published": published,
        "ongoing": ongoing,
        "stats": {
            "published": len(published),
            "under_review": len([p for p in ongoing if p["_category"] == "under_review"]),
            "in_progress": len([p for p in ongoing if p["_category"] == "in_progress"]),
        },
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
