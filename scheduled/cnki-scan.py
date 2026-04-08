#!/usr/bin/env python3
"""CNKI RSS Scanner — 从知网 RSS 抓取中文期刊最新论文，翻译为英文标题（可选），生成邮件推送。"""

import argparse
import json
import os
import re
import sys
import time
import urllib.request
import html as html_lib
from datetime import datetime, timedelta


def fetch_rss(journal_id, journal_name, rss_base_url):
    """Fetch and parse CNKI RSS for a journal."""
    url = f"{rss_base_url}{journal_id}"
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            content = resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"  ERROR {journal_id} ({journal_name}): {e}", file=sys.stderr)
        return []

    items = re.findall(r"<item>(.*?)</item>", content, re.DOTALL)
    papers = []

    for item in items:
        title_m = re.search(r"<title>([^<]+)</title>", item)
        link_m = re.search(r"<link>([^<]+)</link>", item)
        author_m = re.search(r"<author>([^<]*)</author>", item)
        desc_m = re.search(r"<description>([^<]*)</description>", item)
        date_m = re.search(r"<pubDate>([^<]+)</pubDate>", item)

        title = html_lib.unescape(title_m.group(1).strip()) if title_m else ""
        if not title:
            continue

        link = html_lib.unescape(link_m.group(1).strip()) if link_m else ""
        authors = author_m.group(1).strip().rstrip(";") if author_m else ""
        abstract = html_lib.unescape(desc_m.group(1).strip()) if desc_m else ""
        pub_date_str = date_m.group(1).strip() if date_m else ""

        # Parse date
        date_iso = ""
        if pub_date_str:
            try:
                dt = datetime.strptime(pub_date_str, "%a, %d %b %Y %H:%M:%S %Z")
                date_iso = dt.strftime("%Y-%m-%d")
            except ValueError:
                try:
                    dt = datetime.strptime(pub_date_str[:10], "%Y-%m-%d")
                    date_iso = dt.strftime("%Y-%m-%d")
                except ValueError:
                    pass

        papers.append({
            "journal_id": journal_id,
            "journal_name": journal_name,
            "title": title,
            "title_en": "",
            "authors": [a.strip() for a in authors.split(";") if a.strip()],
            "date": date_iso,
            "abstract": abstract,
            "abstract_en": "",
            "link": link,
            "doi": "",
        })

    return papers


def translate_titles(papers, api_key):
    """Translate Chinese titles to English using ChatAnywhere API."""
    import concurrent.futures

    api_url = "https://api.chatanywhere.tech/v1/chat/completions"

    def translate(text):
        if not text or len(text.strip()) < 3:
            return text
        body = json.dumps({
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": "将以下中文学术论文标题翻译为英文，保持学术术语准确。只返回翻译结果。"},
                {"role": "user", "content": text},
            ],
            "temperature": 0.3,
        }).encode()

        for attempt in range(3):
            try:
                req = urllib.request.Request(api_url, data=body, headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}",
                })
                with urllib.request.urlopen(req, timeout=30) as resp:
                    result = json.loads(resp.read())
                    return result["choices"][0]["message"]["content"].strip()
            except Exception:
                if attempt < 2:
                    time.sleep(2)
        return ""

    print("Translating titles to English...")
    titles = [p["title"] for p in papers]
    with concurrent.futures.ThreadPoolExecutor(max_workers=30) as ex:
        results = list(ex.map(translate, titles))
    for i, t in enumerate(results):
        papers[i]["title_en"] = t

    return papers


def main():
    parser = argparse.ArgumentParser(description="CNKI RSS Scanner")
    parser.add_argument("--config", required=True, help="Path to cnki-journals.json")
    parser.add_argument("--output", required=True, help="Output JSON path")
    parser.add_argument("--days", type=int, default=7, help="Only include papers from last N days")
    parser.add_argument("--translate", action="store_true", help="Translate titles to English")
    args = parser.parse_args()

    with open(args.config) as f:
        config = json.load(f)

    rss_base = config.get("rss_base_url", "https://rss.cnki.net/knavi/rss/")
    journals = config["journals"]
    cutoff = (datetime.now() - timedelta(days=args.days)).strftime("%Y-%m-%d")

    print(f"Scanning {len(journals)} CNKI journals (last {args.days} days, cutoff: {cutoff})")

    all_papers = []
    for j in journals:
        papers = fetch_rss(j["id"], j["name"], rss_base)
        # Filter by date
        recent = [p for p in papers if not p["date"] or p["date"] >= cutoff]
        if recent:
            print(f"  {j['id']:6s} {j['name']}: {len(recent)} papers")
        all_papers.extend(recent)
        time.sleep(0.3)

    print(f"Fetched: {len(all_papers)} papers from {len(set(p['journal_id'] for p in all_papers))} journals")

    if not all_papers:
        print("No papers found")
        with open(args.output, "w") as f:
            json.dump([], f)
        return

    # Optional translation
    if args.translate:
        api_key = os.environ.get("CHATANYWHERE_API_KEY", "")
        if api_key:
            all_papers = translate_titles(all_papers, api_key)
        else:
            print("WARNING: CHATANYWHERE_API_KEY not set, skipping translation", file=sys.stderr)

    with open(args.output, "w") as f:
        json.dump(all_papers, f, ensure_ascii=False)

    print(f"Output: {args.output} ({len(all_papers)} papers)")


if __name__ == "__main__":
    main()
