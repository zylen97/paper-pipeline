#!/usr/bin/env python3
"""
source_bib_to_pool.py — 源项目文献导入（lit-pool §0.5）

读取源项目的 bib 文件 + manuscript.tex，解析每篇文献在哪个 section 被引用，
映射到功能标签，生成 _source_pool.json 供 pool_prepare.py 合并。

仅用于学位论文项目（有源项目的情况）。纯英文论文项目不调用此脚本。

用法:
    python3 source_bib_to_pool.py \
        --source-bib /path/to/dj01.bib \
        --source-tex /path/to/manuscript.tex \
        --output structure/2_literature/_source_pool.json \
        [--rq-count 2]

输出:
    1. stdout 结构化摘要 + VERIFY: PASS|FAIL
    2. _source_pool.json（含：文献清单、标签、引用上下文、key映射）
"""

import argparse
import json
import re
import sys
from pathlib import Path

# 导入 pool_prepare.py 的 citation key 生成函数
sys.path.insert(0, str(Path(__file__).parent))
from pool_prepare import (
    generate_citation_key, resolve_key_conflicts, _has_cjk,
    normalize_text, dedup_key,
)


# ---------------------------------------------------------------------------
# BibTeX 解析（轻量级，仅处理 Zotero 输出格式）
# ---------------------------------------------------------------------------

def parse_bibtex(content: str) -> dict[str, dict]:
    """解析 BibTeX 文件，返回 {cite_key: {type, fields, raw}}。

    处理嵌套花括号、多行字段值。不依赖外部库。
    """
    entries = {}
    # 找到所有 @type{key, 开头的位置
    for m in re.finditer(r'@(\w+)\s*\{([^,\s]+)\s*,', content):
        entry_type = m.group(1).lower()
        cite_key = m.group(2).strip()
        start = m.start()

        # 找到匹配的闭合花括号
        depth = 0
        end = start
        for i in range(m.start(), len(content)):
            if content[i] == '{':
                depth += 1
            elif content[i] == '}':
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break

        raw = content[start:end]
        body = raw[m.end() - start:].rstrip('}').strip()

        # 解析字段
        fields = {}
        # 匹配 field = {value} 或 field = "value" 或 field = number
        field_pattern = re.compile(
            r'(\w+)\s*=\s*'
            r'(?:'
            r'\{((?:[^{}]|\{(?:[^{}]|\{[^{}]*\})*\})*)\}'  # {nested braces}
            r'|"([^"]*)"'  # "quoted"
            r'|(\d+)'  # number
            r')',
            re.DOTALL
        )
        for fm in field_pattern.finditer(body):
            fname = fm.group(1).lower()
            fval = fm.group(2) or fm.group(3) or fm.group(4) or ""
            fval = re.sub(r'\s+', ' ', fval).strip()
            fields[fname] = fval

        entries[cite_key] = {
            "type": entry_type,
            "fields": fields,
            "raw": raw,
        }

    return entries


def extract_bib_metadata(entry: dict) -> dict:
    """从 BibTeX entry 提取标准化元数据。"""
    f = entry["fields"]

    # 作者：取第一作者姓氏
    author_raw = f.get("author", "")
    # 处理 "Last, First and Last2, First2" 格式
    first_author = author_raw.split(" and ")[0].strip()
    fa_surname = first_author.split(",")[0].strip()

    # 年份
    year_str = f.get("year", "0")
    year = int(re.search(r'\d{4}', year_str).group()) if re.search(r'\d{4}', year_str) else 0

    # 标题
    title = f.get("title", "")
    # 去掉保护用的花括号
    title = re.sub(r'[{}]', '', title)

    # 期刊
    journal = f.get("journal", f.get("booktitle", ""))

    return {
        "first_author": fa_surname,
        "author_full": author_raw,
        "year": year,
        "title": title,
        "journal": journal,
    }


# ---------------------------------------------------------------------------
# LaTeX 引用提取
# ---------------------------------------------------------------------------

