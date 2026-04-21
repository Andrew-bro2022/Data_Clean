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
  - parse via `pandas.to_datetime`
  - prefer YAML `date_format` when provided
- String type:
  - cast to pandas `string`

## Issue Counting
For each converted column, count rows that were non-null before conversion and null after conversion.
