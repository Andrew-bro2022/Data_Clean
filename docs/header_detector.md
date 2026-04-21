# `src/header_detector.py`

## Purpose
Detects which row should be treated as the header row in raw CSV files.

## Key Function
- `detect_header_row(preview_rows, standard_columns, threshold)`

## Algorithm
- Normalize standard column names and each preview row's cells.
- For each row, compute:
  - `match_ratio = matched_standard_columns / total_standard_columns`
- Select the row with highest ratio.
- Return row index only if ratio is at least `threshold` (default from YAML: `0.6`).

## Return
- Header row index (`int`) when valid
- `None` when no row meets threshold
