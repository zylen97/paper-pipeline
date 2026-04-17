---
name: latex-table
description: "LaTeX 表格模板与格式规范：项目类型自适应输出路径 + caption 宏包预检 + label 防冲突"
user-invocable: true
auto-invoke: true
---

# LaTeX 表格规范

当用户要求创建、修改或格式化 LaTeX 表格时，遵循以下模板和规则。

## 输出位置（按项目类型分流）

Step 0 — 项目类型探测 + 确定 `{TABLES_FILE}`：

| 项目类型（按 `$PWD` 探测） | `{TABLES_FILE}` |
|:---|:---|
| `papers/` / `_gym paper/`（英文小论文） | `structure/figures_tables/tables.tex` |
| `dissertations/`（学位论文） | `structure/figures_tables/tables_{章号}.tex`（按章分文件，避免所有表堆在一起） |
| `fundings/`（基金） | `structure/figures_tables/tables.tex` |
| `$PWD` 不在上述目录 | AskUserQuestion 确认路径，不默认写入 |

- 每次创建/修改表格后，**必须同步更新** `structure/figures_tables/index.md` 的 Tables 表格（不存在则 mkdir + touch）
- 定稿时（/finalize）将 `tables.tex` 内容贴到 manuscript.tex 末尾

## Step 1 — Caption 宏包预检（写入前必做）

扫描主 tex 文件的 preamble，检查是否加载了 `caption` 宏包：

```bash
grep -E '\\usepackage(\[[^\]]*\])?\{caption\}' main.tex  # 或 manuscript.tex
```

- ✅ 命中 → 继续
- ❌ 未命中：
  - 如果 documentclass 是 `elsarticle / sagej / WileyNJDv5 / ctexart` → 通常 cls 自带，可继续
  - 其他（如 `article / IEEEtran / ASCE` 的某些 cls）→ 🟡 告警："`caption` 宏包未加载，`\captionsetup{}` 会编译失败。建议在 preamble 添加 `\usepackage{caption}`，或改用不含 `\captionsetup` 的简化模板"；让用户选择 (1) 添加宏包 (2) 用简化模板 (3) 继续（自行承担风险）

## Step 2 — Label 冲突检查（写入前必做）

扫描 `{TABLES_FILE}` 已有的 `\label{tab:XXX}`，若新表的 label 已存在：
- 🔴 阻断，报告冲突："已存在 `\label{tab:xxx}`（第 N 行）。请选择：(1) 覆盖原表 (2) 改名（如 `tab:xxx_v2`）(3) 取消"
- 禁止静默追加导致 LaTeX 编译警告 `multiply defined labels`

## 标准模板（完整版，适用于支持 caption + threeparttable 的项目）

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

## 简化模板（当 caption/threeparttable 不可用时的降级）

```latex
\begin{table}[!htbp]
\centering
\caption{表格标题}
\label{tab:label_name}
\small
\begin{tabular}{lccccc}
\toprule
\textbf{列标题1} & \textbf{列标题2} & ... \\
\midrule
\textit{变量1} & 数据 & ... \\
\bottomrule
\end{tabular}
\begin{flushleft}
\small \textit{Note}: 注释内容...
\end{flushleft}
\end{table}
```

## 核心规则

- 统一 `\small` 字体，**禁止** `\footnotesize`、`\Large` 等
- 表头 `\textbf{}`，第一列 `\textit{}`，数据列居中 `c`
- 宽度 `0.9\textwidth`，浮动 `[!htbp]`
- Caption 使用 `\captionsetup{font=normalsize, labelsep=period}`（若 caption 可用）
- 必须包含 `threeparttable` + `tablenotes` 结构（若可用）
- **Label 命名约定**：`tab:{chapter}_{semantic}` 或 `tab:{section}_{semantic}`，避免纯数字命名冲突
