# Pre-clean data audit

Standalone step that runs **before** the main cleaning pipeline. It scans CSVs under `raw/` (single directory level), validates them against `config/file_rules.yaml` where applicable, and writes **one** timestamped Excel report under `audit/output/` (for example `audit/output/audit_YYYYMMDD_HHMMSS.xlsx`).

## Prerequisites

- `config/file_rules.yaml` must be present. The audit cannot run without it.
- If a raw file’s path does not match any rule, the tool still performs **file-level** checks (read errors, phantom trailer, total-like rows). It does **not** apply standard column names, date formats, or numeric column rules for that file.
- If the configured encoding fails (common: UTF-8 vs Windows-1252), audit **retries** reads with `cp1252` then `latin-1`, updates `read_opts["encoding"]` for that file, and adds a **`FILE` warning** suggesting you set `defaults.encoding` or the rule’s `read.encoding` in YAML so the main pipeline matches.

## How to run

From the repository root:

```text
python -m audit.main --base-dir .
```

### CLI options

| Option | Description |
|--------|-------------|
| `--base-dir PATH` | Project root (default: current working directory). |
| `--file RELATIVE_PATH` | Audit one file only. Path is resolved under `--base-dir` and must lie under `raw/`. |
| `--max-data-rows N` | After the detected header, use at most **N** data rows for value checks (dates, numbers, quoting). Phantom-row and total-keyword logic use the **same** row window. On very large files, tail-of-file behavior may therefore differ from a full read. Omit this flag to scan all data rows. |

## Report layout

### Sheet: `file_summary`

One row per audited file: matched rule (if any), header row index, `missing_columns` / `extra_columns` (same semantics as the cleaner), row counts, note when sampling was applied, read errors, and overall status.

Roll-up columns (quick filter in Excel):

- `standard_n_columns` / `raw_n_columns` — column counts (YAML standard vs detected raw header width).
- `column_count_match` / `column_order_match` — `Y`/`N` (blank when not applicable, e.g. header not found).
- `column_order_first_mismatch_1based` — first 1-based index where raw header names diverge from standard order **position-wise** (left to right); if counts differ but names match up to `min(n)`, the first difference is at `min(n)+1` (extra tail or missing tail).
- `column_order_mismatch_expected` / `column_order_mismatch_found` — names (or sentinel text) at that position. See `COLUMN_LAYOUT` rows in `issues_detail` for the full sentence.

- `date_issue_columns` — comma-separated column names with at least one `DATE` issue in `issues_detail`.
- `numeric_issue_columns` — same for `NUMERIC` (quoted / `$` / strict numeric checks as implemented).
- `phantom_issue` / `total_keyword_issue` — `Y` when that file-level check fired (these checks usually have no `column` on the detail row).

`categories` remains a compact `CATEGORY:count` summary; use `issues_detail` for every row, message, and sample row numbers.

### Sheet: `issues_detail`

All findings in one table: severity, check name, column (if relevant), row index (1-based in the audited dataframe when applicable), sample cell value, and message.

## What is checked

| Area | Behavior |
|------|----------|
| **Structure** | Header detection and column set compared to the YAML `columns` list, using the same matching logic as the clean pipeline. |
| **Dates** | Values in date columns are parsed strictly with the rule’s `date_format` (cleaning writes each date column using that same `date_format` in CSV, or `%Y-%m-%d` when omitted). |
| **Numbers** | US/Canada grouping is accepted (e.g. `1,234.56`). Other values that do not parse as numbers are flagged. Double-quoted numeric-looking cells are warnings; quoted values that contain a thousands comma (e.g. `"1,234"`) are escalated. `$` in numeric columns is a warning. |
| **Phantom rows** | A long run of mostly empty or comma-padded rows at the **bottom** of the audited data (see `PHANTOM_MIN_CONSECUTIVE` in `audit/constants.py`). |
| **Total-like rows** | Keywords such as `Total`, `Grand Total`, and `SUM` in the last portion of the data (see `TAIL_KEYWORD_SCAN_ROWS` in `audit/constants.py`). |

Adjust sensitivity by editing thresholds in `audit/constants.py`.

## Large files

For inputs on the order of hundreds of MB, pass `--max-data-rows` to cap how many data rows are analyzed. The summary sheet records that sampling was used. Re-run without the cap when you need a full-file tail check.

## Regression fixtures (`raw/_audit_fixtures/`)

Synthetic CSV/XLSX files exercise structure, dates, numeric quoting/currency, phantom trailers, totals, unmatched rules, skipped xlsx, header-detection failure, and multi-column `missing_columns` / `extra_columns` cases. Paths are wired in `config/file_rules.yaml` under `mappings`. Regenerate files after editing:

```text
python -m audit.generate_test_raw_fixtures
```

Note: the main cleaning pipeline intentionally skips `raw/_audit_fixtures/` to avoid fixture noise in production runs.