def extract_citations_by_section(tex_content: str, rq_count: int = 2
                                  ) -> dict[str, list[dict]]:
    """从 manuscript.tex 中提取每个 section 的引用列表。

    返回 {cite_key: [{"section": ..., "subsection": ..., "context": ...}, ...]}
    """
    citation_map: dict[str, list[dict]] = {}

    current_section = ""
    current_subsection = ""

    # 去掉注释行
    lines = []
    for line in tex_content.split('\n'):
        stripped = line.lstrip()
        if not stripped.startswith('%'):
            lines.append(line)
    clean_content = '\n'.join(lines)

    # 按行处理，追踪 section 上下文
    for line in clean_content.split('\n'):
        # 检测 section（用 re.search 兼容缩进和行内出现）
        sec_m = re.search(r'\\section\*?\{(.+?)\}', line)
        if sec_m:
            current_section = sec_m.group(1).strip()
            current_subsection = ""
            continue

        subsec_m = re.search(r'\\subsection\*?\{(.+?)\}', line)
        if subsec_m:
            current_subsection = subsec_m.group(1).strip()
            continue

        # 提取引用命令：\cite, \citep, \citet, \citeN, \parencite, \textcite
        cite_pattern = r'\\(?:cite[pt]?|citeN|parencite|textcite)\{([^}]+)\}'
        for cm in re.finditer(cite_pattern, line):
            keys_str = cm.group(1)
            # 分割多 key：\citep{key1,key2,key3}
            keys = [k.strip() for k in keys_str.split(',') if k.strip()]

            # 提取引用上下文（当前行，截断到 150 字符）
            context = line.strip()
            context = re.sub(r'\\[a-zA-Z]+\{', '', context)  # 简化 LaTeX 命令
            context = re.sub(r'[{}]', '', context)
            context = context[:150]

            for key in keys:
                if key not in citation_map:
                    citation_map[key] = []
                citation_map[key].append({
                    "section": current_section,
                    "subsection": current_subsection,
                    "context": context,
                })

    return citation_map


# ---------------------------------------------------------------------------
# Section → Tag 映射
# ---------------------------------------------------------------------------

# 英文 section 标题 → 标签映射（keyword 匹配，取最长匹配优先）
SECTION_TAG_RULES = [
    # (section keyword, default tags)
    ("introduction", ["BG", "LR"]),
    ("literature", ["LR"]),
    ("review", ["LR"]),
    ("theoretical", ["LR"]),
    ("method", ["METHOD-基础"]),
    ("research design", ["METHOD-基础"]),
    ("data source", ["METHOD-先例"]),
    ("sample", ["METHOD-先例"]),
    ("measurement", ["METHOD-先例"]),
    ("calibration", ["METHOD-先例"]),
    ("result", ["DISC"]),
    ("finding", ["DISC"]),
    ("discussion", ["DISC"]),
    ("implication", ["DISC"]),
    ("conclusion", []),
    ("acknowledgment", []),
    ("appendix", []),
    ("supplement", []),
    ("data availability", []),
]

# 中文 section 标题映射
SECTION_TAG_RULES_ZH = [
    ("绪论", ["BG", "LR"]),
    ("引言", ["BG", "LR"]),
    ("文献综述", ["LR"]),
    ("文献回顾", ["LR"]),
    ("理论基础", ["LR"]),
    ("研究方法", ["METHOD-基础"]),
    ("研究设计", ["METHOD-基础"]),
    ("数据", ["METHOD-先例"]),
    ("变量", ["METHOD-先例"]),
    ("结果", ["DISC"]),
    ("发现", ["DISC"]),
    ("讨论", ["DISC"]),
    ("启示", ["DISC"]),
    ("结论", []),
    ("致谢", []),
    ("附录", []),
]

