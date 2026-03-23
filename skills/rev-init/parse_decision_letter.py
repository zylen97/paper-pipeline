#!/usr/bin/env python3
"""
parse_decision_letter.py — 审稿决定信解析（rev-init §4a-4d）

将原始决定信解析为结构化数据：识别角色边界、标准化编号、清理杂项、
输出 JSON（供主 Agent 填充模板）。

替代主 Agent 的关键词扫描、编号转换、行过滤等手动工作。

用法:
    python3 parse_decision_letter.py \
        --input revision/comment-letter.md \
        --output revision/_parsed_letter.json

输出:
    1. stdout 结构化摘要 + 校验结果
    2. _parsed_letter.json（结构化解析数据）
"""

import argparse
import json
import re
import sys
from pathlib import Path


# ===========================================================================
# 角色检测关键词
# ===========================================================================

EDITOR_KEYWORDS = [
    r"(?:Editor['']?s?\s+)?(?:Decision|Comments?\s+(?:to|for)\s+(?:the\s+)?Author)",
    r"Dear\s+(?:Dr|Prof|Mr|Ms|Authors?)",
    r"Editor(?:-in-Chief)?(?:\s+Comments?)?",
    r"(?:The\s+)?Editor(?:'s)?\s+(?:decision|recommendation)",
]

AE_KEYWORDS = [
    r"Associate\s+Editor",
    r"\bAE\b(?:\s+Comments?)?",
    r"Handling\s+Editor",
]

REVIEWER_PATTERN = re.compile(
    r"(?:Reviewer|Referee)\s*(?:#?\s*(\d+)|\((\d+)\))",
    re.IGNORECASE
)

MAJOR_KEYWORDS = [
    r"Major\s+(?:Comments?|Revisions?|Issues?|Points?|Concerns?)",
]

MINOR_KEYWORDS = [
    r"Minor\s+(?:Comments?|Revisions?|Issues?|Points?|Concerns?)",
]

# 需要清理的行模式
JUNK_PATTERNS = [
    r"^From:\s+",
    r"^To:\s+",
    r"^Sent:\s+",
    r"^Date:\s+",
    r"^Subject:\s+",
    r"^CC:\s+",
    r"^Cc:\s+",
    r"^Content-Type:",
    r"^MIME-Version:",
    r"^Manuscript\s+(?:Central|Manager)\s+URL",
    r"^https?://\S+editorial\S*$",
    r"^-{5,}$",
    r"^={5,}$",
    r"^\*{5,}$",
    r"^_{5,}$",
    r"^Powered\s+by\s+",
    r"^ScholarOne\s+",
    r"^Editorial\s+Manager",
    r"^\d{1,2}/\d{1,2}/\d{2,4}\s+\d{1,2}:\d{2}",  # 日期时间
]


# ===========================================================================
# 解析逻辑
# ===========================================================================

def clean_lines(text: str) -> str:
    """清理邮件头、系统页脚等杂项行。"""
    cleaned = []
    junk_re = [re.compile(p, re.IGNORECASE) for p in JUNK_PATTERNS]

    for line in text.split("\n"):
        if any(p.search(line) for p in junk_re):
            continue
        cleaned.append(line)

    return "\n".join(cleaned)


def detect_decision(text: str) -> str:
    """检测审稿决定。"""
    text_lower = text.lower()
    if "major revision" in text_lower:
        return "Major Revision"
    if "minor revision" in text_lower:
        return "Minor Revision"
    if "reject" in text_lower and "resubmit" in text_lower:
        return "Reject & Resubmit"
    if "reject" in text_lower:
        return "Reject"
    if "accept" in text_lower:
        return "Accept"
    return "Unknown"


