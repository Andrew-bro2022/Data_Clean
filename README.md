# Data Cleaning Pipeline (Python)

## Overview

This project provides a modular Python pipeline to clean raw financial CSV files, validate data against standard definitions, and generate:

- cleaned CSV outputs in `output/`
- one Excel report per run in `reports/`

The pipeline supports:

- batch mode (process all files in `raw/`)
- single-file debug mode
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

---

## How to Run

### 1) Batch Mode

Process all files in `raw/`:

```bash
python -m src.main --base-dir .
```

### 2) Single File Debug Mode

Process only one raw file:

```bash
python -m src.main --base-dir . --file BA_CVA_ALLOCATION_20241031_20250527.csv
```

### 3) Update `config/file_rules.yaml` Only (Run `src/reader.py` Separately)

Regenerate YAML rules from `standards/` without running the full cleaning pipeline:

```bash
python -m src.reader --base-dir .
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
5. Remove fully blank rows/columns
6. Compare against standard columns:
   - keep extra columns in output
   - do not add missing columns
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

- `file_summary`: one row per file
- `column_stats`: per-file, per-column null and conversion issue counts

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
  - add explicit raw-to-standard mappings for ambiguous names
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
- `.xlsx` files are skipped and must be converted manually if needed.

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

After running:

1. Check `reports/report_*.xlsx` first.
2. Review `failed` and `warning` rows.
3. Inspect corresponding cleaned outputs in `output/`.

---

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

