#!/usr/bin/env python3
"""
pool_prepare.py — 引用池预处理（lit-pool §1-2）

从打完标签的 direction reports 中提取所有入选文献，
跨方向去重，生成 citation key，按标签分组，计算 Agent 调度计划。

替代主 Agent 的手动表格解析、去重、key 生成和 bin-packing。

用法:
    python3 pool_prepare.py \
        --report-dir structure/2_literature/ \
        --output-dir structure/2_literature/ \
        --agent-limit 30

输出:
    1. stdout 结构化摘要 + 校验结果
    2. _pool_prepare.json（结构化数据：去重后文献 + citation keys + 标签分组 + 调度计划）
"""

import argparse
import json
import math
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

# 中文拼音支持（可选依赖）
try:
    from pypinyin import lazy_pinyin
    HAS_PINYIN = True
except ImportError:
    HAS_PINYIN = False


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

# 中文复姓列表
_COMPOUND_SURNAMES = {
    "欧阳", "司马", "上官", "诸葛", "司徒", "令狐", "宇文", "长孙",
    "慕容", "皇甫", "东方", "端木", "公孙", "南宫", "独孤", "赫连",
}

# 中文常见虚词（用于标题首实词提取时跳过）
_CN_STOP = set("的了是在有和与及其对从以为被把将而也都能要不")


def _is_cjk(char: str) -> bool:
    """判断单个字符是否为 CJK 汉字。"""
    return '\u4e00' <= char <= '\u9fff'


def _has_cjk(s: str) -> bool:
    """判断字符串是否包含 CJK 汉字。"""
    return any(_is_cjk(c) for c in s)


def chinese_surname_to_pinyin(name: str) -> str:
    """中文姓氏转拼音。支持复姓（欧阳→ouyang）。
    pypinyin 不可用时 fallback 到 Unicode 码位。"""
    if not name:
        return "unknown"
    if not HAS_PINYIN:
        return "cn" + format(ord(name[0]), 'x')
    # 检查复姓
    for cs in _COMPOUND_SURNAMES:
        if name.startswith(cs):
            result = ''.join(lazy_pinyin(cs))
            if result:
                return result
    # 单姓
    result = ''.join(lazy_pinyin(name[0]))
    return result if result else "cn" + format(ord(name[0]), 'x')


def chinese_title_initial(title: str) -> str:
    """中文标题取首个实词的拼音首字母。"""
    for ch in title:
        if _is_cjk(ch) and ch not in _CN_STOP:
            if HAS_PINYIN:
                py = lazy_pinyin(ch)
                return py[0][0] if py and py[0] else 'x'
            else:
                return 'x'
    return 'x'


# 英文常见停用词（用于 citation key 生成时跳过）
STOP_WORDS = {
    "a", "an", "the", "of", "in", "on", "at", "to", "for", "and", "or",
    "is", "are", "was", "were", "be", "been", "by", "with", "from",
    "as", "into", "through", "during", "before", "after", "between",
    "how", "what", "when", "where", "which", "who", "whom", "why",
    "do", "does", "did", "has", "have", "had", "can", "could",
    "will", "would", "shall", "should", "may", "might", "must",
    "not", "no", "nor", "but", "if", "then", "than", "so",
    "its", "it", "this", "that", "these", "those",
}


