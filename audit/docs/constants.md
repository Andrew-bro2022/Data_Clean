# `audit/constants.py`

## Role

Central place for **audit-only** tunables (no YAML). Editing these changes sensitivity without touching rules files.

## Contents (summary)

| Name | Purpose |
|------|---------|
| `PHANTOM_MIN_CONSECUTIVE` | Minimum consecutive trailing “phantom” rows to report. |
| `PHANTOM_EMPTY_CELL_RATIO` | How empty a row must be to count toward phantom logic. |
| `PHANTOM_MIN_COLUMNS` | Minimum column count on the dataframe for phantom checks. |
| `TAIL_KEYWORD_SCAN_ROWS` | How many rows from the bottom to scan for total-like keywords. |
| `TOTAL_KEYWORDS` | Lowercase substrings matched in that tail window. |
| `SAMPLE_ROW_LIMIT` | Max distinct row numbers listed per issue. |
| `READ_ENCODING_FALLBACKS` | Encodings tried after YAML `encoding` fails (`audit.profile._read_csv_audit`). |

## Usage

Imported by **`audit.profile`** and **`audit.checks`**. The main cleaning pipeline does **not** import this module.
