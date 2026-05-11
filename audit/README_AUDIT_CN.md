# 预清洗数据 audit

在主清洗流水线 **之前** 单独运行的步骤。扫描 `raw/` 下的 CSV（单层目录深度），在适用时按 `config/file_rules.yaml` 校验，并在 **`audit/output/`** 下写入 **一份** 带时间戳的 Excel（例如 `audit/output/audit_YYYYMMDD_HHMMSS.xlsx`）。

## 前置条件

- 必须存在 `config/file_rules.yaml`，否则 audit 无法运行。
- 若 raw 路径 **未匹配到任何规则**，仍会执行 **文件级** 检查（读入错误、尾部 phantom、合计关键字等），但 **不会** 对该文件套用标准列名、日期格式或数值列规则。

## 如何运行

在仓库根目录：

```text
python -m audit.main --base-dir .
```

### 命令行选项

| 选项 | 说明 |
|------|------|
| `--base-dir PATH` | 项目根目录（默认：当前工作目录）。 |
| `--file RELATIVE_PATH` | 只 audit 一个文件；路径在 `--base-dir` 下解析，且必须在 `raw/` 下。 |
| `--max-data-rows N` | 检测到表头后，最多只分析 **N** 行数据（日期、数值、引号等）。Phantom 与合计关键字扫描使用 **同一** 行窗口；超大文件尾部行为可能与全文件读取不同。不传则扫描全部数据行。 |

## 报表结构

### 工作表：`file_summary`

每个被 audit 的文件一行：匹配到的规则（若有）、表头行索引、`missing_columns` / `extra_columns`（与清洗器语义一致）、行数、抽样说明、读入错误、汇总状态。

汇总列（便于在 Excel 中筛选）：

- `standard_n_columns` / `raw_n_columns` — 列数（YAML 标准宽度 vs 解析得到的 raw 表头宽度）。
- `column_count_match` / `column_order_match` — `Y`/`N`（不适用时为空，例如未找到表头）。
- `column_order_first_mismatch_1based` — raw 表头与标准列顺序 **从左到右逐位** 比较时，**第一个** 不一致位置的 1-based 索引；若列数不同但前 `min(n)` 个名称一致，则第一处差异在 `min(n)+1`（多余尾部或缺失尾部）。
- `column_order_mismatch_expected` / `column_order_mismatch_found` — 该位置期望与实际的列名（或占位说明）。完整句式见 `issues_detail` 中的 `COLUMN_LAYOUT` 行。

- `date_issue_columns` — 在 `issues_detail` 中至少有一条 `DATE` 问题的列名，逗号分隔、去重排序。
- `numeric_issue_columns` — 同上，针对 `NUMERIC`（引号、`$`、按实现做的数值检查）。
- `phantom_issue` / `total_keyword_issue` — 对应文件级检查触发时为 `Y`（这些检查通常在 detail 里没有 `column`）。

`categories` 仍为紧凑的 `类别:数量`；逐行明细、消息与样本行号见 **`issues_detail`**。

### 工作表：`issues_detail`

所有发现汇总为一张表：严重程度、类别、列（若有）、行号（适用时为 audited dataframe 中的 1-based 行）、样本值、消息。

## 检查内容概览

| 范围 | 行为 |
|------|------|
| **Structure** | 表头检测及列集合与 YAML `columns` 对比，逻辑与清洗流水线一致。 |
| **Dates** | 日期列按规则中的 `date_format` **严格** 解析（与清洗后期望的 `YYYY-MM-DD` 形态对齐）。 |
| **Numbers** | 接受美加千分位（如 `1,234.56`）。其它无法解析为数值的会标记。双引号包裹的数值外观 → 警告；引号内带千分位逗号（如 `"1,234"`）→ 升级上报。数值列中含 `$` → 警告。 |
| **Phantom rows** | 数据 **底部** 连续多行大多为空白或逗号填充（阈值见 `audit/constants.py`）。 |
| **Total-like rows** | 在数据 **末尾一段行** 内扫描 `Total`、`Grand Total`、`SUM` 等关键字（见 `TAIL_KEYWORD_SCAN_ROWS`）。 |

灵敏度可在 `audit/constants.py` 中调整。

## 大文件

数百 MB 量级可传 `--max-data-rows` 限制分析行数；摘要表中会体现抽样。需要完整文件尾部行为时再 **不传** 该参数重跑。

## 回归夹具（`raw/_audit_fixtures/`）

合成 CSV/XLSX 用于覆盖结构、日期、数值引号/货币、phantom、合计、未匹配规则、跳过 xlsx、表头检测失败、多列 missing/extra 等场景。路径在 `config/file_rules.yaml` 的 `mappings` 中绑定。修改夹具逻辑后可重新生成：

```text
python -m audit.generate_test_raw_fixtures
```

说明：主清洗流水线 **有意跳过** `raw/_audit_fixtures/`，避免回归夹具污染生产跑批结果。
