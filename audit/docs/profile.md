# `audit/profile.py`

## Role

Orchestrates a single raw file audit: match rule, read CSV, detect header, align column names to the standard, compare layout, run value checks, return a **`FileAuditResult`**.

## Key types

- **`FileAuditResult`** (dataclass): file name, match info, `header_row_index`, row/column counts, `missing_columns` / `extra_columns` (literal header gaps vs standard names), `issues` (list of dicts), optional `error_message`, and column-order layout fields (`column_count_match`, `column_order_match`, etc.).

## CSV read (aligned with clean)

Audit uses **`src.io.read_csv_raw`** — same as the clean pipeline:

- YAML encoding then **`audit.constants.READ_ENCODING_FALLBACKS`**
- On **`pandas.errors.ParserError`**, retries with **`on_bad_lines="warn"`** and records line-level notes
- **`_csv_parse_structure_issues`** turns parse notes into **`STRUCTURE`** warning issues (same semantics as clean `pre_clean` reporting)

## Important functions

- **`_analyze_column_count_and_order(standard_ordered, raw_ordered)`**  
  Position-wise comparison of header names after rename (used for `column_count_match` / `column_order_match`).

- **`audit_file(...)`**  
  Main state machine: xlsx skip, unmatched rule path, matched path with header detection, layout + **`audit.checks.run_value_checks`**. Uses **`src.utils`**, **`src.file_matcher.match_rule`**, **`src.header_detector.detect_header_row`**.

## Encoding hints

On **`UnicodeDecodeError`**, the outer `except` may append a hint to `error_message` (cp1252 / latin-1).