def normalize_text(s: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace."""
    s = s.lower().strip()
    s = unicodedata.normalize("NFKD", s)
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def dedup_key(author: str, year: int, title: str) -> str:
    """跨方向去重键：first_author(lower) + year + title[:40](normalized)."""
    fa = author.split(",")[0].split(";")[0].strip().lower()
    ti = normalize_text(title)[:40]
    return f"{fa}|{year}|{ti}"


def generate_citation_key(author: str, year: int, title: str) -> str:
    """按全局规则生成 citation key: auth.lower + year + shorttitle(1,1)。
    格式：第一作者姓氏小写 + 四位年份 + 标题首个实词首字母小写。
    示例：
      Akcomak (2023) "What drives network evolution?" → akcomak2023w
      陶鸠 (2026) "价值创造与资源重构" → tao2026j
      欧阳明 (2025) "数字化转型" → ouyang2025s
    """
    # 提取第一作者姓氏
    fa_raw = author.split(",")[0].split(";")[0].strip()
    # 去掉可能的名缩写（如 "Smith J." → "Smith"）
    fa_raw = re.sub(r"\s+[A-Z]\.?$", "", fa_raw).strip()

    # 判断是否中文作者
    if _has_cjk(fa_raw):
        fa = chinese_surname_to_pinyin(fa_raw)
    else:
        fa = fa_raw.lower()
        fa = re.sub(r"[^a-z]", "", fa)

    if not fa:
        fa = "unknown"

    # 提取标题首个实词的首字母（先尝试英文）
    title_words = re.findall(r"[a-zA-Z]+", title.lower())
    first_content_word = ""
    for w in title_words:
        if w not in STOP_WORDS:
            first_content_word = w[0]
            break
    # 英文标题 fallback
    if not first_content_word and title_words:
        first_content_word = title_words[0][0]
    # 中文标题 fallback
    if not first_content_word:
        if _has_cjk(title):
            first_content_word = chinese_title_initial(title)
        else:
            first_content_word = "x"

    return f"{fa}{year}{first_content_word}"


def resolve_key_conflicts(keys: dict[str, str]) -> dict[str, str]:
    """处理 citation key 冲突：同 key 追加 b/c/d... 后缀。
    输入：{dedup_key: citation_key}
    输出：{dedup_key: resolved_citation_key}
    """
    # 统计每个 citation key 出现次数
    key_groups: dict[str, list[str]] = defaultdict(list)
    for dk, ck in keys.items():
        key_groups[ck].append(dk)

    resolved = {}
    for ck, dks in key_groups.items():
        if len(dks) == 1:
            resolved[dks[0]] = ck
        else:
            # 按 dedup_key 排序保证稳定
            for i, dk in enumerate(sorted(dks)):
                if i == 0:
                    resolved[dk] = ck
                else:
                    suffix = chr(ord('b') + i - 1)  # b, c, d, ...
                    resolved[dk] = f"{ck}{suffix}"

    return resolved


# ---------------------------------------------------------------------------
# 解析 direction report（复用 tag_aggregate.py 的逻辑）
# ---------------------------------------------------------------------------

def parse_report(filepath: Path) -> list[dict]:
    """从带标签的 direction report 中提取所有入选文献。"""
    try:
        with open(filepath, encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        print(f"WARNING: Cannot read {filepath}: {e}", file=sys.stderr)
        return []

    d_match = re.match(r"direction(\d+)", filepath.name)
    direction = int(d_match.group(1)) if d_match else 0

    # 提取方向名称（从标题行）
    name_match = re.search(r"#\s*方向\d+[：:]\s*(.+?)(?:\s*文献|$)", content)
    direction_name = name_match.group(1).strip() if name_match else f"方向{direction}"

    papers = []
    current_tier = None

    for line in content.split("\n"):
        if re.match(r"^##\s.*(核心文献|Core)", line, re.IGNORECASE):
            current_tier = "core"
        elif re.match(r"^##\s.*(重要文献|Important)", line, re.IGNORECASE):
            current_tier = "important"
        elif re.match(r"^##\s.*(备选文献|Backup)", line, re.IGNORECASE):
            current_tier = "backup"

        # 7列（带标签）
        m7 = re.match(
            r"\|\s*(\d+)\s*\|"
            r"\s*([^|]+)\|"
            r"\s*([^|]+)\|"
            r"\s*(\d{4})\s*\|"
            r"\s*([^|]+)\|"
            r"\s*([^|]+)\|"
            r"\s*([^|]+)\|",
            line
        )
        if m7:
            tags_raw = m7.group(6).strip()
            # 去掉反引号，统一分隔符
            tags_raw = tags_raw.replace("`", "")
            tags_raw = tags_raw.replace("\\|", ";")
            tags_raw = tags_raw.replace("\\", "")
            if tags_raw.strip() in ("—", "-", "N/A", ""):
                tags = []
            else:
                tags = [t.strip().rstrip("\\").strip() for t in re.split(r"[+,、/;|]", tags_raw) if t.strip().rstrip("\\").strip()]
            papers.append({
                "direction": direction,
                "direction_name": direction_name,
                "author": m7.group(2).strip(),
                "title": m7.group(3).strip(),
                "year": int(m7.group(4)),
                "journal": m7.group(5).strip(),
                "tags": tags,
                "tier": current_tier or "backup",
                "reason": m7.group(7).strip(),
            })

    return papers


# ---------------------------------------------------------------------------
# 去重 + citation key
# ---------------------------------------------------------------------------

TIER_ORDER = {"core": 0, "important": 1, "backup": 2}


def deduplicate(all_papers: list[dict]) -> list[dict]:
    """跨方向去重。同一文献保留最高分级，合并标签和来源方向。"""
    seen: dict[str, dict] = {}

    for p in all_papers:
        dk = dedup_key(p["author"], p["year"], p["title"])
        if dk not in seen:
            seen[dk] = {
                **p,
                "source_directions": [p["direction"]],
                "all_reasons": [p["reason"]],
            }
        else:
            existing = seen[dk]
            # 保留最高分级
            if TIER_ORDER.get(p["tier"], 2) < TIER_ORDER.get(existing["tier"], 2):
                existing["tier"] = p["tier"]
            # 合并标签
            for tag in p["tags"]:
                if tag not in existing["tags"]:
                    existing["tags"].append(tag)
            # 合并来源方向
            if p["direction"] not in existing["source_directions"]:
                existing["source_directions"].append(p["direction"])
            # 合并理由
            if p["reason"] not in existing["all_reasons"]:
                existing["all_reasons"].append(p["reason"])

    # 生成 citation key
    raw_keys = {}
    for dk, p in seen.items():
        raw_keys[dk] = generate_citation_key(p["author"], p["year"], p["title"])

    resolved_keys = resolve_key_conflicts(raw_keys)

    # 附加 citation key
    result = []
    for dk, p in seen.items():
        p["citation_key"] = resolved_keys[dk]
        p["dedup_key"] = dk
        result.append(p)

    return result


# ---------------------------------------------------------------------------
# 按标签分组 + 贪心合并
# ---------------------------------------------------------------------------

def group_by_tag(papers: list[dict]) -> dict[str, list[dict]]:
    """按标签分组（一篇文献可出现在多个标签组）。"""
    groups: dict[str, list[dict]] = defaultdict(list)
    for p in papers:
        for tag in p["tags"]:
            groups[tag].append(p)
    return dict(groups)


def plan_agents(tag_groups: dict[str, list[dict]], limit: int) -> list[dict]:
    """按标签分组计算 agent 调度，小标签贪心合并。"""
    agents = []
    agent_id = 1

    large_tags = {}
    small_tags = {}

    for tag, papers in sorted(tag_groups.items()):
        n = len(papers)
        if n == 0:
            continue
        if n > limit // 2:  # > 15 的算大
            large_tags[tag] = papers
        else:
            small_tags[tag] = papers

    # 大标签：按 limit 拆分
    for tag, papers in large_tags.items():
        n = len(papers)
        n_agents = math.ceil(n / limit)
        per_agent = math.ceil(n / n_agents)

        # 按来源方向分段
        for i in range(n_agents):
            start = i * per_agent
            end = min((i + 1) * per_agent, n)
            batch = papers[start:end]
            src_dirs = sorted(set(d for p in batch for d in p.get("source_directions", [p.get("direction")])))
            agents.append({
                "agent_id": agent_id,
                "tags": [tag],
                "item_count": len(batch),
                "split_info": f"拆分{i + 1}/{n_agents}" if n_agents > 1 else "独立",
                "source_directions": src_dirs,
                "paper_keys": [p["citation_key"] for p in batch],
            })
            agent_id += 1

    # 小标签：贪心合并
    if small_tags:
        sorted_small = sorted(small_tags.items(), key=lambda x: len(x[1]), reverse=True)
        bins: list[dict] = []

        for tag, papers in sorted_small:
            n = len(papers)
            placed = False
            for b in bins:
                if b["item_count"] + n <= limit:
                    b["tags"].append(tag)
                    b["item_count"] += n
                    b["paper_keys"].extend(p["citation_key"] for p in papers)
                    src = set(b.get("source_directions", []))
                    for p in papers:
                        src.update(p.get("source_directions", [p.get("direction")]))
                    b["source_directions"] = sorted(src)
                    placed = True
                    break
            if not placed:
                src_dirs = sorted(set(d for p in papers for d in p.get("source_directions", [p.get("direction")])))
                bins.append({
                    "tags": [tag],
                    "item_count": n,
                    "source_directions": src_dirs,
                    "paper_keys": [p["citation_key"] for p in papers],
                })

        for b in bins:
            b["agent_id"] = agent_id
            b["split_info"] = "合并" if len(b["tags"]) > 1 else "独立"
            agents.append(b)
            agent_id += 1

    return agents


# ---------------------------------------------------------------------------
# 校验
# ---------------------------------------------------------------------------

CK_PATTERN = re.compile(r"^[a-z][a-z0-9]*\d{4}[a-z][a-z]?$")


def verify(papers: list[dict], tag_groups: dict[str, list[dict]],
           agents: list[dict], all_papers_raw: list[dict]) -> list[str]:
    """内建校验。"""
    errors = []

    # 1. citation key 格式校验
    for p in papers:
        ck = p.get("citation_key", "")
        if not CK_PATTERN.match(ck):
            errors.append(f"KEY_FORMAT: '{ck}' for '{p['author']}({p['year']})' does not match pattern")

    # 2. citation key 全局唯一
    key_set: dict[str, list[str]] = defaultdict(list)
    for p in papers:
        key_set[p["citation_key"]].append(f"{p['author']}({p['year']})")
    for ck, owners in key_set.items():
        if len(owners) > 1:
            errors.append(f"KEY_DUPLICATE: '{ck}' used by: {', '.join(owners)}")

    # 3. 每篇文献至少有 1 个标签
    no_tag = [p for p in papers if not p.get("tags")]
    if no_tag:
        errors.append(f"NO_TAGS: {len(no_tag)} papers have no tags")

    # 4. agent 调度一致性（每个标签的文献都被分配到 agent）
    for tag, tag_papers in tag_groups.items():
        agent_keys = set()
        for a in agents:
            if tag in a["tags"]:
                agent_keys.update(a.get("paper_keys", []))
        paper_keys = {p["citation_key"] for p in tag_papers}
        missing = paper_keys - agent_keys
        if missing:
            errors.append(f"AGENT_MISSING: tag={tag}, {len(missing)} papers not assigned to any agent")

    # 5. 去重前后数量关系
    if len(papers) > len(all_papers_raw):
        errors.append(f"DEDUP_ERROR: deduped={len(papers)} > raw={len(all_papers_raw)}")

    return errors


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Prepare citation pool data")
    parser.add_argument("--report-dir", required=True,
                        help="Directory containing tagged direction*_report.md files")
    parser.add_argument("--output-dir", required=True,
                        help="Directory for output JSON")
    parser.add_argument("--agent-limit", type=int, default=30,
                        help="Agent item limit (default: 30)")
    args = parser.parse_args()

    report_dir = Path(args.report_dir)
    output_dir = Path(args.output_dir)

    # 1. 扫描 reports
    report_files = sorted(report_dir.glob("direction*_report.md"))
    if not report_files:
        print("ERROR: No direction reports found", file=sys.stderr)
        sys.exit(1)

    all_papers_raw = []
    for fp in report_files:
        papers = parse_report(fp)
        all_papers_raw.extend(papers)
        print(f"  Parsed {fp.name}: {len(papers)} papers", file=sys.stderr)

    if not all_papers_raw:
        print("ERROR: No papers found in reports", file=sys.stderr)
        sys.exit(1)

    # 2. 去重 + citation key
    papers = deduplicate(all_papers_raw)

    # 3. 按标签分组
    tag_groups = group_by_tag(papers)

    # 4. Agent 调度
    agents = plan_agents(tag_groups, args.agent_limit)

    # 5. 校验
    errors = verify(papers, tag_groups, agents, all_papers_raw)

    # 6. 写出 JSON
    json_path = str(output_dir / "_pool_prepare.json")

    # 构建 citation key 映射表（供 subAgent 使用）
    key_map = []
    for i, p in enumerate(papers, 1):
        key_map.append({
            "seq": i,
            "citation_key": p["citation_key"],
            "author": p["author"],
            "year": p["year"],
            "title": p["title"],
            "journal": p["journal"],
            "tags": p["tags"],
            "tier": p["tier"],
            "reason": p.get("reason", ""),
            "source_directions": p.get("source_directions", []),
        })

    output_data = {
        "total_raw": len(all_papers_raw),
        "total_deduped": len(papers),
        "duplicates_removed": len(all_papers_raw) - len(papers),
        "papers": key_map,
        "tag_groups": [
            {
                "tag": tag,
                "count": len(tag_papers),
                "source_directions": sorted(set(
                    d for p in tag_papers
                    for d in p.get("source_directions", [p.get("direction")])
                )),
            }
            for tag, tag_papers in sorted(tag_groups.items())
        ],
        "agents": agents,
    }

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    # ===== 生成模板文件（模板填空 + 结构分离） =====
    POOL_TEMPLATE = (
        "（逐条添加文献，严格按以下格式。不要添加任何 # 标题行。）\n\n"
        "### paper1\n"
        "- 标签: {{标签名，如 BG / GAP-RQ1 / METHOD-先例}}\n"
        "- citation_key: {{原样复制，不可修改}}\n"
        "- 分级: {{核心/重要/备选}}\n"
        "- 作者: {{作者}}\n"
        "- 年份: {{4位数字}}\n"
        "- 引用场景: {{中文描述}}\n"
        "- 期刊: {{从报告原样复制完整期刊名，不要缩写}}\n"
    )
    tpl_count = 0
    for a in agents:
        agent_id = a["agent_id"]
        tpl_path = output_dir / f"_tmp_pool_agent{agent_id}_raw.md"
        tpl_path.write_text(POOL_TEMPLATE, encoding="utf-8")
        tpl_count += 1
    print(f"Templates generated: {tpl_count} files", file=sys.stderr)

    # ===== stdout 结构化摘要 =====
    print(f"=== POOL PREPARE ===")
    print(f"Reports parsed: {len(report_files)}")
    print(f"Raw papers: {len(all_papers_raw)}")
    print(f"After dedup: {len(papers)}")
    print(f"Duplicates removed: {len(all_papers_raw) - len(papers)}")
    print()

    # 标签分组
    print("Tag groups:")
    for tag in sorted(tag_groups):
        print(f"  {tag}: {len(tag_groups[tag])} papers")
    print()

    # Citation key 样本
    print("Citation key samples (first 5):")
    for p in papers[:5]:
        print(f"  {p['citation_key']} ← {p['author']} ({p['year']}) \"{p['title'][:50]}...\"")
    print()

    # Agent 调度表
    print(f"Agent dispatch ({len(agents)} agents):")
    print("| Agent# | 标签 | 条目数 | 拆分 |")
    print("|:------:|:-----|:------:|:----:|")
    for a in agents:
        tags_str = "+".join(a["tags"])
        print(f"| {a['agent_id']} | {tags_str} | {a['item_count']} | {a['split_info']} |")
    print()

    # 校验结果
    if errors:
        print("=== VERIFY: FAIL ===")
        for e in errors:
            print(f"  ❌ {e}")
        sys.exit(1)
    else:
        print("=== VERIFY: PASS ===")
        print(f"Output: {json_path}")


if __name__ == "__main__":
    main()
