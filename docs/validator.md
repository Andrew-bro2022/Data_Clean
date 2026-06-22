# `src/validator.py`

## Purpose
Converts columns to expected types and derives per-file `status`.

## Key Functions
- `convert_types(df, column_rules)` → `(DataFrame, TypeConversionMeta)`
  - `type_issues`: non-empty cells that failed conversion
  - `date_stats`: per-column strict / alternate / Excel serial / inferred / failed counts
  - `scientific_preserved`: float cells kept as literal scientific strings
- `derive_status(...)`: maps flags to `success` / `warning` / `failed`

## Conversion Rules

### Numeric (`int`, `integer`, `float`, `numeric`)
- `to_numeric` with `errors="coerce"`
- `int` → round, nullable `Int64`
- **`float` / `numeric`:** cells matching Excel scientific notation are **not** coerced — kept as source text for CSV output

### Date (`date`, `datetime`)
Per cell, in order:
1. Strict YAML `date_format`
2. Excel serial (e.g. `45674`)
3. Common alternate formats (`%m/%d/%Y`, `%m%d%y`, …)
4. `pandas.to_datetime` infer (`dayfirst=False`)

Parsed values normalized to midnight. Non-strict successes → `warning` in report (`DATE` category). Output formatting: see `save_cleaned`.

### String
- pandas `string` dtype

## Issue Counting
- Type: non-null before, null after conversion
- Date: `date_stats.failed` plus `TYPE` warning when parse fails

Policy: [README_DATA_CLEAN_POLICY.md](../README_DATA_CLEAN_POLICY.md)
