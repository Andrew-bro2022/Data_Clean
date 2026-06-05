# `audit/reporter.py`

## Role

Turns a list of **`FileAuditResult`** into one Excel workbook for stakeholders.

## Key functions

- **`write_audit_excel(results, output_path)`**  
  - Sheet **`file_summary`**: one row per file — match, header index, row/column counts, `missing_columns` / `extra_columns` (joined strings), layout flags (`column_count_match` / `column_order_match` as `Y`/`N`/blank), issue counts, **`date_issue_columns`** / **`numeric_issue_columns`** / **`placeholder_issue_columns`** (distinct columns with issues in that category), phantom/total flags, **`read_error`**.  
  - Sheet **`issues_detail`**: one row per issue dict (category, severity, column, message, count, sample rows).

- **`default_audit_path(base_dir)`** — under `audit/output/`, timestamped filename.

## Helpers

- **`_yn_or_blank`**, **`_sorted_issue_columns`**, **`_has_category`** — small formatting / aggregation utilities for the summary sheet.

## Dependencies

- **`pandas`**, **`openpyxl`** (Excel writer). No `src/` imports.
