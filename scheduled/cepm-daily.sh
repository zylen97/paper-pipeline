#!/bin/bash
# CE/PM Daily Scan — 每天 9:10 自动扫描建工/PM期刊最近5天新论文
# 由 launchd 触发，通过独立 Python 脚本执行扫描

# ── 文件锁（防止睡眠唤醒后多脚本同时操作 git） ──
LOCKDIR="/tmp/idea_scout_git.lock"
while ! mkdir "$LOCKDIR" 2>/dev/null; do
    sleep 10
done
trap 'rmdir "$LOCKDIR" 2>/dev/null' EXIT

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

# ── 同步 App 端最新 user_state（App 通过 GitHub API 写入 gh-pages） ──
git fetch origin gh-pages --quiet 2>> "$LOG_FILE"
git show origin/gh-pages:data/user_state.json > /tmp/idea_scout_user_state.json 2>/dev/null \
    || cp data/user_state.json /tmp/idea_scout_user_state.json 2>/dev/null

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

# 加载 user_state.json，过滤已删除/已加入 Idea 的论文
deleted_dois = set()
try:
    with open('/tmp/idea_scout_user_state.json', 'r') as f:
        _us = json.load(f)
    deleted_dois = set(_us.get('cepm', {}).get('deleted_dois', []))
    for ip in _us.get('cepm', {}).get('idea_papers', []):
        tid = ip.get('tracking_id', ip.get('doi', ''))
        if tid: deleted_dois.add(tid)
except (FileNotFoundError, json.JSONDecodeError):
    pass

all_papers = [p for doi, p in doi_map.items() if doi not in deleted_dois]

from datetime import datetime, timedelta
cutoff = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
all_papers = [p for p in all_papers if p.get('scan_date', p.get('date', '9999')) >= cutoff]
all_papers.sort(key=lambda p: p.get('date', ''), reverse=True)

with open(papers_path, 'w') as f:
    json.dump(all_papers, f, ensure_ascii=False)

print(f"Merged: {len(new_papers)} fetched, {len(all_papers)} total")
PYEOF

echo "Merge done" >> "$LOG_FILE"

# ── 统计去重后真实新论文数 ──
NEW_COUNT=$(python3 -c "
import json
papers = json.load(open('data/cepm_latest.json'))
if isinstance(papers, dict) and 'papers' in papers: papers = papers['papers']
try: seen = set(json.load(open('data/cepm_seen_dois.json')))
except: seen = set()
new = [p for p in papers if not p.get('doi') or p['doi'] not in seen]
print(len(new))
" 2>/dev/null || echo "0")
echo "New papers (after dedup): $NEW_COUNT" >> "$LOG_FILE"

# ── 邮件日报（在 git push 之前，避免 push 卡死阻塞邮件） ──
export SMTP_SERVER SMTP_PORT SMTP_USER SMTP_PASS
export EMAIL_TO="$EMAIL_TO,zhangshfan@mail.usts.edu.cn"

python3 "$SCRIPT_DIR/send-digest-email.py" \
    "data/cepm_latest.json" \
    "$SCAN_FROM" \
    "data/cepm_seen_dois.json" \
    "cepm" \
    >> "$LOG_FILE" 2>&1 || echo "Email sending failed" >> "$LOG_FILE"

# ── 通知 + 打开 App（仅有新论文时） ──
if [ "$NEW_COUNT" -gt 0 ] 2>/dev/null; then
    osascript -e "display notification \"CE/PM: ${NEW_COUNT} 篇新论文\" with title \"CE/PM Scout\" subtitle \"$TODAY\" sound name \"Glass\""
    open "https://zylen97.github.io/idea-scout/"
fi

# ── 推送到 GitHub + 部署 gh-pages（带超时保护） ──
git add data/cepm_latest.json data/cepm_papers.json data/cepm_seen_dois.json
git commit -m "cepm: $TODAY - scan from $SCAN_FROM" 2>> "$LOG_FILE"

PUSH_OK=0
for _attempt in 1 2 3; do
    perl -e 'alarm 60; exec @ARGV' git push origin main >> "$LOG_FILE" 2>&1 && { PUSH_OK=1; break; }
    sleep 5
done
if [ $PUSH_OK -eq 0 ]; then
    echo "ERROR: git push main failed after 3 attempts" >> "$LOG_FILE"
    osascript -e 'display notification "git push main 超时/失败，数据未同步" with title "CE/PM Scout" subtitle "Push Failed" sound name "Basso"'
fi

# 部署到 gh-pages
mkdir -p /tmp/idea_scout_all_data
cp data/*.json /tmp/idea_scout_all_data/
git checkout gh-pages 2>> "$LOG_FILE"
cp /tmp/idea_scout_all_data/*.json data/
git add data/
git commit -m "data: cepm $TODAY" 2>> "$LOG_FILE"

PUSH_OK=0
for _attempt in 1 2 3; do
    perl -e 'alarm 60; exec @ARGV' git push origin gh-pages >> "$LOG_FILE" 2>&1 && { PUSH_OK=1; break; }
    sleep 5
done
if [ $PUSH_OK -eq 0 ]; then
    echo "ERROR: git push gh-pages failed after 3 attempts" >> "$LOG_FILE"
    osascript -e 'display notification "gh-pages push 超时/失败，App 未更新" with title "CE/PM Scout" subtitle "Push Failed" sound name "Basso"'
fi

git checkout main 2>> "$LOG_FILE"
rm -rf /tmp/idea_scout_all_data

echo "GitHub push done" >> "$LOG_FILE"
