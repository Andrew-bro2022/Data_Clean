# `src/cleaner.py`

## Purpose
Performs value-level cleaning and removes fully blank rows/columns.

## Key Functions
- `_clean_scalar(value)`: normalizes one cell value.
- `clean_dataframe(df)`: applies scalar cleaning to all cells and removes fully blank axes.

## Cleaning Rules Implemented
- Trim whitespace.
- Strip surrounding single/double quotes.
- Convert null-like tokens to null:
  - `""`, `-`, `null`, `n/a`, `na`
- Remove `$`.
- Numeric separators:
  - European format like `1.234,56` -> `1234.56`
  - Otherwise remove commas (thousand separators).
- Drop fully blank rows.
- Drop fully blank columns.
