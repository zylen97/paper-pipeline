#!/bin/bash
# Figure Harvest — 单期刊采集脚本（CDN 直下版）
# Usage: bash harvest.sh <journal_slug> <journal_id> <dir_name> <output_base>
# Example: bash harvest.sh automation-in-construction AIC Automation_in_Construction ~/Library/CloudStorage/Dropbox/02-Research/Zylen\ paper/figure_harvest
#
# 策略：CDP 只用于获取论文列表（1次页面访问），图片全部通过 CDN 直下
# CDN URL 模式: https://ars.els-cdn.com/content/image/1-s2.0-{PII}-{ga1|grN}_lrg.jpg

set -euo pipefail

SLUG="$1"
JID="$2"
DIR_NAME="$3"
OUTBASE="$4"
PROXY="http://localhost:3456"

echo "=== [$JID] 开始采集: $SLUG ==="

# ─── 1. CDP: 获取最新卷期论文列表 ───────────────────────

# 打开期刊 All Issues 页面
RESULT=$(curl -s "$PROXY/new?url=https://www.sciencedirect.com/journal/${SLUG}/issues")
TID=$(echo "$RESULT" | python3 -c "import sys,json;print(json.load(sys.stdin).get('targetId',''))" 2>/dev/null)
if [ -z "$TID" ]; then
  echo "ERROR: 无法打开期刊页面"
  exit 1
fi
sleep 4

