#!/bin/bash
# CE/PM Daily Scan — 每天 9:05 自动扫描建工/PM期刊最近5天新论文
# 由 launchd 触发，通过独立 Python 脚本执行扫描

LOG_DIR="$HOME/.claude/scheduled/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/cepm-$(date +%Y%m%d-%H%M%S).log"
TODAY=$(date +%Y-%m-%d)
SCAN_FROM=$(date -v-5d +%Y-%m-%d)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# 设置 PATH（launchd 环境不继承 shell 的 PATH）
export PATH="$HOME/.local/bin:$HOME/develop/flutter/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

# 加载配置
source "$SCRIPT_DIR/email-config.sh"
export CHATANYWHERE_API_KEY

echo "=== CE/PM Daily Scan ===" >> "$LOG_FILE"
echo "Started: $(date), range: $SCAN_FROM ~ $TODAY" >> "$LOG_FILE"

# 在 idea_scout 仓库目录下运行
cd "$HOME/idea_scout" || {
    echo "ERROR: ~/idea_scout not found" >> "$LOG_FILE"
    osascript -e 'display notification "idea_scout dir not found" with title "CE/PM Scout" subtitle "Failed" sound name "Basso"'
    exit 1
}

# ── 扫描（独立 Python 脚本） ──
python3 "$SCRIPT_DIR/scout-scan.py" \
    --config "$SCRIPT_DIR/cepm-journals.json" \
    --from "$SCAN_FROM" --to "$TODAY" \
    --output "data/cepm_latest.json" \
    >> "$LOG_FILE" 2>&1

EXIT_CODE=$?
echo "Scan finished: $(date), exit code: $EXIT_CODE" >> "$LOG_FILE"

if [ $EXIT_CODE -ne 0 ] || [ ! -s "data/cepm_latest.json" ]; then
    echo "Scan failed, aborting" >> "$LOG_FILE"
    osascript -e 'display notification "CE/PM scan failed, check logs" with title "CE/PM Scout" subtitle "Failed" sound name "Basso"'
    exit 1
fi

# ── 合并数据 ──
python3 - "data/cepm_latest.json" "data/cepm_papers.json" "$TODAY" << 'PYEOF'
import json, sys

latest_path, papers_path, scan_date = sys.argv[1], sys.argv[2], sys.argv[3]

try:
    with open(latest_path, 'r') as f:
        new_papers = json.load(f)
    if isinstance(new_papers, dict) and 'papers' in new_papers:
        new_papers = new_papers['papers']
except Exception as e:
    print(f"Cannot read cepm_latest.json: {e}", file=sys.stderr)
    sys.exit(0)

for p in new_papers:
    p['scan_date'] = scan_date

try:
    with open(papers_path, 'r') as f:
        all_papers = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    all_papers = []

doi_map = {p.get('doi', ''): p for p in all_papers if p.get('doi')}
for p in new_papers:
    if p.get('doi'):
        doi_map[p['doi']] = p
all_papers = list(doi_map.values())

from datetime import datetime, timedelta
cutoff = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
all_papers = [p for p in all_papers if p.get('scan_date', p.get('date', '9999')) >= cutoff]
all_papers.sort(key=lambda p: p.get('date', ''), reverse=True)

with open(papers_path, 'w') as f:
    json.dump(all_papers, f, ensure_ascii=False)

print(f"Merged: {len(new_papers)} new, {len(all_papers)} total")
PYEOF

echo "Merge done" >> "$LOG_FILE"

# ── 推送到 GitHub + 部署 gh-pages ──
git add data/cepm_latest.json data/cepm_papers.json
git commit -m "cepm: $TODAY - scan from $SCAN_FROM" 2>> "$LOG_FILE"
git push origin main >> "$LOG_FILE" 2>&1

# 部署到 gh-pages（只更新数据，不重建 Flutter）
# 复制所有 data/*.json 避免覆盖 FT50 数据
mkdir -p /tmp/idea_scout_all_data
cp data/*.json /tmp/idea_scout_all_data/
git checkout gh-pages 2>> "$LOG_FILE"
cp /tmp/idea_scout_all_data/*.json data/
git add data/
git commit -m "data: cepm $TODAY" 2>> "$LOG_FILE"
git push origin gh-pages >> "$LOG_FILE" 2>&1
git checkout main 2>> "$LOG_FILE"
rm -rf /tmp/idea_scout_all_data

echo "GitHub push done" >> "$LOG_FILE"

# ── 通知 ──
osascript -e "display notification \"CE/PM scan done\" with title \"CE/PM Scout\" subtitle \"$TODAY\" sound name \"Glass\""

# ── 邮件日报 ──
export SMTP_SERVER SMTP_PORT SMTP_USER SMTP_PASS EMAIL_TO

python3 "$SCRIPT_DIR/send-digest-email.py" \
    "data/cepm_latest.json" \
    "$SCAN_FROM" \
    "data/cepm_seen_dois.json" \
    "cepm" \
    >> "$LOG_FILE" 2>&1 || echo "Email sending failed" >> "$LOG_FILE"

# 自动打开 App
open "https://zylen97.github.io/idea-scout/"
