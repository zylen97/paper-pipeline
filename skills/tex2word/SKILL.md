---
name: tex2word
description: 将 LaTeX 论文稿（elsarticle/article + natbib）转换为与编译 PDF 观感一致、正文可编辑的 Word 文档，供导师/合作者批注。pandoc + citeproc 管线：引用渲染为期刊样式文本、公式转 Word 原生公式、交叉引用按 .aux 真实编号回填；表格从编译 PDF 按区域裁成高清图嵌入（与 PDF 完全一致），图注自动补 "Figure N:" 编号，正文双倍行距无首行缩进。触发场景：用户要求"转 Word / 生成 docx / 发给导师看的版本"。
---

# tex2word — LaTeX 论文转 Word（PDF 还原版）

## 产出标准

| 元素 | 转换结果 |
|:-----|:---------|
| 标题 | Word Title 样式段落（来自 `\title{}`） |
| 摘要/关键词 | 正文段落（keyword 环境转 "Keywords: a; b; c"） |
| 引用 | citeproc 渲染为正文文本（默认 elsevier-harvard 样式）+ 文末排序 References 表 |
| 公式 | OMML（Word 原生可编辑公式） |
| 表格 | 从编译 PDF 按区域裁出的 300dpi 图（caption + 表体 + 表注一体，与 PDF 像素级一致），宽度按 PDF 相对宽度等比保留 |
| 图片 | 300dpi PNG 内嵌（由图源 PDF 转换），caption 自动补 "Figure N:" 编号（与 PDF 一致） |
| 交叉引用 | 从 `.aux` 回填真实编号（含附录 A/B/C、Table A.1 等） |
| 正文版式 | Times New Roman 12pt、双倍行距、**无首行缩进**（段落左对齐起笔） |

## 前置条件

1. **稿件已编译且 PDF/aux 新鲜**（表图从 PDF 裁、编号从 aux 读）。不确定先 `latexmk -pdf manuscript.tex`。
2. 工具：`pandoc`（≥3.x）、`pdftocairo`（poppler）、python3 + PyMuPDF（`import fitz`）。注意本机 `pdftotext -bbox` 会崩溃，表格坐标必须走 PyMuPDF。
3. CSL 样式：`~/Zotero/styles/` 下选与稿件 bibliographystyle 最接近的（apalike → `elsevier-harvard.csl` 或 `apa.csl`）。

## 第 0 步：bib 质量预检（影响 PDF 和 Word 双端，发现就修源头）

```bash
# 全大写期刊名（WoS 导出脏数据）——这是稿件级 bug，PDF 参考文献同样会全大写
grep -E "^\s*journal\s*=\s*\{[A-Z 0-9:&-]+\}" <主bib> | sort -u
```
发现后**直接修仓库 bib 源头**（逐本对照官方名做显式映射替换，不要算法 title-case——PLOS ONE 这类官方全大写名要保留），然后**重编译 PDF 再走管线**。这是唯一一个改仓库原件的步骤，因为它本质是投稿 bug。

## 执行步骤（全部在**项目根目录**运行，否则 `\input` 相对路径失效）

```bash
PROJ=<项目根>; cd "$PROJ"
SKILL=/Users/zylen/.claude/skills/tex2word/scripts
mkdir -p word_export/figures

# 1. 图源 PDF → 300dpi PNG（仅处理 \includegraphics 引用的图目录）
for f in <figures目录>/*.pdf; do
  pdftocairo -png -singlefile -r 300 "$f" "word_export/figures/$(basename "$f" .pdf)"
done

# 2. 清洗 bib 副本（弯引号 citation key 会让 pandoc 解析直接失败）
sed "s/’/'/g" <主bib文件> > word_export/bib_clean.bib

# 3. 从编译 PDF 裁出每张表为紧致 PNG（PyMuPDF）
#    自动识别 "Table N." / "Table X.Y." / "(continued)" caption，
#    按相邻 caption 切片 + 文本/表线矢量包围盒收紧，输出 table_<编号>.png
python3 "$SKILL/extract_tables.py" manuscript.pdf word_export/tables
# 裁完必须 Read 抽查 2 张 PNG：caption/表注完整、无相邻表串台

# 4. 预处理 tex（展开 \input、aux 回填 \ref、表格环境替换为表图、
#    图 caption 补 "Figure N:" 编号、剥 adjustbox/landscape/resizebox 壳、
#    keyword 环境转段落、附录节转 "Appendix X." 无编号节、提取标题）
TITLE=$(python3 "$SKILL/preprocess.py" manuscript.tex word_export/manuscript_for_word.tex word_export/tables)

# 5. pandoc 转换（filter 顺序重要：fix_images 在 citeproc 前，refs 标题在后）
pandoc word_export/manuscript_for_word.tex -f latex -t docx \
  --citeproc --bibliography=word_export/bib_clean.bib \
  --csl="$HOME/Zotero/styles/elsevier-harvard.csl" \
  --lua-filter="$SKILL/fix_images.lua" \
  --lua-filter="$SKILL/add_refs_heading.lua" \
  --metadata title="$TITLE" \
  --number-sections \
  --reference-doc="$SKILL/reference_pdfstyle.docx" \
  -o <项目编号>_manuscript_word.docx
```