# 找到最新卷期并点击
VOL_INFO=$(curl -s -X POST "$PROXY/eval?target=$TID" -d '
(function() {
  // 找最新卷期链接
  var volLinks = document.querySelectorAll("a[href*=\"/vol/\"]");
  if (volLinks.length === 0) {
    // 尝试其他选择器
    volLinks = document.querySelectorAll("a[href*=\"/journal/\"][href*=\"vol\"]");
  }
  if (volLinks.length > 0) {
    var first = volLinks[0];
    var text = first.textContent.trim();
    var href = first.href;
    first.click();
    return JSON.stringify({volume: text, href: href, found: true});
  }
  return JSON.stringify({found: false, html: document.body.innerText.substring(0,300)});
})()
')
echo "[$JID] 卷期信息: $(echo "$VOL_INFO" | python3 -c "import sys,json;d=json.loads(json.load(sys.stdin)['value']);print(d.get('volume','unknown'))" 2>/dev/null)"

sleep 4

# 提取论文列表
ARTICLES_JSON=$(curl -s -X POST "$PROXY/eval?target=$TID" -d '
(function() {
  // 卷期标签
  var volText = "";
  var candidates = document.querySelectorAll("h2, h3, .text-s, .u-clr-grey8, title");
  for (var i = 0; i < candidates.length; i++) {
    var t = candidates[i].textContent.trim();
    if (t.match(/[Vv]ol/) && t.match(/\d+/)) { volText = t; break; }
  }
  if (!volText) volText = document.title;

  // 论文链接
  var links = document.querySelectorAll("a[href*=\"/science/article/pii/\"]");
  var seen = {};
  var articles = [];
  for (var j = 0; j < links.length; j++) {
    var text = links[j].textContent.trim();
    var href = links[j].href;
    if (text.length < 20 || text === "View PDF" || text === "Download PDF") continue;
    var m = href.match(/pii\/([A-Z0-9]+)/);
    if (!m || seen[m[1]]) continue;
    seen[m[1]] = true;
    articles.push({pii: m[1], title: text});
  }
  return JSON.stringify({volume: volText, articles: articles});
})()
')

# 关闭 tab
curl -s "$PROXY/close?target=$TID" > /dev/null

# 解析结果
python3 -c "
import sys, json, re
raw = json.load(sys.stdin)
data = json.loads(raw['value'])
vol = data['volume']
m = re.search(r'[Vv]ol(?:ume)?\.?\s*(\d+)', vol)
vol_num = m.group(1) if m else 'unknown'
m2 = re.search(r'((?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4})', vol)
date_str = m2.group(1).replace(' ', '_') if m2 else '2026'
vol_label = f'Vol{vol_num}_{date_str}'
print(vol_label)

stop = {'a','an','the','of','in','on','for','and','or','to','with','by','from','at','is','are','was','were','be','been','its','their','this','that','these','those','as','it','not','but','into','through','between','among','using','based','via','towards','toward'}
for a in data['articles']:
    words = re.findall(r'[A-Za-z]+', a['title'])
    meaningful = [w.lower() for w in words if w.lower() not in stop][:4]
    short = '_'.join(meaningful)[:40]
    print(f'{a[\"pii\"]}|{short}')
" <<< "$ARTICLES_JSON" > /tmp/harvest_${JID}.txt

VOL_LABEL=$(head -1 /tmp/harvest_${JID}.txt)
ARTICLE_COUNT=$(tail -n +2 /tmp/harvest_${JID}.txt | wc -l | tr -d ' ')

echo "[$JID] 卷期: $VOL_LABEL, 论文数: $ARTICLE_COUNT"

if [ "$ARTICLE_COUNT" = "0" ]; then
  echo "[$JID] 未找到论文，跳过"
  exit 0
fi

# ─── 2. CDN 直下: 批量下载图片 ──────────────────────────

OUTDIR="$OUTBASE/$DIR_NAME/$VOL_LABEL"
mkdir -p "$OUTDIR"

TOTAL_FIGS=0
NUM=0

tail -n +2 /tmp/harvest_${JID}.txt | while IFS='|' read -r PII SHORT; do
  NUM=$((NUM + 1))
  PADNUM=$(printf "%02d" $NUM)
  PAPER_DIR="$OUTDIR/paper${PADNUM}_${SHORT}"
  mkdir -p "$PAPER_DIR"

  BASE="https://ars.els-cdn.com/content/image/1-s2.0-${PII}"
  FCOUNT=0

  # GA (graphical abstract)
  curl -s -L -o "$PAPER_DIR/ga1.jpg" "${BASE}-ga1_lrg.jpg"
  FSIZE=$(stat -f%z "$PAPER_DIR/ga1.jpg" 2>/dev/null || echo "0")
  if [ "$FSIZE" -lt 1024 ]; then
    curl -s -L -o "$PAPER_DIR/ga1.jpg" "${BASE}-ga1.jpg"
    FSIZE=$(stat -f%z "$PAPER_DIR/ga1.jpg" 2>/dev/null || echo "0")
  fi
  [ "$FSIZE" -lt 1024 ] && rm -f "$PAPER_DIR/ga1.jpg" || FCOUNT=$((FCOUNT + 1))

  # gr1 ~ gr30
  MISS=0
  for i in $(seq 1 30); do
    curl -s -L -o "$PAPER_DIR/gr${i}.jpg" "${BASE}-gr${i}_lrg.jpg"
    FSIZE=$(stat -f%z "$PAPER_DIR/gr${i}.jpg" 2>/dev/null || echo "0")
    if [ "$FSIZE" -lt 1024 ]; then
      curl -s -L -o "$PAPER_DIR/gr${i}.jpg" "${BASE}-gr${i}.jpg"
      FSIZE=$(stat -f%z "$PAPER_DIR/gr${i}.jpg" 2>/dev/null || echo "0")
    fi
    if [ "$FSIZE" -lt 1024 ]; then
      rm -f "$PAPER_DIR/gr${i}.jpg"
      MISS=$((MISS + 1))
      [ "$MISS" -ge 3 ] && break
    else
      FCOUNT=$((FCOUNT + 1))
      MISS=0
    fi
  done

  if [ "$FCOUNT" -eq 0 ]; then
    echo "  [$PADNUM] $SHORT — 无图片"
    rmdir "$PAPER_DIR" 2>/dev/null || true
  else
    echo "  [$PADNUM] $SHORT — $FCOUNT 张图片"
    TOTAL_FIGS=$((TOTAL_FIGS + FCOUNT))
  fi
done

echo ""
echo "=== [$JID] 采集完成: $VOL_LABEL ==="
echo "RESULT:$JID|$VOL_LABEL|$ARTICLE_COUNT|$TOTAL_FIGS|$OUTDIR"
