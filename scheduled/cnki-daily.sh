#!/bin/bash
# CNKI Daily Scan — 每天 9:20 自动扫描中文期刊最新论文
# 由 launchd 触发，通过 CNKI RSS 抓取

# ── 文件锁（防止睡眠唤醒后多脚本同时操作 git） ──
LOCKDIR="/tmp/idea_scout_git.lock"
while ! mkdir "$LOCKDIR" 2>/dev/null; do
    sleep 10
done
trap 'rmdir "$LOCKDIR" 2>/dev/null' EXIT

LOG_DIR="$HOME/.claude/scheduled/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/cnki-$(date +%Y%m%d-%H%M%S).log"
TODAY=$(date +%Y-%m-%d)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# 设置 PATH
export PATH="$HOME/.local/bin:$HOME/develop/flutter/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

# 加载配置（CNKI 不需要翻译 API，只用 SMTP 发邮件）
source "$SCRIPT_DIR/email-config.sh"

echo "=== CNKI Daily Scan ===" >> "$LOG_FILE"
echo "Started: $(date)" >> "$LOG_FILE"

# 在 idea_scout 仓库目录下运行
cd "$HOME/idea_scout" || {
    echo "ERROR: ~/idea_scout not found" >> "$LOG_FILE"
    osascript -e 'display notification "idea_scout dir not found" with title "CNKI Scout" subtitle "Failed" sound name "Basso"'
    exit 1
}

# ── 扫描（CNKI RSS） ──
python3 "$SCRIPT_DIR/cnki-scan.py" \
    --config "$SCRIPT_DIR/cnki-journals.json" \
    --output "data/cnki_latest.json" \
    --days 30 \
    >> "$LOG_FILE" 2>&1

EXIT_CODE=$?
echo "Scan finished: $(date), exit code: $EXIT_CODE" >> "$LOG_FILE"

if [ $EXIT_CODE -ne 0 ] || [ ! -s "data/cnki_latest.json" ]; then
    echo "Scan failed, aborting" >> "$LOG_FILE"
    osascript -e 'display notification "CNKI scan failed, check logs" with title "CNKI Scout" subtitle "Failed" sound name "Basso"'
    exit 1
fi

# ── 统计去重后真实新论文数 ──
NEW_COUNT=$(python3 -c "
import json
papers = json.load(open('data/cnki_latest.json'))
if isinstance(papers, dict) and 'papers' in papers: papers = papers['papers']
try: seen = set(json.load(open('data/cnki_seen_titles.json')))
except: seen = set()
new = [p for p in papers if p.get('title') and p['title'] not in seen]
print(len(new))
" 2>/dev/null || echo "0")
echo "New papers (after dedup): $NEW_COUNT" >> "$LOG_FILE"

# ── 邮件推送（CNKI 只发给自己） ──
export SMTP_SERVER SMTP_PORT SMTP_USER SMTP_PASS
export EMAIL_TO="$SMTP_USER"

python3 "$SCRIPT_DIR/send-cnki-email.py" \
    "data/cnki_latest.json" \
    "$TODAY" \
    "data/cnki_seen_titles.json" \
    >> "$LOG_FILE" 2>&1 || echo "Email sending failed" >> "$LOG_FILE"

# ── 通知 + 打开 App（仅有新论文时） ──
if [ "$NEW_COUNT" -gt 0 ] 2>/dev/null; then
    osascript -e "display notification \"CNKI: ${NEW_COUNT} 篇新论文\" with title \"CNKI Scout\" subtitle \"$TODAY\" sound name \"Glass\""
    open "https://zylen97.github.io/idea-scout/"
fi

# ── 推送到 GitHub + 部署 gh-pages（带超时保护） ──
git add data/cnki_latest.json data/cnki_seen_titles.json
git commit -m "cnki: $TODAY" 2>> "$LOG_FILE"

PUSH_OK=0
for _attempt in 1 2 3; do
    perl -e 'alarm 60; exec @ARGV' git push origin main >> "$LOG_FILE" 2>&1 && { PUSH_OK=1; break; }
    sleep 5
done
if [ $PUSH_OK -eq 0 ]; then
    echo "ERROR: git push main failed after 3 attempts" >> "$LOG_FILE"
    osascript -e 'display notification "git push main 超时/失败，数据未同步" with title "CNKI Scout" subtitle "Push Failed" sound name "Basso"'
fi

# 部署到 gh-pages
mkdir -p /tmp/idea_scout_all_data
cp data/*.json /tmp/idea_scout_all_data/
git checkout gh-pages 2>> "$LOG_FILE"
cp /tmp/idea_scout_all_data/*.json data/
git add data/
git commit -m "data: cnki $TODAY" 2>> "$LOG_FILE"

PUSH_OK=0
for _attempt in 1 2 3; do
    perl -e 'alarm 60; exec @ARGV' git push origin gh-pages >> "$LOG_FILE" 2>&1 && { PUSH_OK=1; break; }
    sleep 5
done
if [ $PUSH_OK -eq 0 ]; then
    echo "ERROR: git push gh-pages failed after 3 attempts" >> "$LOG_FILE"
    osascript -e 'display notification "gh-pages push 超时/失败，App 未更新" with title "CNKI Scout" subtitle "Push Failed" sound name "Basso"'
fi

git checkout main 2>> "$LOG_FILE"
rm -rf /tmp/idea_scout_all_data

echo "GitHub push done" >> "$LOG_FILE"

# 清理 30 天前的旧日志
find "$LOG_DIR" -name "cnki-*.log" -mtime +30 -delete 2>/dev/null

echo "Done: $(date)" >> "$LOG_FILE"