# 子节标题关键词 → RQ 编号推断
RQ_KEYWORDS = {
    # RQ1 相关（竞争优势、组态、SCA）
    "configuration": 1,
    "competitive advantage": 1,
    "antecedent": 1,
    "necessary condition": 1,
    "NCA": 1,
    "case tracing": 1,
    "组态": 1,
    "竞争优势": 1,
    "必要条件": 1,
    # RQ2 相关（韧性、危机）
    "resilience": 2,
    "crisis": 2,
    "disruption": 2,
    "韧性": 2,
    "危机": 2,
}


def section_to_tags(section: str, subsection: str, rq_count: int) -> list[str]:
    """将 section/subsection 标题映射到功能标签。"""
    tags = []
    sec_lower = section.lower()
    sub_lower = subsection.lower() if subsection else ""
    combined = f"{sec_lower} {sub_lower}"

    # 先匹配 section 级别
    for keyword, default_tags in SECTION_TAG_RULES + SECTION_TAG_RULES_ZH:
        if keyword.lower() in combined:
            tags.extend(default_tags)
            break

    if not tags:
        tags = ["LR"]  # 兜底

    # 将 DISC 展开为 DISC-RQx
    if "DISC" in tags:
        tags.remove("DISC")
        # 尝试从 subsection 推断 RQ 编号
        detected_rqs = set()
        for kw, rq_num in RQ_KEYWORDS.items():
            if kw.lower() in combined and rq_num <= rq_count:
                detected_rqs.add(rq_num)

        if detected_rqs:
            for rq in detected_rqs:
                tags.append(f"DISC-RQ{rq}")
        else:
            # 无法推断 → 标记所有 RQ
            for rq in range(1, rq_count + 1):
                tags.append(f"DISC-RQ{rq}")

    # 去重
    return list(dict.fromkeys(tags))


def assign_tags(citation_contexts: list[dict], rq_count: int) -> list[str]:
    """根据一篇文献的所有引用上下文，汇总标签。"""
    all_tags = []
    for ctx in citation_contexts:
        tags = section_to_tags(ctx["section"], ctx["subsection"], rq_count)
        all_tags.extend(tags)
    # 去重并保持顺序
    return list(dict.fromkeys(all_tags))


