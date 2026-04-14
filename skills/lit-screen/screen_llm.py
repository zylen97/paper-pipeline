"""
LLM 相关性批量筛选

用法:
  python3 screen_llm.py <ris_path> --direction "博弈论" [--threads 20] [--output filtered.ris]

对每篇论文的标题+摘要，用 LLM 判断是否与研究方向相关。
多线程并发调用 ChatAnywhere API (gpt-4o-mini)。
"""

import argparse
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# 复用 screen_xr 的 RIS 解析/写入
sys.path.insert(0, str(Path(__file__).parent))
from screen_xr import parse_ris, write_ris

# ChatAnywhere 配置
API_BASE = "https://api.chatanywhere.tech/v1"
MODEL = "gpt-4o-mini"

# 基于六非博 Literature Review Software 7B prompt 改进
# 改动：允许方法论关联（原版禁止"拓展、推测或主观关联"，导致跨领域方法论文献被误杀）
SYSTEM_PROMPT = """你的任务是解读文献摘要，判断其是否与用户的研究观点相关。判断标准：
1. **主题相关**：摘要研究的行业、情境或问题与用户研究直接相关，标注为 1
2. **方法相关**：摘要使用的理论框架、模型或分析方法与用户研究相同或高度相似，标注为 1
3. **无关**：主题和方法均无关联，标注为 0
请仅基于摘要本身的信息进行判断。请严格按照以下格式提供结果：标注. 理由（中文）"""


def _get_client(api_key: str):
    """获取或创建共享的 OpenAI client（线程安全）。"""
    global _shared_client
    if "_shared_client" not in globals() or _shared_client is None:
        from openai import OpenAI
        _shared_client = OpenAI(api_key=api_key, base_url=API_BASE, timeout=60)
    return _shared_client

_shared_client = None


def screen_one(index: int, title: str, abstract: str, direction: str, api_key: str) -> dict:
    """筛选单篇论文。返回 {index, relevant, reason} 或 {index, error}。"""
    # 六非博原版格式：system prompt 含判断规则，user message = 研究观点 + 摘要
    user_msg = f"以下是用户感兴趣的研究观点：{direction}\n\n标题：{title}\n摘要：{abstract}"

    client = _get_client(api_key)

    max_retries = 3
    for attempt in range(max_retries):
        try:
            resp = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_msg},
                ],
                temperature=0,
            )
            answer = resp.choices[0].message.content.strip()
            # 解析六非博格式: "1. 理由" 或 "0. 理由"
            relevant, reason = _parse_answer(answer)
            return {"index": index, "relevant": relevant, "reason": reason}
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(3)
            else:
                return {"index": index, "error": str(e)}

    return {"index": index, "error": "max retries exceeded"}


def _parse_answer(answer: str) -> tuple[bool, str]:
    """解析 LLM 返回的 '标注. 理由' 格式。"""
    answer = answer.strip()
    # 匹配 "1. 理由" 或 "0. 理由"（开头可能有空格）
    match = re.match(r"^\s*([01])\s*[.。:：]\s*(.*)$", answer, re.DOTALL)
    if match:
        label = match.group(1)
        reason = match.group(2).strip()
        return label == "1", reason
    # 回退：检查开头字符
    if answer.startswith("1"):
        return True, answer
    elif answer.startswith("0"):
        return False, answer
    # 最终回退：包含关键词
    if "直接相关" in answer or "标注为 1" in answer or "标注为1" in answer:
        return True, answer
    return False, answer


def screen(ris_path: str, direction: str, api_key: str, threads: int = 20, output_path: str | None = None):
    """
    批量 LLM 筛选。

    Args:
        ris_path: RIS 文件路径
        direction: 研究方向关键词
        api_key: ChatAnywhere API Key
        threads: 并发线程数
        output_path: 输出路径
    """
    records = parse_ris(ris_path)
    total = len(records)

    # 构建任务列表
    tasks = []
    for i, rec in enumerate(records):
        title = rec.get("TI", rec.get("T1", ""))
        if isinstance(title, list):
            title = " ".join(title)
        abstract = rec.get("AB", "")
        if isinstance(abstract, list):
            abstract = " ".join(abstract)
        tasks.append((i, title, abstract))

    # 多线程执行
    results = {}
    errors = 0
    done = 0

    with ThreadPoolExecutor(max_workers=threads) as executor:
        futures = {}
        for i, title, abstract in tasks:
            if not title and not abstract:
                # 没有标题和摘要的直接保留
                results[i] = {"index": i, "relevant": True, "reason": "无标题和摘要，默认保留"}
                done += 1
                continue
            f = executor.submit(screen_one, i, title, abstract, direction, api_key)
            futures[f] = i

        for f in as_completed(futures):
            result = f.result()
            idx = result["index"]
            results[idx] = result
            done += 1
            if "error" in result:
                errors += 1
            # 进度输出到 stderr（不干扰 stdout 的 JSON）
            if done % 50 == 0 or done == total:
                print(f"  进度: {done}/{total}", file=sys.stderr)

    # 分类
    kept = []
    removed = []
    error_records = []

    for i, rec in enumerate(records):
        r = results.get(i)
        if r is None or "error" in r:
            # 出错的默认保留
            error_records.append(rec)
        elif r["relevant"]:
            kept.append(rec)
        else:
            removed.append(rec)

    kept_all = kept + error_records

    # 输出
    if not output_path:
        base = Path(ris_path)
        output_path = str(base.parent / f"{base.stem}_llm{base.suffix}")

    write_ris(kept_all, output_path)

    # 输出统计
    stats = {
        "input": total,
        "relevant": len(kept),
        "irrelevant": len(removed),
        "errors": errors,
        "output": len(kept_all),
        "output_path": output_path,
        "direction": direction,
        "removed_titles": [
            (r.get("TI", r.get("T1", "unknown")))
            for r in removed[:30]  # 最多显示 30 篇
        ],
    }
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    return stats


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LLM 文献相关性筛选")
    parser.add_argument("ris_path", help="输入 RIS 文件路径")
    parser.add_argument("--direction", required=True, help="研究方向 (如 '博弈论')")
    parser.add_argument("--api-key", help="ChatAnywhere API Key (默认从环境变量 CHATANYWHERE_API_KEY 读取)")
    parser.add_argument("--threads", type=int, default=20, help="并发线程数 (默认 20)")
    parser.add_argument("--output", help="输出 RIS 文件路径")
    args = parser.parse_args()

    api_key = args.api_key or os.environ.get("CHATANYWHERE_API_KEY")
    if not api_key:
        print("错误: 需要 API Key，通过 --api-key 或 CHATANYWHERE_API_KEY 环境变量提供", file=sys.stderr)
        sys.exit(1)

    screen(args.ris_path, args.direction, api_key, args.threads, args.output)