def split_into_sections(text: str) -> list[dict]:
    """将决定信按角色边界分段。

    返回列表：[{role: "editor"|"ae"|"reviewer", number: int|None, start: int, end: int, content: str}]
    """
    lines = text.split("\n")
    sections = []
    current = {"role": "preamble", "number": None, "start": 0, "lines": []}

    editor_re = [re.compile(p, re.IGNORECASE) for p in EDITOR_KEYWORDS]
    ae_re = [re.compile(p, re.IGNORECASE) for p in AE_KEYWORDS]

    for i, line in enumerate(lines):
        stripped = line.strip()

        # 检测 Reviewer 边界
        rev_match = REVIEWER_PATTERN.search(stripped)
        if rev_match:
            # 保存当前段
            if current["lines"] or current["role"] != "preamble":
                current["content"] = "\n".join(current["lines"])
                sections.append(current)
            num = int(rev_match.group(1) or rev_match.group(2))
            current = {"role": "reviewer", "number": num, "start": i, "lines": []}
            continue

        # 检测 AE 边界（在 Editor 之前检查，因为 AE 关键词更具体）
        if any(p.search(stripped) for p in ae_re):
            if current["lines"] or current["role"] != "preamble":
                current["content"] = "\n".join(current["lines"])
                sections.append(current)
            current = {"role": "ae", "number": None, "start": i, "lines": []}
            continue

        # 检测 Editor 边界
        if any(p.search(stripped) for p in editor_re):
            if current["role"] == "preamble" and not any(s["role"] == "editor" for s in sections):
                if current["lines"]:
                    current["content"] = "\n".join(current["lines"])
                    sections.append(current)
                current = {"role": "editor", "number": None, "start": i, "lines": []}
                continue

        current["lines"].append(line)

    # 保存最后一段
    current["content"] = "\n".join(current["lines"])
    sections.append(current)

    return [s for s in sections if s.get("content", "").strip()]


def parse_reviewer_comments(content: str, reviewer_num: int) -> list[dict]:
    """解析单个审稿人的意见，拆分为编号 Comments。

    返回：[{id: "R1-1", type: "major"|"minor"|"general", text: str}]
    """
    comments = []
    lines = content.split("\n")

    # 检测是否已分 Major/Minor
    major_re = [re.compile(p, re.IGNORECASE) for p in MAJOR_KEYWORDS]
    minor_re = [re.compile(p, re.IGNORECASE) for p in MINOR_KEYWORDS]

    current_type = "major"  # 默认
    has_major_minor = False

    # 先检测是否有 Major/Minor 分区
    for line in lines:
        if any(p.search(line) for p in major_re):
            has_major_minor = True
            break
        if any(p.search(line) for p in minor_re):
            has_major_minor = True
            break

    # 检测已有编号模式
    # 常见格式：1. / (1) / 1) / Comment 1: / #1
    numbered_pattern = re.compile(
        r"^\s*(?:"
        r"(\d+)\.\s+"           # "1. "
        r"|(?:\((\d+)\))\s+"    # "(1) "
        r"|(\d+)\)\s+"          # "1) "
        r"|(?:Comment|Point|Issue)\s*#?\s*(\d+)"  # "Comment 1"
        r"|#(\d+)\s+"           # "#1 "
        r")"
    )

    # 解析
    current_comment_lines = []
    current_num = 0
    major_count = 0
    minor_count = 0

    def flush_comment():
        nonlocal major_count, minor_count
        if not current_comment_lines:
            return
        text = "\n".join(current_comment_lines).strip()
        if not text or len(text) < 5:
            return

        if current_type == "minor":
            minor_count += 1
            cid = f"R{reviewer_num}-m{minor_count}"
        else:
            major_count += 1
            cid = f"R{reviewer_num}-{major_count}"

        comments.append({
            "id": cid,
            "type": current_type,
            "text": text,
        })

    for line in lines:
        stripped = line.strip()

        # 检测 Major/Minor 分区切换
        if any(p.search(stripped) for p in major_re):
            flush_comment()
            current_comment_lines = []
            current_type = "major"
            continue
        if any(p.search(stripped) for p in minor_re):
            flush_comment()
            current_comment_lines = []
            current_type = "minor"
            continue

        # 检测编号边界
        num_match = numbered_pattern.match(stripped)
        if num_match:
            flush_comment()
            current_comment_lines = []
            # 去掉编号前缀后的文本
            text_after = numbered_pattern.sub("", stripped, count=1).strip()
            if text_after:
                current_comment_lines.append(text_after)
            continue

        # 空行：如果当前有内容且下一个不是编号，可能是段落间隔
        if not stripped and current_comment_lines:
            current_comment_lines.append("")
            continue

        if stripped:
            current_comment_lines.append(line)

    flush_comment()

    # 如果没检测到编号，把整段作为一条 general comment
    if not comments and content.strip():
        # 过滤掉只有标题行的情况
        substantive = [l for l in lines if l.strip() and not REVIEWER_PATTERN.search(l)]
        if substantive:
            comments.append({
                "id": f"R{reviewer_num}-1",
                "type": "general",
                "text": "\n".join(substantive).strip(),
            })

    return comments


