# `audit/profile.py`

## Role

Orchestrates a single raw file audit: match rule, read CSV (with encoding fallbacks and optional parse recovery), detect header, align column names to the standard, compare layout, run value checks, return a **`FileAuditResult`**.

## Key types

- **`FileAuditResult`** (dataclass): file name, match info, `header_row_index`, row/column counts, `missing_columns` / `extra_columns` (literal header gaps vs standard names), `issues` (list of dicts), optional `error_message`, and column-order layout fields (`column_count_match`, `column_order_match`, etc.).

## Important functions

- **`_read_csv_audit(path, header=..., read_opts=..., nrows=...)`**  
  Returns **`(DataFrame, encoding_used, parse_notes)`**. Tries YAML encoding then **`audit.constants.READ_ENCODING_FALLBACKS`**. On **`pandas.errors.ParserError`**, retries with **`on_bad_lines="warn"`** so audit can continue; appends human-readable notes (e.g. ragged rows / unquoted commas) for **`STRUCTURE`** issues.

- **`_analyze_column_count_and_order(standard_ordered, raw_ordered)`**  
  Position-wise comparison of header names after rename (used for `column_count_match` / `column_order_match`).

- **`_issues_from_csv_parse_notes(notes)`**  
  Turns parse-recovery strings into **`STRUCTURE`** warning issues.

- **`audit_file(...)`**  
  Main state machine: xlsx skip, unmatched rule path, matched path with header detection, layout + **`audit.checks.run_value_checks`**. Uses **`src.utils`**: `normalize_header_column_name`, `preview_rows_for_header_detection`, `rename_raw_headers_to_standard`, `literal_header_missing_and_extra`, `raw_subfolder_under_raw`. Uses **`src.file_matcher.match_rule`**, **`src.header_detector.detect_header_row`**.

## Encoding hints

On **`UnicodeDecodeError`**, the outer `except` may append a hint to `error_message` (cp1252 / latin-1), similar in spirit to the cleaning pipeline docs.
