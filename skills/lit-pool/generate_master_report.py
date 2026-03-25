#!/usr/bin/env python3
"""Generate master_report.md skeleton with data sections auto-filled and judgment placeholders.

Step 1 of the two-step master report generation:
  1. Python fills all data tables (competitors, methods, tag stats, distribution)
  2. Main Agent fills judgment sections (marked with <!-- JUDGE: ... -->)

Data sources: ONLY permanent files (direction reports, tag_report.md, screening_summary,
citation_pool/). No dependency on _*.json intermediate files.

Usage:
    python3 generate_master_report.py \
      --pool-dir structure/2_literature/citation_pool/ \
      --data-dir structure/2_literature/ \
      --idea-file structure/0_global/idea.md \
      --output structure/2_literature/master_report.md
"""

import argparse, json, re, os, glob
from datetime import date


def parse_pool_table(filepath):
    """Parse citation pool markdown file, extract table rows.

    Pool tables: | 分级 | 作者 | 年份 | citation key | 引用场景 | ... |
    First column is tier (核心/重要/备选), not a number.
    """
    rows = []
    if not os.path.exists(filepath):
        return rows
    header_seen = False
    with open(filepath, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line.startswith('|'):
                continue
            if line.startswith('|:') or line.startswith('| -'):
                header_seen = True
                continue
            cells = [c.strip() for c in line.split('|')]
            cells = [c for c in cells if c]
            if not cells:
                continue
            if cells[0] in ('分级', '#', '标签', 'Tag'):
                continue
            if header_seen and cells:
                rows.append(cells)
    return rows


def load_json(filepath):
    if not os.path.exists(filepath):
        return {}
    with open(filepath, encoding='utf-8') as f:
        return json.load(f)


def extract_gaps_from_idea(idea_path):
    """Extract Gap/RQ table from idea.md."""
    gaps = []
    if not os.path.exists(idea_path):
        return gaps
    with open(idea_path, encoding='utf-8') as f:
        content = f.read()
    for m in re.finditer(r'^\| (G\d+)[:\s]*(.+?)(?:\|)', content, re.MULTILINE):
        gaps.append({'id': m.group(1), 'desc': m.group(2).strip()})
    return gaps


def parse_adequacy_from_tag_report(tag_report_path):
    """Parse adequacy table from tag_report.md. Returns list of dicts."""
    results = []
    if not os.path.exists(tag_report_path):
        return results
    with open(tag_report_path, encoding='utf-8') as f:
        in_adequacy = False
        for line in f:
            line = line.strip()
            if '均衡性预警' in line:
                in_adequacy = True
                continue
            if in_adequacy and line.startswith('|') and not line.startswith('|:') and not line.startswith('| 标签'):
                cells = [c.strip() for c in line.split('|')]
                cells = [c for c in cells if c]
                if cells and cells[0] in ('BG', 'LR', 'GAP', 'METHOD', 'DISC'):
                    try:
                        rate = float(cells[3].replace('%', ''))
                    except (ValueError, IndexError):
                        rate = 0
                    results.append({
                        'tag': cells[0],
                        'target': cells[1] if len(cells) > 1 else '?',
                        'actual': cells[2] if len(cells) > 2 else '?',
                        'rate_str': cells[3] if len(cells) > 3 else '?',
                        'status': cells[4] if len(cells) > 4 else '?',
                        'rate': rate,
                    })
            if in_adequacy and line.startswith('#') and '均衡' not in line:
                break
    return results


def extract_bg_refs(pool_dir):
    """Extract recent BG references for urgency section."""
    bg_rows = parse_pool_table(os.path.join(pool_dir, 'BG.md'))
    refs = []
    for row in bg_rows[:8]:  # top 8 BG references
        if len(row) >= 4:
            refs.append(f'{row[1]} ({row[2]})')
    return refs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--pool-dir', required=True)
    parser.add_argument('--data-dir', required=True)
    parser.add_argument('--idea-file', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--project-id', default='', help='Project ID for report title (e.g. zy06)')
    args = parser.parse_args()

    # === LOAD DATA (permanent files only) ===

    # 1. Total raw: sum "检索数" column from screening_summary table
    total_raw = 0
    summary_path = os.path.join(args.data_dir, 'screening_summary_report.md')
    if os.path.exists(summary_path):
        with open(summary_path, encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line.startswith('| D') and '|' in line:
                    cells = [c.strip() for c in line.split('|')]
                    cells = [c for c in cells if c]
                    if len(cells) >= 3:
                        try:
                            total_raw += int(cells[2])
                        except ValueError:
                            pass
    if total_raw == 0:
        for ris_path in glob.glob(os.path.join(args.data_dir, '*.ris')):
            with open(ris_path, encoding='utf-8-sig') as f:
                total_raw += f.read().count('TY  -')

    # 2. Per-direction stats + deduped tier counts from direction reports
    dir_reports = sorted(glob.glob(os.path.join(args.data_dir, 'direction*_report.md')))
    dir_stats = {}
    all_papers = {}  # dedup key -> highest tier
    tier_priority = {'core': 0, 'important': 1, 'backup': 2}

    for rpath in dir_reports:
        m = re.search(r'direction(\d+)', os.path.basename(rpath))
        if not m:
            continue
        dnum = int(m.group(1))
        with open(rpath, encoding='utf-8') as f:
            content = f.read()

        current_tier = None
        d_core = d_imp = d_bak = 0
        for line in content.split('\n'):
            if '核心文献' in line and line.startswith('#'):
                current_tier = 'core'
            elif '重要文献' in line and line.startswith('#'):
                current_tier = 'important'
            elif '备选文献' in line and line.startswith('#'):
                current_tier = 'backup'
            if not line.startswith('|') or line.startswith('|:') or line.startswith('| #'):
                continue
            cells = [c.strip() for c in line.split('|')]
            cells = [c for c in cells if c]
            if not cells or not cells[0].isdigit():
                continue
            if current_tier == 'core': d_core += 1
            elif current_tier == 'important': d_imp += 1
            elif current_tier == 'backup': d_bak += 1
            if len(cells) >= 4:
                key = f'{cells[1].lower()}_{cells[3]}_{cells[2][:40].lower()}'
                if key not in all_papers:
                    all_papers[key] = current_tier
                elif tier_priority.get(current_tier, 99) < tier_priority.get(all_papers[key], 99):
                    all_papers[key] = current_tier

        dir_stats[dnum] = {'core': d_core, 'important': d_imp, 'backup': d_bak,
                           'total': d_core + d_imp + d_bak}

    total_dedup = len(all_papers)
    total_core = sum(1 for t in all_papers.values() if t == 'core')
    total_imp = sum(1 for t in all_papers.values() if t == 'important')
    total_bak = sum(1 for t in all_papers.values() if t == 'backup')
    total_prededup = sum(s['total'] for s in dir_stats.values())

    dir_names = {}
    for rpath in dir_reports:
        bn = os.path.basename(rpath)
        nm = re.search(r'direction(\d+)_(.+?)_report\.md', bn)
        if nm:
            dir_names[int(nm.group(1))] = nm.group(2)

    # 3. Pool tables
    comp_rows = parse_pool_table(os.path.join(args.pool_dir, 'COMP.md'))
    method_rows = parse_pool_table(os.path.join(args.pool_dir, 'METHOD.md'))

    # 4. Adequacy from tag_report.md
    tag_report_path = os.path.join(args.data_dir, 'tag_report.md')
    adequacy_list = parse_adequacy_from_tag_report(tag_report_path)

    # 5. Gaps from idea.md
    gaps = extract_gaps_from_idea(args.idea_file)

    # 6. BG refs for urgency section
    bg_refs = extract_bg_refs(args.pool_dir)

    # === BUILD REPORT ===
    lines = []
    project_id = args.project_id or os.path.basename(os.path.dirname(os.path.abspath(args.output))).split('_')[0] if args.output else ''
    lines.append(f'# 文献总报告 — {project_id}' if project_id else '# 文献总报告')
    lines.append('')
    lines.append(f'> **日期**: {date.today().isoformat()}')
    lines.append(f'> **分析方向数**: {len(dir_stats)}')
    lines.append(f'> **文献总量**: 检索{total_raw}篇 → 去重后入选{total_dedup}篇（核心{total_core} + 重要{total_imp} + 备选{total_bak}）')
    lines.append('')
    lines.append('---')
    lines.append('')

    # --- Section 1: Competitors ---
    lines.append('## 一、创新性判断：有没有人做过？')
    lines.append('')
    lines.append('### 竞品论文清单')
    lines.append('')
    if comp_rows:
        # COMP.md: [0]分级 [1]作者 [2]年份 [3]key [4]引用场景(含差异) [5]期刊
        lines.append('| # | Citation Key | 作者 | 年份 | 分级 | 关键差异摘要 |')
        lines.append('|:--|:------------|:-----|:----:|:----:|:------------|')
        for i, row in enumerate(comp_rows, 1):
            tier = row[0] if len(row) > 0 else ''
            author = row[1] if len(row) > 1 else ''
            year = row[2] if len(row) > 2 else ''
            ckey = row[3] if len(row) > 3 else ''
            scenario = row[4] if len(row) > 4 else ''
            # Extract after "关键差异" marker, or use full text
            diff = scenario
            for sep in ['关键差异：', '关键差异:', '本文增量贡献：', '本文增量贡献:']:
                if sep in scenario:
                    diff = scenario.split(sep, 1)[1]
                    break
            lines.append(f'| {i} | {ckey} | {author} | {year} | {tier} | {diff[:120]}... |')
        lines.append('')
        lines.append(f'> 完整引用场景与差异分析详见 `citation_pool/COMP.md`')
    else:
        lines.append('*未发现竞品论文*')
    lines.append('')
    lines.append('### 判断')
    lines.append('')
    lines.append('<!-- JUDGE: 竞品判断 -->')
    lines.append('<!-- 请填写：(1)直接竞品有/无及差异化空间 (2)间接竞品列表 (3)结论(能做/需调整/风险高) -->')
    lines.append('')
    lines.append('---')
    lines.append('')

    # --- Section 2: Gap Analysis ---
    lines.append('## 二、Research Gap 分析')
    lines.append('')
    if gaps:
        lines.append('| Gap | 描述 | 评估 | 文献支撑 | 理由 |')
        lines.append('|:----|:-----|:----:|:---------|:-----|')
        for g in gaps:
            lines.append(f'| {g["id"]} | {g["desc"][:80]}... | <!-- JUDGE --> | <!-- JUDGE --> | <!-- JUDGE --> |')
    else:
        lines.append('<!-- JUDGE: Gap分析（idea.md中未找到Gap表格，请手动填写） -->')
    lines.append('')
    lines.append('---')
    lines.append('')

    # --- Section 3: Method Precedents ---
    lines.append('## 三、方法论先例')
    lines.append('')
    if method_rows:
        lines.append('| # | Citation Key | 作者 | 年份 | 分级 | 引用场景摘要 |')
        lines.append('|:--|:------------|:-----|:----:|:----:|:------------|')
        count = 0
        for row in method_rows:
            tier = row[0] if len(row) > 0 else ''
            if '核心' in tier or '重要' in tier:
                count += 1
                author = row[1] if len(row) > 1 else ''
                year = row[2] if len(row) > 2 else ''
                ckey = row[3] if len(row) > 3 else ''
                scenario = row[4][:80] if len(row) > 4 else ''
                lines.append(f'| {count} | {ckey} | {author} | {year} | {tier} | {scenario}... |')
                if count >= 20:
                    break
        lines.append('')
        lines.append(f'> 完整引用场景详见 `citation_pool/METHOD.md`')
    else:
        lines.append('*无方法论先例文献*')
    lines.append('')
    lines.append('### 结论')
    lines.append('')
    lines.append('<!-- JUDGE: 方法论结论 -->')
    lines.append('<!-- 请填写：方法论有充分先例/有部分先例需论证/首次应用需重点论证 -->')
    lines.append('')
    lines.append('---')
    lines.append('')

    # --- Section 4: Urgency ---
    lines.append('## 四、紧迫性与实践需求')
    lines.append('')
    if bg_refs:
        lines.append(f'> **参考素材**（BG引用池近年文献）：{", ".join(bg_refs)}')
        lines.append('')
    lines.append('<!-- JUDGE: 紧迫性 -->')
    lines.append('<!-- 请填写：')
    lines.append('  (1) 行业实践证据（至少引用2-3篇BG文献作为支撑）')
    lines.append('  (2) 政策/行业趋势（具体政策文件名称或行业事件）')
    lines.append('  (3) 结论（紧迫性高/中/低 + 一句话理由）-->')
    lines.append('')
    lines.append('---')
    lines.append('')

    # --- Section 5: Pool Adequacy ---
    lines.append('## 五、引用池充足性')
    lines.append('')
    lines.append('### 按分级')
    lines.append('')
    lines.append('| 分级 | 数量 | 充足性 |')
    lines.append('|:-----|:----:|:------:|')
    lines.append(f'| 核心 | {total_core} | {"✅" if total_core >= 50 else "⚠️"} |')
    lines.append(f'| 重要 | {total_imp} | {"✅" if total_imp >= 80 else "⚠️"} |')
    lines.append(f'| 备选 | {total_bak} | {"✅" if total_bak >= 40 else "⚠️"} |')
    lines.append('')
    lines.append('### 按标签')
    lines.append('')
    lines.append('| 标签 | Pool目标 | 实际入选 | 达标率 | 状态 |')
    lines.append('|:-----|:-------:|:-------:|:-----:|:----:|')
    if adequacy_list:
        for a in adequacy_list:
            lines.append(f'| {a["tag"]} | {a["target"]} | {a["actual"]} | {a["rate_str"]} | {a["status"]} |')
        # Auto-flag lowest adequacy tag
        lowest = min(adequacy_list, key=lambda x: x['rate'])
        lines.append('')
        lines.append(f'> **最低达标率**: {lowest["tag"]}（{lowest["rate_str"]}）。即使达标，写作时仍需关注该标签的文献覆盖深度。')
    else:
        targets = {'BG': 50, 'LR': 150, 'GAP': 75, 'METHOD': 60, 'DISC': 65}
        for tag_name, target in targets.items():
            lines.append(f'| {tag_name} | {target} | ? | ? | ? |')
    lines.append('')
    lines.append('---')
    lines.append('')

    # --- Section 6: Supplementary Search ---
    lines.append('## 六、补检建议')
    lines.append('')
    lines.append('<!-- JUDGE: 补检建议 -->')
    lines.append('<!-- 即使全部达标，也请检查：')
    lines.append('  (1) 达标率最低的标签是否写作时可能不够用')
    lines.append('  (2) 某个RQ的DISC文献是否偏少（如DISC-RQ1仅15篇）')
    lines.append('  (3) 是否有特定论点缺乏直接文献支撑')
    lines.append('  如确实无需补检，写"暂无补检需求"并说明理由 -->')
    lines.append('')
    lines.append('---')
    lines.append('')

    # --- Summary ---
    lines.append('## 综合评估')
    lines.append('')
    lines.append('### 本研究可行性')
    lines.append('')
    lines.append('<!-- JUDGE: 可行性 -->')
    lines.append('<!-- ✅可行 / ⚠️可行但需调整 / ❌风险过高，附1-2句理由 -->')
    lines.append('')
    lines.append('### 核心发现')
    lines.append('')
    lines.append('<!-- JUDGE: 文献分析的核心发现(3-5条) -->')
    lines.append('')
    lines.append('### 对研究设计的建议')
    lines.append('')
    lines.append('<!-- JUDGE: 建议(2-3条) -->')
    lines.append('')
    lines.append('### 文献分布可视化')
    lines.append('')
    lines.append('| 方向 | 名称 | 核心 | 重要 | 备选 | 小计 |')
    lines.append('|:-----|:-----|:----:|:----:|:----:|:----:|')
    for dk in sorted(dir_stats.keys()):
        s = dir_stats[dk]
        name = dir_names.get(dk, f'方向{dk}')
        lines.append(f'| D{dk} | {name} | {s["core"]} | {s["important"]} | {s["backup"]} | {s["total"]} |')
    lines.append(f'| **各方向合计** | *(含跨方向重复)* | | | | **{total_prededup}** |')
    lines.append(f'| **去重后独立文献** | | **{total_core}** | **{total_imp}** | **{total_bak}** | **{total_dedup}** |')
    lines.append('')

    # === WRITE ===
    os.makedirs(os.path.dirname(args.output) or '.', exist_ok=True)
    with open(args.output, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

    # === VERIFY ===
    judge_count = sum(1 for l in lines if '<!-- JUDGE' in l)
    table_count = sum(1 for l in lines if l.startswith('|') and not l.startswith('|:'))
    method_core_imp = len([r for r in method_rows if len(r) >= 1 and ('核心' in r[0] or '重要' in r[0])])

    errors = []
    if len(comp_rows) == 0:
        errors.append('COMP table empty')
    if method_core_imp == 0:
        errors.append('METHOD table empty')
    if total_raw == 0:
        errors.append('total_raw is 0')
    if total_dedup == 0:
        errors.append('total_dedup is 0')
    if len(dir_stats) == 0:
        errors.append('dir_stats empty')
    if total_core + total_imp + total_bak != total_dedup:
        errors.append(f'tier sum {total_core}+{total_imp}+{total_bak}={total_core+total_imp+total_bak} != {total_dedup}')

    print(f'=== MASTER REPORT SKELETON ===')
    print(f'Output: {args.output}')
    print(f'Lines: {len(lines)}')
    print(f'Data tables: {table_count} rows')
    print(f'Judgment placeholders: {judge_count}')
    print(f'Competitors listed: {len(comp_rows)}')
    print(f'Method precedents listed: {min(method_core_imp, 20)}')
    print(f'Adequacy tags: {len(adequacy_list)}')
    print(f'Total raw: {total_raw}, Dedup: {total_dedup} (core={total_core}, imp={total_imp}, bak={total_bak})')
    if errors:
        print(f'=== VERIFY: FAIL ===')
        for e in errors:
            print(f'  ERROR: {e}')
    else:
        print(f'=== VERIFY: PASS ===')


if __name__ == '__main__':
    main()
