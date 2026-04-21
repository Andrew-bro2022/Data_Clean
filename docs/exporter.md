# `src/exporter.py`

## Purpose
Writes cleaned output CSV files and run-level Excel reports.

## Key Functions
- `save_cleaned(df, output_dir, raw_filename)`: writes cleaned CSV with original raw filename.
- `save_report_excel(results, reports_dir)`: writes one Excel report per run.

## Report Structure
Report filename:
- `report_YYYYMMDD_HHMMSS.xlsx`

Sheets:
- `file_summary`: one row per file, includes status, row counts, column differences, and errors.
- `column_stats`: one row per file-column with null counts and conversion issue counts.

## Dependencies
- Uses `openpyxl` engine via pandas ExcelWriter.