def detect_qa_section(text: str) -> list[dict]:
    """检测标准化 Q&A 区域（ASCE EM、Elsevier EES 等）。"""
    qa_items = []

    # 常见 Q&A 模式
    qa_patterns = [
        r"(?:Q|Question)\s*\d*[.:]\s*(.+?)(?:\n\s*(?:A|Answer)\s*\d*[.:]\s*(.+?))?(?=\n(?:Q|Question)\s*\d*[.:]|\Z)",
        r"(?:Is\s+.+?\?)\s*\n\s*(.+?)(?=\n(?:Is\s+|\Z))",
    ]

    for pattern in qa_patterns:
        for m in re.finditer(pattern, text, re.DOTALL | re.IGNORECASE):
            question = m.group(1).strip() if m.group(1) else ""
            answer = m.group(2).strip() if len(m.groups()) > 1 and m.group(2) else ""
            if question and answer and len(answer) > 20:  # 有实质性回答
                qa_items.append({"question": question[:100], "answer": answer})

    return qa_items


# ===========================================================================
# 主流程
# ===========================================================================

def parse_letter(text: str) -> dict:
    """解析完整决定信，返回结构化数据。"""
    # 1. 清理
    cleaned = clean_lines(text)

    # 2. 检测决定
    decision = detect_decision(text)

    # 3. 分段
    sections = split_into_sections(cleaned)

    # 4. 解析各段
    result = {
        "decision": decision,
        "editor": None,
        "ae": None,
        "reviewers": [],
        "reviewer_numbers": [],
        "total_comments": 0,
        "total_major": 0,
        "total_minor": 0,
    }

    for sec in sections:
        if sec["role"] == "editor":
            result["editor"] = {"content": sec["content"].strip()}
        elif sec["role"] == "ae":
            result["ae"] = {"content": sec["content"].strip()}
        elif sec["role"] == "reviewer":
            num = sec["number"]
            comments = parse_reviewer_comments(sec["content"], num)
            major = [c for c in comments if c["type"] == "major"]
            minor = [c for c in comments if c["type"] == "minor"]
            general = [c for c in comments if c["type"] == "general"]

            # 检测该审稿人是否明确区分了 Major/Minor
            has_major_minor_split = len(major) > 0 and len(minor) > 0

            reviewer = {
                "number": num,
                "raw_content": sec["content"].strip(),
                "comments": comments,
                "has_major_minor_split": has_major_minor_split,
                "major_count": len(major),
                "minor_count": len(minor),
                "general_count": len(general),
                "total": len(comments),
            }
            result["reviewers"].append(reviewer)
            result["reviewer_numbers"].append(num)
            result["total_comments"] += len(comments)
            result["total_major"] += len(major)
            result["total_minor"] += len(minor)

    # 5. Q&A 检测
    qa = detect_qa_section(text)
    if qa:
        result["qa_items"] = qa

    # 6. 编号连续性检查
    nums = sorted(result["reviewer_numbers"])
    result["numbering_continuous"] = (nums == list(range(nums[0], nums[-1] + 1))) if nums else True
    result["numbering_preserved"] = True  # 始终保留原始编号

    return result


