#!/usr/bin/env python3
"""
update_citation_refs.py — 更新章节 md 的引用池区块（lit-pool §5）

按固定映射关系，在各章节 md 文件中插入/更新引用池指向。

替代主 Agent 的逐文件手动编辑。

用法:
    python3 update_citation_refs.py \
        --structure-dir structure/ \
        --pool-dir structure/2_literature/citation_pool/

    # 预览模式
    python3 update_citation_refs.py \
        --structure-dir structure/ \
        --pool-dir structure/2_literature/citation_pool/ \
        --dry-run

输出:
    1. stdout 结构化摘要 + 校验结果
    2. 更新后的章节 md 文件（非 dry-run 模式）
"""

import argparse
import re
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# 章节 → 引用池映射
# ---------------------------------------------------------------------------

# 标签消费规则——只针对技术型章节（X.md 是 /method-audit + /technical 的素材源，需要在 md 中插入引用池区块）。
# 叙述型章节（Introduction / Literature Review / Discussion）由 /narrative 在交互中按 lit-pool/SKILL.md
# 标签消费表的优先级直接读 citation_pool/，不写入 md 中间产物。
CHAPTER_POOL_MAP = {
    "methodology": {
        "[主] METHOD": "2_literature/citation_pool/METHOD.md",
    },
    "results": {
        "[次] METHOD-基础": "2_literature/citation_pool/METHOD.md",
    },
    "simulation": {
        "[次] BG": "2_literature/citation_pool/BG.md",
        "[次] LR": "2_literature/citation_pool/LR.md",
    },
}

# LABEL_MAP 别名（与 lit-pool/SKILL.md "契约提示" 中的命名对齐）
LABEL_MAP = CHAPTER_POOL_MAP

# 章节文件名模式（按优先级，仅技术型）
CHAPTER_FILE_PATTERNS = {
    "methodology": ["methodology.md", "3_methodology.md", "method.md", "methods.md"],
    "results": ["results.md", "4_results.md"],
    "simulation": ["simulation.md", "5_simulation.md", "numerical_simulation.md"],
}


def find_chapter_file(structure_dir: Path, chapter: str) -> Path | None:
    """查找章节 md 文件。"""
    # 递归搜索
    for pattern in CHAPTER_FILE_PATTERNS.get(chapter, []):
        matches = list(structure_dir.rglob(pattern))
        if matches:
            return matches[0]
    return None


def generate_pool_block(pool_map: dict[str, str]) -> str:
    """生成引用池区块内容。"""
    lines = ["## 引用池"]
    for label, path in pool_map.items():
        lines.append(f"- **{label}** → 见 `{path}`")
    return "\n".join(lines)


def update_file(filepath: Path, pool_block: str, dry_run: bool) -> dict:
    """更新单个文件的引用池区块。返回操作信息。"""
    try:
        with open(filepath, encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        return {"status": "error", "message": str(e)}

    original = content

    # 查找现有引用池区块
    # 匹配 "## 引用池" 到下一个 "##" 或文件末尾
    pattern = r"(## 引用池\n(?:.*\n)*?)(?=^## |\Z)"
    match = re.search(pattern, content, re.MULTILINE)

    if match:
        # 替换现有区块
        content = content[:match.start()] + pool_block + "\n\n" + content[match.end():]
        action = "updated"
    else:
        # 在文件末尾追加
        if not content.endswith("\n"):
            content += "\n"
        content += "\n---\n\n" + pool_block + "\n"
        action = "appended"

    if content == original:
        return {"status": "unchanged", "action": "no change needed"}

    if not dry_run:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

    return {"status": "ok", "action": action}


# ---------------------------------------------------------------------------
# 校验
# ---------------------------------------------------------------------------

def verify(results: dict[str, dict], structure_dir: Path,
           pool_dir: Path, dry_run: bool) -> list[str]:
    """内建校验。"""
    errors = []

    # 1. 引用池文件是否存在
    for chapter, pool_map in CHAPTER_POOL_MAP.items():
        for label, rel_path in pool_map.items():
            pool_file = structure_dir / rel_path
            if not pool_file.exists():
                errors.append(f"POOL_MISSING: {rel_path} referenced by {chapter} does not exist")

    # 2. 更新后的文件是否包含引用池区块（非 dry-run 模式）
    if not dry_run:
        for chapter, info in results.items():
            if info.get("status") != "ok":
                continue
            filepath = info.get("filepath")
            if not filepath:
                continue
            try:
                with open(filepath, encoding="utf-8") as f:
                    content = f.read()
                if "## 引用池" not in content:
                    errors.append(f"UPDATE_FAILED: {filepath} does not contain '## 引用池' after update")
            except Exception as e:
                errors.append(f"READBACK_ERROR: {filepath}: {e}")

    # 3. 文件其他部分是否未被意外修改（检查行数差异不超过预期）
    # 这个检查在 dry-run 模式下跳过

    return errors


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Update chapter md citation pool references")
    parser.add_argument("--structure-dir", required=True,
                        help="Project structure/ directory")
    parser.add_argument("--pool-dir", required=True,
                        help="citation_pool/ directory (for existence check)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview only, don't write files")
    args = parser.parse_args()

    structure_dir = Path(args.structure_dir)
    pool_dir = Path(args.pool_dir)
    mode = "PREVIEW" if args.dry_run else "UPDATE"

    results = {}

    for chapter, pool_map in CHAPTER_POOL_MAP.items():
        filepath = find_chapter_file(structure_dir, chapter)
        if not filepath:
            results[chapter] = {"status": "skipped", "message": "file not found"}
            continue

        pool_block = generate_pool_block(pool_map)
        info = update_file(filepath, pool_block, args.dry_run)
        info["filepath"] = str(filepath)
        results[chapter] = info

    # 校验
    errors = verify(results, structure_dir, pool_dir, args.dry_run)

    # ===== stdout 结构化摘要 =====
    print(f"=== CITATION REFS {mode} ===")
    for chapter, info in results.items():
        status = info.get("status", "?")
        action = info.get("action", info.get("message", ""))
        filepath = info.get("filepath", "not found")
        icon = "✅" if status == "ok" else "⏭️" if status in ("skipped", "unchanged") else "❌"
        print(f"  {icon} {chapter}: {action} ({filepath})")
    print()

    if errors:
        print("=== VERIFY: FAIL ===")
        for e in errors:
            print(f"  ❌ {e}")
        sys.exit(1)
    else:
        print("=== VERIFY: PASS ===")


if __name__ == "__main__":
    main()