注意：`fix_images.lua` 假定 PNG 在 `word_export/figures/`，若图不在该约定路径需先改 filter。

## 验收（必做，不要只看文件生成就报成功）

```bash
python3 -c "
from zipfile import ZipFile
z = ZipFile('<输出>.docx')
doc = z.read('word/document.xml').decode('utf8')
styles = z.read('word/styles.xml').decode('utf8')
print('native tables:', doc.count('<w:tbl>'))   # 应为 0（表全部是图）
print('images:', doc.count('<pic:pic'))          # 应 = 图数 + 表图数（含 _cont 续页）
print('equations:', doc.count('<m:oMath'))       # >0（仅正文行内公式，表内公式已随图走）
print('fig numbered:', all('Figure %d:' % i in doc for i in range(1, <图数>+1)))
print('title:', '<标题前几词>' in doc)
print('refs:', '>References<' in doc)
print('no indent:', 'w:firstLine=\"317\"' not in styles)
print('double spacing:', 'w:line=\"480\"' in styles)
"
# plain 回读抽查：Keywords 行、Appendix A/B/C 节名、正文 'Table 2'/'Fig. 4' 编号为字面数字、
# References 条目期刊名无全大写
pandoc <输出>.docx -t plain --wrap=none | grep -nE "^Keywords:|^References$|^Appendix [A-Z]"
pandoc <输出>.docx -t plain --wrap=none | grep -E "^[A-Z][a-z]+.*[0-9]{4}\." | grep -E "[A-Z]{8,}" | head  # 残留全大写
```

## 已知坑（按踩坑顺序）

1. **bib 弯引号**：citation key 含 `'`（U+2019）→ pandoc 解析整库失败，报 `unexpected '\8217'`。sed 清洗副本。
2. **adjustbox/landscape/resizebox 包裹的表**：pandoc 不认识环境会**静默吞掉整张表**（表转图模式下无此风险，但 preprocess 仍剥壳兜底）。
3. **`\ref` 编号漂移**：pandoc 自己按解析顺序编号，一旦有元素丢失全文编号错位，附录也不会用 A/B/C。必须用 `.aux` 的 `\newlabel` 回填字面编号（preprocess.py 已做）。
4. **elsarticle frontmatter**：`\title` 不进正文（用 `--metadata title` 补）；`keyword` 环境内容会裸泄为无标签文本（preprocess.py 转成 "Keywords:" 段落）。
5. **References 无标题**：citeproc 只生成条目不生成标题，`add_refs_heading.lua` 在 `#refs` div 前插入无编号 References 节（**必须放在 --citeproc 之后**）。
6. **运行目录**：pandoc 解析 `\input` 相对当前目录，必须在项目根运行；在子目录运行只会报 WARNING 然后产出一个缺了所有图表的"成功"文件。
7. **图 caption 无编号**：pandoc 只输出 caption 文本，不带 "Figure N:" 前缀。preprocess.py 按 aux 编号在 caption 里预置（格式对齐编译 PDF 的 "Figure 1: xxx"）。
8. **首行缩进幽灵**：pandoc 默认 reference docx 的 **Normal 样式自带 `w:firstLine="317"`**（不在 docDefaults 里，藏在样式层）。`reference_pdfstyle.docx` 已清零；自建 reference 时务必检查 Normal 的 `w:ind`。
9. **表跨页（longtable continued）**：续页单独裁为 `table_N_cont.png`，preprocess 会把两张图先后插入同一位置。
10. **期刊名全大写**：见第 0 步，修源头并重编译，不要只修 Word 端。
11. **横版页（pdflscape，rotation=90）坐标系陷阱**：PyMuPDF 的 `get_text`/`get_drawings` 返回**未旋转坐标**，而 `page.rect`/`get_pixmap` 用**旋转后显示坐标**——混用会把横版表裁掉一半且不报错。extract_tables.py 已统一用 `page.rotation_matrix` 把所有文本/表线 rect 变换到显示空间再切片；横版页的页码会旋转落在页侧，按"页边 60pt 内的孤立纯数字"过滤。**验收时必须 Read 抽查横版表的 PNG**。

## 局限（提前告知用户）

- 双栏/精确分页/行号（lineno）不保留——产出目标是**正文可编辑、图表与 PDF 一致**的批注版 Word。
- 表格和图均为位图：导师改不了表内数字和图内文字（要改回 LaTeX/数据脚本改，改完重跑本管线）。
- 表内行内公式随图走，docx 公式计数只剩正文部分，验收时不要误判为丢失。