def assign_tier(citation_contexts: list[dict]) -> str:
    """根据引用次数和位置推断分级。"""
    sections = set(ctx["section"].lower() for ctx in citation_contexts)

    if len(sections) >= 3:
        return "core"
    elif len(sections) >= 2:
        return "important"
    else:
        return "backup"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Extract source project citations for pool integration")
    parser.add_argument("--source-bib", required=True,
                        help="Path to source project's .bib file")
    parser.add_argument("--source-tex", required=True,
                        help="Path to source project's manuscript.tex")
    parser.add_argument("--output", required=True,
                        help="Output _source_pool.json path")
    parser.add_argument("--rq-count", type=int, default=2,
                        help="Number of RQs (default: 2)")
    args = parser.parse_args()

    source_bib_path = Path(args.source_bib)
    source_tex_path = Path(args.source_tex)

    # 1. 解析 BibTeX
    try:
        bib_content = source_bib_path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"ERROR: Cannot read {source_bib_path}: {e}", file=sys.stderr)
        sys.exit(1)

    bib_entries = parse_bibtex(bib_content)
    print(f"  Parsed {len(bib_entries)} bib entries from {source_bib_path.name}",
          file=sys.stderr)

    # 2. 解析 manuscript.tex
    try:
        tex_content = source_tex_path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"ERROR: Cannot read {source_tex_path}: {e}", file=sys.stderr)
        sys.exit(1)

    citation_map = extract_citations_by_section(tex_content, args.rq_count)
    print(f"  Found {len(citation_map)} cited keys in {source_tex_path.name}",
          file=sys.stderr)

    # 3. 对每篇被引用的文献：提取元数据 + 映射标签 + 生成 citation key
    papers = []
    raw_keys = {}  # dedup_key → raw citation key
    key_to_source = {}  # dedup_key → source cite key

    for source_key, contexts in citation_map.items():
        if source_key not in bib_entries:
            print(f"  WARNING: cited key '{source_key}' not found in bib",
                  file=sys.stderr)
            continue

        entry = bib_entries[source_key]
        meta = extract_bib_metadata(entry)

        if meta["year"] == 0:
            print(f"  WARNING: no year for '{source_key}', skipping",
                  file=sys.stderr)
            continue

        # 生成 citation key（传完整作者名，函数内部会提取姓氏）
        ck = generate_citation_key(meta["author_full"], meta["year"], meta["title"])
        # 构建 dedup key（必须与 pool_prepare.py 的 dedup_key() 完全一致）
        dk = dedup_key(meta["author_full"], meta["year"], meta["title"])
        raw_keys[dk] = ck
        key_to_source[dk] = source_key

        # 标签
        tags = assign_tags(contexts, args.rq_count)
        tier = assign_tier(contexts)

        # 引用上下文（去重，最多保留 3 条）
        seen_sections = set()
        unique_contexts = []
        for ctx in contexts:
            sec_key = f"{ctx['section']}|{ctx['subsection']}"
            if sec_key not in seen_sections:
                seen_sections.add(sec_key)
                unique_contexts.append(ctx)
        unique_contexts = unique_contexts[:3]

        papers.append({
            "source_cite_key": source_key,
            "dedup_key": dk,
            "author": meta["first_author"],
            "author_full": meta["author_full"],
            "year": meta["year"],
            "title": meta["title"],
            "journal": meta["journal"],
            "tags": tags,
            "tier": tier,
            "citation_contexts": unique_contexts,
            "source_bib_entry": entry["raw"],
        })

    # 解决 citation key 冲突
    resolved_keys = resolve_key_conflicts(raw_keys)
    for p in papers:
        p["new_cite_key"] = resolved_keys.get(p["dedup_key"], "unknown0000x")

    # 4. 统计
    uncited_keys = [k for k in bib_entries if k not in citation_map]

    # 标签分布
    tag_dist: dict[str, int] = {}
    for p in papers:
        for t in p["tags"]:
            tag_dist[t] = tag_dist.get(t, 0) + 1

    # 5. 构建 key 映射
    key_map = {p["source_cite_key"]: p["new_cite_key"] for p in papers}

    # 6. 输出 JSON
    output_data = {
        "source_project": source_bib_path.stem,
        "source_bib": str(source_bib_path),
        "source_tex": str(source_tex_path),
        "total_bib_entries": len(bib_entries),
        "cited_in_manuscript": len(papers),
        "uncited_count": len(uncited_keys),
        "papers": papers,
        "key_map": key_map,
        "uncited_keys": uncited_keys[:20],  # 仅列前 20 个
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    # ===== stdout 结构化摘要 =====
    print("=== SOURCE BIB TO POOL ===")
    print(f"Source: {source_bib_path.name}")
    print(f"Bib entries: {len(bib_entries)}")
    print(f"Cited in manuscript: {len(papers)}")
    print(f"Uncited: {len(uncited_keys)}")
    print()

    print("Tag distribution:")
    for tag in sorted(tag_dist):
        print(f"  {tag}: {tag_dist[tag]}")
    print()

    # Key 映射样本
    print("Key mapping samples (first 5):")
    for p in papers[:5]:
        print(f"  {p['source_cite_key']} → {p['new_cite_key']}"
              f" ({p['author']} {p['year']})")
    print()

    # 校验
    errors = []
    if len(papers) == 0:
        errors.append("NO_PAPERS: No cited papers found")
    no_tags = [p for p in papers if not p["tags"]]
    if no_tags:
        errors.append(f"NO_TAGS: {len(no_tags)} papers have no tags")

    if errors:
        print("=== VERIFY: FAIL ===")
        for e in errors:
            print(f"  ❌ {e}")
        sys.exit(1)
    else:
        print("=== VERIFY: PASS ===")
        print(f"Output: {args.output}")


if __name__ == "__main__":
    main()
