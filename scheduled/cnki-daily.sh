#!/bin/bash
# CNKI Daily Scan — 每天 9:10 自动扫描中文期刊最新论文
# 由 launchd 触发，通过 CNKI RSS 抓取

LOG_DIR="$HOME/.claude/scheduled/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/cnki-$(date +%Y%m%d-%H%M%S).log"
TODAY=$(date +%Y-%m-%d)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# 设置 PATH
export PATH="$HOME/.local/bin:$HOME/develop/flutter/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

# 加载配置
source "$SCRIPT_DIR/email-config.sh"
export CHATANYWHERE_API_KEY

echo "=== CNKI Daily Scan ===" >> "$LOG_FILE"
echo "Started: $(date)" >> "$LOG_FILE"

# 在 idea_scout 仓库目录下运行
cd "$HOME/idea_scout" || {
    echo "ERROR: ~/idea_scout not found" >> "$LOG_FILE"
    osascript -e 'display notification "idea_scout dir not found" with title "CNKI Scout" subtitle "Failed" sound name "Basso"'
    exit 1
}

# ── 扫描（CNKI RSS + 翻译标题） ──
python3 "$SCRIPT_DIR/cnki-scan.py" \
    --config "$SCRIPT_DIR/cnki-journals.json" \
    --output "data/cnki_latest.json" \
    --days 7 \
    --translate \
    >> "$LOG_FILE" 2>&1

EXIT_CODE=$?
echo "Scan finished: $(date), exit code: $EXIT_CODE" >> "$LOG_FILE"

if [ $EXIT_CODE -ne 0 ] || [ ! -s "data/cnki_latest.json" ]; then
    echo "Scan failed, aborting" >> "$LOG_FILE"
    osascript -e 'display notification "CNKI scan failed, check logs" with title "CNKI Scout" subtitle "Failed" sound name "Basso"'
    exit 1
fi

# ── 邮件推送 ──
# CNKI 用独立的 seen_dois (基于 title 去重，因为中文论文没有 DOI)
export SMTP_SERVER SMTP_PORT SMTP_USER SMTP_PASS EMAIL_TO

python3 "$SCRIPT_DIR/send-cnki-email.py" \
    "data/cnki_latest.json" \
    "$TODAY" \
    "data/cnki_seen_titles.json" \
    >> "$LOG_FILE" 2>&1 || echo "Email sending failed" >> "$LOG_FILE"

# ── 通知 ──
osascript -e "display notification \"CNKI scan done\" with title \"CNKI Scout\" subtitle \"$TODAY\" sound name \"Glass\""

echo "Done: $(date)" >> "$LOG_FILE"
