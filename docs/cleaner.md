# `src/cleaner.py`

## Purpose
Performs value-level cleaning and removes fully blank **rows**. Columns from the layout gate are retained even if all cells are empty after clean.

## Key Functions
- `_clean_scalar(value, data_type, stats, column)`: normalizes one cell; records per-column stats via `CleanActionStats.record`.
- `clean_dataframe(df, column_rules)`: applies cleaning; returns `(df, CleanActionStats)`.

## Cleaning Rules
| Pattern | Action |
|---------|--------|
| `-`, `–`, `—`, `null`, `n/a`, `na` | Clear to empty |
| Surrounding quotes | Strip |
| `$` on numeric or numeric-looking string cells | Strip |
| `1,234.56` / European `1.234,56` | Normalize separators |
| Accounting `(5000)`, `($2,364)` | **Negative** numeric text (accounting convention) |
| `type: string` | Preserve alpha IDs; clean numeric-looking cells per `is_all_numeric_string_cell` |

Fully blank rows after clean → dropped (`all_blank_rows_dropped`).

Policy: [README_DATA_CLEAN_POLICY.md](../README_DATA_CLEAN_POLICY.md)
