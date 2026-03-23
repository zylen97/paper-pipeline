#!/usr/bin/env python3
"""
tex_section.py — LaTeX Section Tree 工具（共用）

供 pen-draft / pen-outline / pen-polish 三个 skill 共用。
替代主 Agent 的正则解析、模糊匹配、引用池路径提取、BibTeX 操作。

功能:
    1. section-tree   — 解析 .tex 构建 Section Tree JSON
    2. match-section  — 在 Section Tree 中模糊匹配
    3. citation-paths — 从章节 md 的 ## 引用池 提取路径
    4. update-bib     — 扫描 LaTeX cite 命令 → 从 master.bib 提取 → 追加到项目 bib

用法:
    # 1. 构建 Section Tree
    python3 tex_section.py section-tree --tex manuscript.tex

    # 2. 匹配 section
    python3 tex_section.py match-section --tree _section_tree.json --query "Literature Review"

    # 3. 提取引用池路径
    python3 tex_section.py citation-paths --chapter-md structure/2_literature/literature.md

    # 4. 更新 bib
    python3 tex_section.py update-bib \
        --draft-files drafts/Xxx/final.md \
        --master-bib structure/2_literature/citation_pool/master.bib \
        --project-bib zl14.bib
"""

import argparse
import json
import re
import sys
from pathlib import Path


# ===========================================================================
# 功能 1: Section Tree 构建
# ===========================================================================

def build_section_tree(tex_content: str) -> list[dict]:
    """从 .tex 内容解析 section/subsection/subsubsection 命令，构建树。

    返回 flat list，每个节点含：
    - id, level, title, line_no
    - parent_id, children_ids
    - preceding_id, following_id (同级)
    """
    LEVEL_MAP = {"section": 1, "subsection": 2, "subsubsection": 3}

    # 匹配 \section{...}, \subsection{...}, \subsubsection{...}
    # 忽略 \section*{...} 变体（带 *）
    pattern = re.compile(
        r"^[^%]*?"  # 忽略注释行
        r"\\(section|subsection|subsubsection)\*?\{([^}]+)\}",
        re.MULTILINE
    )

    nodes = []
    for i, m in enumerate(pattern.finditer(tex_content)):
        cmd = m.group(1)
        title = m.group(2).strip()
        # 计算行号
        line_no = tex_content[:m.start()].count("\n") + 1
        nodes.append({
            "id": i,
            "level": LEVEL_MAP[cmd],
            "cmd": cmd,
            "title": title,
            "line_no": line_no,
            "parent_id": None,
            "children_ids": [],
            "preceding_id": None,
            "following_id": None,
        })

    # 构建父子关系
    for i, node in enumerate(nodes):
        # 找 parent：向前找第一个 level 更小的
        for j in range(i - 1, -1, -1):
            if nodes[j]["level"] < node["level"]:
                node["parent_id"] = nodes[j]["id"]
                nodes[j]["children_ids"].append(node["id"])
                break

    # 构建同级 preceding/following
    for i, node in enumerate(nodes):
        # 找 preceding：向前找同 level 同 parent 的
        for j in range(i - 1, -1, -1):
            if nodes[j]["level"] == node["level"] and nodes[j]["parent_id"] == node["parent_id"]:
                node["preceding_id"] = nodes[j]["id"]
                nodes[j]["following_id"] = node["id"]
                break
            if nodes[j]["level"] < node["level"]:
                break  # 跨越了父级边界

    return nodes


