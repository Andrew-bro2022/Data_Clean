# `audit/checks.py`

## Role

Builds the **`issues`** list for `audit.profile.audit_file`: each item is a dict with **`category`**, **`severity`**, optional **`column`**, **`message`**, **`count`**, **`sample_rows`** (1-based row indices where applicable).

## Entry point

- **`run_value_checks(df, column_rules, *, raw_path=None, read_opts=None, header_row_index=None)`**  
  - Runs **date** strict checks when YAML has `date_format`.  
  - Runs **numeric** checks for int/float/numeric columns present in `df` (`$`, accounting parentheses, scientific notation).
  - Runs **scientific notation** checks for **string** columns as well (Excel CSV export).
  - If `raw_path` / `read_opts` / `header_row_index` are set, runs **`collect_numeric_quoting_issues_from_raw`** (raw line scan for quoted numerics / quoted comma patterns; not scientific notation).
  - Runs **placeholder** checks on every YAML column present in `df` (`-`, `–`, `—`, `null`, `n/a`, `na`).
  - Appends **phantom** trailer and **total-keyword** checks on `df`.

## Helpers (selected)

- **`check_dates_strict`**, **`check_numeric_column`** (`$`, accounting parentheses), **`check_scientific_notation`** (numeric + string columns on `df`), **`check_placeholder_tokens`** (all YAML columns on `df`).  
- **`split_csv_raw_fields`**, **`collect_numeric_quoting_issues_from_raw`** — delimiter-aware raw line parsing for numeric columns.  
- **`check_phantom_trailer`**, **`check_total_keywords`** — file-tail heuristics.

## Categories (typical)

`DATE`, `NUMERIC`, `PLACEHOLDER`, `STRUCTURE`, `COLUMN_LAYOUT`, `PHANTOM`, `TOTAL`, `FILE` — used by **`audit.reporter`** for roll-up columns and filters.

## Constants

Thresholds used here come from **`audit.constants`** (`SAMPLE_ROW_LIMIT`, phantom/total parameters, etc.). See [constants.md](constants.md).
