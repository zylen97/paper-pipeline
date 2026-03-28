---
name: latex-table
description: "Elsarticle表格模板与格式规范，创建或修改LaTeX表格时使用"
user-invocable: false
auto-invoke: true
---

# Elsarticle 表格规范

当用户要求创建、修改或格式化 LaTeX 表格时，遵循以下模板和规则。

## 输出位置

- **所有表格**统一写入 `structure/figures_tables/tables.tex`（追加到文件末尾）
- 每次创建/修改表格后，**必须同步更新** `structure/figures_tables/index.md` 的 Tables 表格
- 定稿时将 `tables.tex` 内容贴到 manuscript.tex 末尾

## 标准模板

```latex
\begin{table}[!htbp]
\centering
\captionsetup{font=normalsize, labelsep=period}
\setlength{\abovecaptionskip}{5pt}
\setlength{\belowcaptionskip}{0pt}
\caption{表格标题}
\label{tab:label_name}
\small
\begin{threeparttable}
\begin{tabular*}{0.9\textwidth}{@{\extracolsep{\fill}}lccccccc}
\toprule
\textbf{列标题1} & \textbf{列标题2} & ... \\
\midrule
\textit{变量1} & 数据 & ... \\
\textit{变量2} & 数据 & ... \\
\bottomrule
\end{tabular*}
\begin{tablenotes}[flushleft]
\small\linespread{1}\selectfont
\item \textit{Note}: 注释内容...
\end{tablenotes}
\end{threeparttable}
\end{table}
\vspace{-15pt}
```

## 核心规则

- 统一 `\small` 字体，**禁止** `\footnotesize`、`\Large` 等
- 表头 `\textbf{}`，第一列 `\textit{}`，数据列居中 `c`
- 宽度 `0.9\textwidth`，浮动 `[!htbp]`
- Caption 使用 `\captionsetup{font=normalsize, labelsep=period}`
- 必须包含 `threeparttable` + `tablenotes` 结构