def cmd_section_tree(args):
    """子命令: section-tree"""
    tex_path = Path(args.tex)
    if not tex_path.exists():
        print(f"ERROR: {tex_path} not found", file=sys.stderr)
        sys.exit(1)

    with open(tex_path, encoding="utf-8") as f:
        content = f.read()

    nodes = build_section_tree(content)

    # 输出 JSON
    output_path = args.output or str(tex_path.parent / "_section_tree.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(nodes, f, ensure_ascii=False, indent=2)

    # 校验
    errors = []
    if not nodes:
        errors.append("EMPTY_TREE: No section commands found")
    # 检查顶级 section 至少 1 个
    top_level = [n for n in nodes if n["level"] == 1]
    if not top_level:
        errors.append("NO_TOP_SECTIONS: No \\section{} found")
    # 回读校验
    try:
        with open(output_path, encoding="utf-8") as f:
            readback = json.load(f)
        if len(readback) != len(nodes):
            errors.append(f"READBACK_MISMATCH: wrote {len(nodes)}, read {len(readback)}")
    except Exception as e:
        errors.append(f"READBACK_ERROR: {e}")

    # stdout
    print("=== SECTION TREE ===")
    print(f"File: {tex_path}")
    print(f"Nodes: {len(nodes)}")
    for n in nodes:
        indent = "  " * (n["level"] - 1)
        children = f" ({len(n['children_ids'])} children)" if n["children_ids"] else ""
        print(f"  {indent}L{n['line_no']:>4d} [{n['cmd']}] {n['title']}{children}")
    print()

    if errors:
        print("=== VERIFY: FAIL ===")
        for e in errors:
            print(f"  ❌ {e}")
        sys.exit(1)
    else:
        print("=== VERIFY: PASS ===")
        print(f"Output: {output_path}")


# ===========================================================================
# 功能 2: Section 模糊匹配
# ===========================================================================

# 英文冠词和常见省略词
ARTICLES = {"a", "an", "the"}


def normalize_for_match(title: str) -> str:
    """归一化标题用于模糊匹配。"""
    s = title.lower().strip()
    # & ↔ and
    s = s.replace("&", "and")
    # 去掉编号前缀 (如 "2.1 " or "2.1. ")
    s = re.sub(r"^\d+(\.\d+)*\.?\s*", "", s)
    # 去掉冠词
    words = s.split()
    words = [w for w in words if w not in ARTICLES]
    s = " ".join(words)
    # 去掉标点
    s = re.sub(r"[^\w\s]", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def match_section(query: str, nodes: list[dict]) -> dict | None:
    """在 Section Tree 中匹配 section。

    匹配策略（按优先级）：
    1. 精确匹配（大小写不敏感）
    2. 归一化后精确匹配（去冠词、& ↔ and）
    3. 归一化后包含匹配（query 是标题的子串，或反过来）
    """
    query_lower = query.lower().strip()
    query_norm = normalize_for_match(query)

    # 1. 精确匹配
    for n in nodes:
        if n["title"].lower().strip() == query_lower:
            return n

    # 2. 归一化精确匹配
    for n in nodes:
        if normalize_for_match(n["title"]) == query_norm:
            return n

    # 3. 包含匹配（双向）
    if len(query_norm) >= 3:
        for n in nodes:
            n_norm = normalize_for_match(n["title"])
            if query_norm in n_norm or n_norm in query_norm:
                return n

    return None


def get_ancestors(node: dict, nodes: list[dict]) -> list[dict]:
    """获取祖先节点列表（从顶到当前）。"""
    ancestors = []
    current = node
    while current["parent_id"] is not None:
        parent = nodes[current["parent_id"]]
        ancestors.insert(0, parent)
        current = parent
    return ancestors


def get_top_parent(node: dict, nodes: list[dict]) -> dict:
    """获取顶层父 section。"""
    current = node
    while current["parent_id"] is not None:
        current = nodes[current["parent_id"]]
    return current


def cmd_match_section(args):
    """子命令: match-section"""
    tree_path = Path(args.tree)
    if not tree_path.exists():
        print(f"ERROR: {tree_path} not found", file=sys.stderr)
        sys.exit(1)

    with open(tree_path, encoding="utf-8") as f:
        nodes = json.load(f)

    query = args.query
    matched = match_section(query, nodes)

    # 构建结果
    result = {"query": query, "matched": False}

    if matched:
        result["matched"] = True
        result["node"] = matched

        # 父子关系
        top = get_top_parent(matched, nodes)
        result["top_parent"] = {"id": top["id"], "title": top["title"]}

        ancestors = get_ancestors(matched, nodes)
        result["ancestors"] = [{"id": a["id"], "title": a["title"]} for a in ancestors]

        # 子节点
        children = [nodes[cid] for cid in matched["children_ids"]]
        result["children"] = [{"id": c["id"], "title": c["title"]} for c in children]
        result["has_children"] = len(children) > 0

        # 同级
        siblings = [n for n in nodes
                    if n["parent_id"] == matched["parent_id"]
                    and n["level"] == matched["level"]
                    and n["id"] != matched["id"]]
        result["siblings"] = [{"id": s["id"], "title": s["title"]} for s in siblings]

        # preceding / following
        if matched["preceding_id"] is not None:
            result["preceding"] = nodes[matched["preceding_id"]]["title"]
        if matched["following_id"] is not None:
            result["following"] = nodes[matched["following_id"]]["title"]
    else:
        # 列出所有可用 section
        result["available"] = [
            {"id": n["id"], "level": n["level"], "title": n["title"]}
            for n in nodes
        ]

    # 输出
    output_path = args.output or str(tree_path.parent / "_section_match.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    # stdout
    print("=== SECTION MATCH ===")
    print(f"Query: \"{query}\"")
    if matched:
        path = " → ".join(a["title"] for a in ancestors) + (" → " if ancestors else "") + matched["title"]
        print(f"Matched: {matched['title']} (L{matched['line_no']}, {matched['cmd']})")
        print(f"Path: {path}")
        print(f"Top parent: {top['title']}")
        print(f"Children: {len(children)}")
        if children:
            for c in children:
                print(f"  - {c['title']}")
        print()
        print("=== VERIFY: PASS ===")
    else:
        print("NOT FOUND")
        print(f"Available sections ({len(nodes)}):")
        for n in nodes:
            indent = "  " * (n["level"] - 1)
            print(f"  {indent}{n['title']}")
        print()
        print("=== VERIFY: FAIL ===")
        print(f"  ❌ MATCH_FAILED: \"{query}\" not found in section tree")
        sys.exit(1)

    print(f"Output: {output_path}")


# ===========================================================================
# 功能 3: 引用池路径解析
# ===========================================================================

def extract_citation_paths(md_content: str) -> list[str]:
    """从章节 md 的 ## 引用池 区块提取路径列表。"""
    paths = []

    # 查找 ## 引用池 区块
    pool_match = re.search(r"^## 引用池\s*$", md_content, re.MULTILINE)
    if not pool_match:
        return paths

    # 从 ## 引用池 到下一个 ## 或文件末尾
    rest = md_content[pool_match.end():]
    next_section = re.search(r"^## ", rest, re.MULTILINE)
    block = rest[:next_section.start()] if next_section else rest

    # 提取路径（格式：`path/to/file.md` 或 path/to/file.md）
    for m in re.finditer(r"`([^`]+\.(?:md|bib))`", block):
        paths.append(m.group(1))

    return paths


def cmd_citation_paths(args):
    """子命令: citation-paths"""
    md_path = Path(args.chapter_md)
    if not md_path.exists():
        print(f"ERROR: {md_path} not found", file=sys.stderr)
        sys.exit(1)

    with open(md_path, encoding="utf-8") as f:
        content = f.read()

    paths = extract_citation_paths(content)

    result = {
        "chapter_md": str(md_path),
        "citation_pool_paths": paths,
        "count": len(paths),
    }

    output_path = args.output or str(md_path.parent / "_citation_paths.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    # stdout
    print("=== CITATION PATHS ===")
    print(f"Source: {md_path}")
    print(f"Paths found: {len(paths)}")
    for p in paths:
        print(f"  {p}")
    print()

    if not paths:
        print("=== VERIFY: PASS ===")
        print("(No citation pool block found — this is OK for some sections)")
    else:
        print("=== VERIFY: PASS ===")
    print(f"Output: {output_path}")


# ===========================================================================
# 功能 4: BibTeX 条目提取（update-bib）
# ===========================================================================

def extract_cite_keys(text: str) -> set[str]:
    r"""从 LaTeX 文本中提取所有 \citep{} 和 \citet{} 的 key。"""
    keys = set()
    for m in re.finditer(r"\\cite[pt]?\{([^}]+)\}", text):
        raw = m.group(1)
        for key in raw.split(","):
            key = key.strip()
            if key:
                keys.add(key)
    return keys


def parse_bib_entries(bib_content: str) -> dict[str, str]:
    """解析 BibTeX 文件，返回 {key: 完整条目文本}。"""
    entries = {}
    # 匹配 @type{key, ... }
    # 使用括号计数来正确找到结束位置
    for m in re.finditer(r"@\w+\{(\w+)\s*,", bib_content):
        key = m.group(1)
        start = m.start()
        # 从 @ 开始，用括号计数找到匹配的 }
        depth = 0
        end = start
        for i in range(start, len(bib_content)):
            if bib_content[i] == '{':
                depth += 1
            elif bib_content[i] == '}':
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        entries[key] = bib_content[start:end]
    return entries


def cmd_update_bib(args):
    """子命令: update-bib"""
    # 1. 读取 draft 文件，提取 cite keys
    all_keys = set()
    draft_files = args.draft_files
    for fp in draft_files:
        p = Path(fp)
        if not p.exists():
            print(f"WARNING: {fp} not found, skipping", file=sys.stderr)
            continue
        with open(p, encoding="utf-8") as f:
            text = f.read()
        keys = extract_cite_keys(text)
        all_keys.update(keys)

    if not all_keys:
        print("=== UPDATE BIB ===")
        print("No citation keys found in draft files.")
        print("=== VERIFY: PASS ===")
        return

    # 2. 读取 master.bib
    master_path = Path(args.master_bib)
    if not master_path.exists():
        print(f"ERROR: {master_path} not found", file=sys.stderr)
        sys.exit(1)
    with open(master_path, encoding="utf-8") as f:
        master_content = f.read()
    master_entries = parse_bib_entries(master_content)

    # 3. 读取项目 bib
    project_path = Path(args.project_bib)
    if project_path.exists():
        with open(project_path, encoding="utf-8") as f:
            project_content = f.read()
        project_entries = parse_bib_entries(project_content)
    else:
        project_content = ""
        project_entries = {}

    # 4. 找出新增 key
    new_keys = all_keys - set(project_entries.keys())
    found_keys = []
    not_found_keys = []
    new_entries = []

    for key in sorted(new_keys):
        if key in master_entries:
            found_keys.append(key)
            new_entries.append(master_entries[key])
        else:
            not_found_keys.append(key)

    # 5. 追加到项目 bib
    if new_entries and not args.dry_run:
        with open(project_path, "a", encoding="utf-8") as f:
            f.write("\n\n" + "\n\n".join(new_entries) + "\n")

    # 6. 年份一致性检查
    year_mismatches = []
    for key in all_keys:
        # 从 key 提取年份（格式: auth2023x）
        key_year_match = re.search(r"(\d{4})", key)
        if not key_year_match:
            continue
        key_year = key_year_match.group(1)

        # 从 bib 条目提取 year 字段
        entry = master_entries.get(key) or project_entries.get(key)
        if not entry:
            continue
        bib_year_match = re.search(r"year\s*=\s*\{(\d{4})\}", entry)
        if bib_year_match and bib_year_match.group(1) != key_year:
            year_mismatches.append(f"{key}: key says {key_year}, bib says {bib_year_match.group(1)}")

    # 校验
    errors = []
    if not args.dry_run and new_entries:
        # 回读验证
        with open(project_path, encoding="utf-8") as f:
            readback = f.read()
        readback_entries = parse_bib_entries(readback)
        for key in found_keys:
            if key not in readback_entries:
                errors.append(f"READBACK_MISSING: {key} not found after append")

    if year_mismatches:
        for ym in year_mismatches:
            errors.append(f"YEAR_MISMATCH: {ym}")

    # stdout
    mode = "PREVIEW" if args.dry_run else "UPDATE"
    print(f"=== UPDATE BIB ({mode}) ===")
    print(f"Draft files: {len(draft_files)}")
    print(f"Citation keys found: {len(all_keys)}")
    print(f"Already in project bib: {len(all_keys) - len(new_keys)}")
    print(f"New keys to add: {len(new_keys)}")
    print(f"  Found in master.bib: {len(found_keys)}")
    print(f"  NOT in master.bib: {len(not_found_keys)}")
    if not_found_keys:
        print("  Missing keys:")
        for k in not_found_keys:
            print(f"    ❓ {k}")
    if year_mismatches:
        print("  Year mismatches:")
        for ym in year_mismatches:
            print(f"    ⚠️ {ym}")
    print()

    if errors:
        print("=== VERIFY: FAIL ===")
        for e in errors:
            print(f"  ❌ {e}")
        sys.exit(1)
    else:
        print("=== VERIFY: PASS ===")
        if not args.dry_run and found_keys:
            print(f"Appended {len(found_keys)} entries to {project_path}")


# ===========================================================================
# main
# ===========================================================================

def main():
    parser = argparse.ArgumentParser(description="LaTeX Section Tree tools")
    sub = parser.add_subparsers(dest="command", required=True)

    # section-tree
    p1 = sub.add_parser("section-tree", help="Build section tree from .tex file")
    p1.add_argument("--tex", required=True, help="Path to .tex file")
    p1.add_argument("--output", default=None, help="Output JSON path")

    # match-section
    p2 = sub.add_parser("match-section", help="Match a section name in the tree")
    p2.add_argument("--tree", required=True, help="Path to _section_tree.json")
    p2.add_argument("--query", required=True, help="Section name to match")
    p2.add_argument("--output", default=None, help="Output JSON path")

    # citation-paths
    p3 = sub.add_parser("citation-paths", help="Extract citation pool paths from chapter md")
    p3.add_argument("--chapter-md", required=True, help="Path to chapter md file")
    p3.add_argument("--output", default=None, help="Output JSON path")

    # update-bib
    p4 = sub.add_parser("update-bib", help="Extract cite keys and update project bib")
    p4.add_argument("--draft-files", nargs="+", required=True, help="Draft file(s) to scan")
    p4.add_argument("--master-bib", required=True, help="Path to master.bib")
    p4.add_argument("--project-bib", required=True, help="Path to project bib file")
    p4.add_argument("--dry-run", action="store_true", help="Preview only")

    args = parser.parse_args()

    if args.command == "section-tree":
        cmd_section_tree(args)
    elif args.command == "match-section":
        cmd_match_section(args)
    elif args.command == "citation-paths":
        cmd_citation_paths(args)
    elif args.command == "update-bib":
        cmd_update_bib(args)


if __name__ == "__main__":
    main()
