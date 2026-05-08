# `src/validator.py`

## Purpose
Converts columns to expected types and derives per-file status.

## Key Functions
- `convert_types(df, column_rules)`: applies type conversion by rule and counts conversion failures.
- `derive_status(header_row_found, has_conversion_issue, failed)`: maps processing flags to status code.

## Conversion Rules
- Numeric types (`int`, `integer`, `float`, `numeric`):
  - convert via `pandas.to_numeric(errors="coerce")`
  - `int` values are rounded and cast to nullable `Int64`
- Date types (`date`, `datetime`):
  - **Canonical output** in CSV is always **`YYYY-MM-DD`** (see `save_cleaned` `date_format`).
  - **Parsing**: first try YAML `date_format` (should be `%Y-%m-%d` for new standards); any non-empty cell that still fails is parsed again with `pandas.to_datetime(..., errors="coerce", dayfirst=False)` so legacy shapes (e.g. `MM/DD/YYYY`) can still be read.
  - Parsed values are **normalized** to midnight (date-only).
- String type:
  - cast to pandas `string`

## Issue Counting
For each converted column, count rows that were non-null before conversion and null after conversion.
