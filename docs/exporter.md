# `src/exporter.py`

## Purpose
Writes cleaned output CSV files and run-level Excel reports.

## Key Functions
- `save_cleaned(df, output_csv_path, column_rules=None)`: writes cleaned CSV.
  - Date columns: formatted with each rule's `date_format` (default `%Y-%m-%d`).
  - Numeric columns: `_format_cell_for_csv` — no scientific notation for floats; scientific literals kept as strings.
- `save_report_excel(results, reports_dir)`: writes one Excel report per run.

## Report Structure
Report filename: `report_YYYYMMDD_HHMMSS.xlsx`

Sheets (5):

| Sheet | Contents |
|-------|----------|
| `file_summary` | Status, `output_written`, `layout_status`, `clean_status`, `status_reason`, row counts, paths |
| `issues_detail` | Phase, category, severity, column, message, sample rows |
| `clean_actions` | File-level placeholder / `$` / parens / comma / blank-row counts |
| `clean_actions_by_column` | Same metrics per column |
| `column_stats` | Nulls, type issues, scientific notation, date parse breakdown per column |

## Dependencies
- `openpyxl` via pandas `ExcelWriter`

See [clean_pipeline.md](clean_pipeline.md) for how to read the report.