# ===========================================================================
# 校验
# ===========================================================================

def verify(result: dict, original_text: str) -> list[str]:
    """内建校验。"""
    errors = []

    # 1. 至少检测到 1 个审稿人
    if not result["reviewers"]:
        errors.append("NO_REVIEWERS: No reviewers detected")

    # 2. 每个审稿人至少 1 条 comment
    for r in result["reviewers"]:
        if r["total"] == 0:
            errors.append(f"NO_COMMENTS: Reviewer #{r['number']} has 0 comments")

    # 3. Editor 段应存在
    if not result["editor"]:
        errors.append("NO_EDITOR: Editor section not detected (may be OK for some journals)")

    # 4. comment ID 全局唯一
    all_ids = []
    for r in result["reviewers"]:
        for c in r["comments"]:
            all_ids.append(c["id"])
    if len(all_ids) != len(set(all_ids)):
        duplicates = [cid for cid in all_ids if all_ids.count(cid) > 1]
        errors.append(f"DUPLICATE_IDS: {set(duplicates)}")

    # 5. 编号格式合规（RN-K 或 RN-mK）
    id_pattern = re.compile(r"^R\d+-(?:m?\d+)$")
    for cid in all_ids:
        if not id_pattern.match(cid):
            errors.append(f"BAD_ID_FORMAT: {cid}")

    return errors


# ===========================================================================
# main
# ===========================================================================

def main():
    parser = argparse.ArgumentParser(description="Parse review decision letter")
    parser.add_argument("--input", required=True,
                        help="Path to raw decision letter (comment-letter.md)")
    parser.add_argument("--output", default=None,
                        help="Output JSON path (default: _parsed_letter.json in same dir)")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"ERROR: {input_path} not found", file=sys.stderr)
        sys.exit(1)

    with open(input_path, encoding="utf-8") as f:
        text = f.read()

    if not text.strip():
        print("ERROR: Input file is empty", file=sys.stderr)
        sys.exit(1)

    # 解析
    result = parse_letter(text)

    # 校验
    errors = verify(result, text)

    # 输出 JSON
    output_path = args.output or str(input_path.parent / "_parsed_letter.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    # stdout
    print("=== PARSE DECISION LETTER ===")
    print(f"Decision: {result['decision']}")
    print(f"Editor: {'✅ detected' if result['editor'] else '❌ not found'}")
    print(f"AE: {'✅ detected' if result['ae'] else '(none)'}")
    print(f"Reviewers: {len(result['reviewers'])}")
    print(f"  Numbers: {result['reviewer_numbers']}")
    print(f"  Numbering continuous: {result['numbering_continuous']}")
    print()

    for r in result["reviewers"]:
        print(f"  Reviewer #{r['number']}: {r['total']} comments "
              f"(Major={r['major_count']}, Minor={r['minor_count']}, General={r['general_count']})")
    print()

    print(f"Total comments: {result['total_comments']}")
    print(f"  Major: {result['total_major']}")
    print(f"  Minor: {result['total_minor']}")

    if result.get("qa_items"):
        print(f"  Q&A items with substantive answers: {len(result['qa_items'])}")
    print()

    if errors:
        # NO_EDITOR 单独不算 FAIL（有些期刊确实没 Editor 段）
        real_errors = [e for e in errors if not e.startswith("NO_EDITOR")]
        if real_errors:
            print("=== VERIFY: FAIL ===")
            for e in errors:
                print(f"  ❌ {e}")
            sys.exit(1)
        else:
            print("=== VERIFY: PASS (with warnings) ===")
            for e in errors:
                print(f"  ⚠️ {e}")
    else:
        print("=== VERIFY: PASS ===")

    print(f"Output: {output_path}")


if __name__ == "__main__":
    main()
