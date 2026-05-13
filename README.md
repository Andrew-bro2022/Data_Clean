# Data Cleaning Pipeline (Python)

## Overview

This project provides a modular Python pipeline to clean raw financial CSV files, validate data against standard definitions, and generate:

- cleaned CSV outputs in `output/`
- one Excel report per run in `reports/`

Optionally, a **pre-clean audit** (separate from the pipeline) can scan `raw/` and write one Excel workbook under `audit/output/`; see [audit/README_AUDIT.md](audit/README_AUDIT.md).

The pipeline supports:

- batch mode (process files in `raw/` and **one subdirectory level**: `raw/*.csv` and `raw/*/*.csv`).
- single-file debug mode (path relative to `--base-dir`, must stay under `raw/`)
- automatic standard-to-YAML rule generation

---

## Project Structure

```text
data_clean/
├─ raw/                 # Input raw files
├─ standards/           # Standard definition CSV files
├─ config/
│  └─ file_rules.yaml   # Runtime rules (mapping, types, formats, read options)
├─ output/              # Cleaned CSV files
├─ reports/             # Excel run reports
├─ audit/               # Pre-clean audit code; reports under audit/output/
├─ logs/                # Pipeline logs
├─ src/                 # Python source code
├─ docs/                # Per-script documentation
└─ requirements.txt
```

---

## Prerequisites

- Python `3.10+`
- Install dependencies:

```bash
pip install -r requirements.txt
```

---

## How Standard Rules Work

Standard files in `standards/` are expected to be CSV files where:

- row 1 = column names
- row 2 = sample values (used for type/date-format inference)

Rule config is stored in `config/file_rules.yaml`.

- If `file_rules.yaml` does not exist, the pipeline auto-generates it from `standards/`.
- If `file_rules.yaml` already exists, the pipeline uses it directly.

**Date columns:** Put representative values in standard row 2 and set each column's `date_format` in YAML (for example `'%Y-%m-%d'` or `'%m/%d/%Y'`). Raw cells may still use other common shapes; the pipeline tries the YAML format first, then infers the rest when parsing. **Output CSV** writes each date/datetime column using **that column's `date_format`** from the rule. If `date_format` is omitted for a date column, the writer falls back to **`%Y-%m-%d`**.

---

## Pre-clean audit (optional)

Run **before** the main pipeline to flag structure issues, strict date parse failures, suspicious numeric cells, phantom rows at the file tail, and total-like rows. Requires an existing `config/file_rules.yaml`.

```bash
python -m audit.main --base-dir .
```

Details, CLI flags (`--file`, `--max-data-rows`), and how to read the workbook: [audit/README_AUDIT.md](audit/README_AUDIT.md).

---

## How to Run

### 1) Batch Mode

Process all eligible files under `raw/` (top-level files and files one folder deep):

```bash
python -m src.main --base-dir .
```

Cleaned outputs **mirror** the structure under `raw/`, for example `raw/teamA/foo.csv` -> `output/teamA/foo.csv`.

Note: the pipeline **skips** synthetic audit regression fixtures under `raw/_audit_fixtures/`.
Note: `.xlsx` files are always reported as `skipped_xlsx` (the pipeline does not process Excel inputs).

### 2) Single File Debug Mode

Process one file; path is **relative to `--base-dir`** and must lie under `raw/`:

```bash
python -m src.main --base-dir . --file raw/BA_CVA_ALLOCATION_20241031_20250527.csv
```

### 3) Update `config/file_rules.yaml` Only (Run `src/reader.py` Separately)

Regenerate YAML rules from `standards/` without running the full cleaning pipeline:

```bash
python -m src.reader --base-dir .
```

If `config/file_rules.yaml` **already exists**, the default behavior is to **merge** into the new file:

- keeps `mappings` and `raw_prefix_to_standard`
- keeps `header_match_threshold` and merges `defaults` with CLI flags
- merges extra `aliases` and per-rule `read` blocks for each standard file that still exists

Use `--no-merge` for a clean slate (drops manual `mappings` / prefixes until you add them again):

```bash
python -m src.reader --base-dir . --no-merge
```

Optional overrides:

```bash
python -m src.reader --base-dir . --standards-dir ./standards --output-yaml ./config/file_rules.yaml --encoding utf-8 --delimiter "," --skiprows 0
```

---

## What the Pipeline Does

For each file:

1. Skip `.xlsx` files and mark as `skipped_xlsx`
2. Match raw file to a standard rule
3. Detect header row using match ratio threshold (default `0.6`)
4. Clean values (trim, null normalization, currency/quotes cleanup, numeric normalization)
5. Remove fully blank rows only (columns that appear in the header row are kept even if every cell is empty after cleaning)
6. Compare header names to standard columns:
   - keep extra columns in output (and report them as `extra_columns`)
   - report `missing_columns` only when a YAML-standard column name is absent from the raw header row (do not output columns that were never present in the raw header)
7. Convert types based on YAML rules
8. Save cleaned CSV with original raw filename
9. Add summary and column stats to Excel report

---

## Status Definitions

- `success`: processed successfully (missing/extra columns allowed)
- `warning`: processed with type conversion issues
- `failed`: unrecoverable issue (for example, no matching rule or header not found)
- `skipped_xlsx`: skipped by design

---

## Report Output

Each run creates:

- `reports/report_YYYYMMDD_HHMMSS.xlsx`

Sheets:

- `file_summary`: one row per file (includes `raw_subfolder`: the folder name directly under `raw/`, or empty for files in `raw/` root)
- `column_stats`: per-file, per-column null and conversion issue counts (also includes `raw_subfolder` to disambiguate same file names in different folders)

---

## Teammate Onboarding: What They Need to Change

If a teammate uses this project in a different environment or with new files, they should review these locations:

### 1) `config/file_rules.yaml` (most important)

Update:

- `defaults`
  - `encoding` (for example `utf-8`, `latin1`)
  - `delimiter` (for example `,`, `|`, `\t`)
  - `skiprows` (if upstream files include fixed pre-header lines)
- `header_match_threshold` (default `0.6`)
- `mappings`
  - map a **raw file name** to a **standard file** (for example `foo.csv: MyStandard_r20260217.csv`)
  - optional: map a path **under `raw/`** (forward slashes) to disambiguate same name in different subfolders (for example `teamA/foo.csv: MyStandard_r20260217.csv`); this match is tried before the filename-only key
- `raw_prefix_to_standard` (optional)
  - map a **raw basename prefix** to an exact **standard file** key under `rules` (for example `DESK_STANDALONE_RWA_: Desk_RWA_r20260205.csv`) so changing date suffixes in the filename still match without listing every file
- `rules`
  - per standard file column definitions:
    - `name`
    - `type` (`int`, `float`, `date`, `string`)
    - `date_format` for date columns

### 2) `standards/`

- Add or update standard CSV files when new data domains appear.
- Keep row 1/row 2 format consistent.

### 3) `raw/`

- Place new raw files here before running.
- `.xlsx` files are skipped and must be converted to CSV manually if needed.
- `raw/_audit_fixtures/` is reserved for audit regression fixtures (the pipeline skips this folder).
- `raw/pipeline_tests/` may contain synthetic CSVs to exercise the main cleaning pipeline (see below).

### 4) Optional code-level adjustments in `src/`

Only needed if business rules change:

- `src/cleaner.py`: custom value cleaning logic
- `src/header_detector.py`: header detection strategy
- `src/validator.py`: type conversion strategy
- `src/file_matcher.py` and `src/utils.py`: filename normalization/matching behavior

---

## Team Usage Checklist

Before running:

1. Confirm Python and dependencies are installed.
2. Confirm standard CSV files exist in `standards/`.
3. Review `config/file_rules.yaml` for local encoding/delimiter/mapping differences.
4. Put raw files into `raw/`.
5. (Optional) Run `python -m audit.main --base-dir .` and review `audit/output/audit_*.xlsx` before a full clean.

After running:

1. Check `reports/report_*.xlsx` first.
2. Review `failed` and `warning` rows.
3. Inspect corresponding cleaned outputs in `output/`.

---

## Regression fixtures (main pipeline)

To generate synthetic raw files that cover common pipeline statuses (success/warning/failed/skipped_xlsx), run:

```bash
python tools/generate_pipeline_fixtures.py
```

This writes files under `raw/pipeline_tests/`. These fixtures are designed to be processed by the pipeline (unlike `raw/_audit_fixtures/` which is audit-only).

`Test_Wide_multi_*.csv` files use the synthetic 10-column standard `Test_Wide_Audit_r20260510.csv` so **multiple** missing/extra columns can appear while still passing the default `header_match_threshold` (a 4-column standard cannot show two missing columns and still match at 0.6).

## Script Documentation

Detailed per-script docs are available in `docs/`:

- `docs/main.md`
- `docs/reader.md`
- `docs/file_matcher.md`
- `docs/header_detector.md`
- `docs/cleaner.md`
- `docs/validator.md`
- `docs/exporter.md`
- `docs/utils.md`
- `docs/types.md`

