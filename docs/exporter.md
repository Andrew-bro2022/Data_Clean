# `src/exporter.py`

## Purpose
Writes cleaned output CSV files and run-level Excel reports.

## Key Functions
- `save_cleaned(df, output_csv_path, column_rules=None)`: writes cleaned CSV. Date/datetime columns use each rule's `date_format` when `column_rules` is provided; otherwise `to_csv` uses default `%Y-%m-%d` for any remaining datetime columns.
- `save_report_excel(results, reports_dir)`: writes one Excel report per run.

## Report Structure
Report filename:
- `report_YYYYMMDD_HHMMSS.xlsx`

Sheets:
- `file_summary`: one row per file, includes status, row counts, column differences, and errors.
- `column_stats`: one row per file-column with null counts and conversion issue counts.

## Dependencies
- Uses `openpyxl` engine via pandas ExcelWriter.
