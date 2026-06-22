# Data Cleaning Pipeline (Python)

## Overview

This project provides a modular Python pipeline to clean raw financial CSV files, validate data against standard definitions, and generate:

- cleaned CSV outputs in `output/`
- one Excel report per run in `reports/`

Optionally, a **pre-clean audit** (separate from the pipeline) can scan `raw/` and write one Excel workbook under `audit/output/`; see [audit/README_AUDIT.md](audit/README_AUDIT.md).

**Clean behavior (fail vs warn, row filters, value rules)** is documented in [README_DATA_CLEAN_POLICY.md](README_DATA_CLEAN_POLICY.md) ([中文版](README_DATA_CLEAN_POLICY_CN.md)). YAML defines schema only (`type`, `date_format`, mappings)—not clean policy.

For a colleague-oriented walkthrough, see [docs/clean_pipeline.md](docs/clean_pipeline.md).  
**Audit then clean (recommended batch workflow):** [docs/audit_clean_workflow.md](docs/audit_clean_workflow.md).

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

Run **before** the main pipeline on new batches. Full step-by-step: **[docs/audit_clean_workflow.md](docs/audit_clean_workflow.md)**.

```bash
python -m audit.main --base-dir .
```

Report: `audit/output/audit_YYYYMMDD_HHMMSS.xlsx`. CLI (`--file`, `--max-data-rows`) and sheet layout: [audit/README_AUDIT.md](audit/README_AUDIT.md).

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

For each file (see [README_DATA_CLEAN_POLICY.md](README_DATA_CLEAN_POLICY.md) for full policy):

1. Skip `.xlsx` → `skipped_xlsx`; skip `raw/_audit_fixtures/`
2. Match raw file to a standard rule (`file_rules.yaml`)
3. Read CSV (encoding fallback; ragged rows → warn with line numbers)
4. Detect header row (default threshold `0.6`)
5. Rename headers to standard names; **fail** on duplicate standard columns
6. **Layout gate:** **fail** on missing or extra columns vs YAML; **reorder** + warn if only order differs
7. Warn on scientific notation in source cells
8. Remove phantom trailer rows; report (do not remove) total-like keyword rows
9. Clean values (placeholders, `$`, commas, accounting parentheses → negative, etc.)
10. Convert types (flexible dates → YAML `date_format` on output; float scientific literals preserved)
11. Save cleaned CSV under `output/` (mirrors `raw/` path) and append to Excel report

---

## Status Definitions

- `success`: processed; output written; no warnings
- `warning`: output written; review `status_reason` and `issues_detail` (e.g. column reorder, non-strict dates, scientific notation, type conversion, encoding fallback, ragged CSV)
- `failed`: no output (no rule, header not found, layout/duplicate-column gate, unhandled error)
- `skipped_xlsx`: Excel not processed; convert to CSV

Also see `layout_status`, `clean_status`, and `output_written` on `file_summary`.

---

## Report Output

Each run creates `reports/report_YYYYMMDD_HHMMSS.xlsx` with **five** sheets:

| Sheet | Purpose |
|-------|---------|
| `file_summary` | One row per file: `status`, `output_written`, `layout_status`, `clean_status`, `status_reason`, row counts, paths (`raw_subfolder` disambiguates same filename in different folders) |
| `issues_detail` | Issues by `phase` and `category` with column, count, sample rows |
| `clean_actions` | File-level clean counts (placeholders, `$`, parens, commas, blank rows) |
| `clean_actions_by_column` | Same actions per column |
| `column_stats` | Per-column nulls, conversion issues, scientific notation, date-parse breakdown |

Details: [docs/clean_pipeline.md](docs/clean_pipeline.md), [docs/exporter.md](docs/exporter.md).

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

See **[docs/audit_clean_workflow.md](docs/audit_clean_workflow.md)** for the full audit → clean flow and the audit-vs-clean behavior table.

Before running:

1. Confirm Python and dependencies are installed.
2. Confirm standard CSV files exist in `standards/`.
3. Review `config/file_rules.yaml` for local encoding/delimiter/mapping differences.
4. Put raw files into `raw/`.
5. Run audit and review `audit/output/audit_*.xlsx` (recommended for new batches).

After clean:

1. Check `reports/report_*.xlsx`.
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

- **[docs/audit_clean_workflow.md](docs/audit_clean_workflow.md)** — recommended audit → clean batch workflow
- **[docs/clean_pipeline.md](docs/clean_pipeline.md)** — colleague guide (flow, report, common cases)
- **[README_DATA_CLEAN_POLICY.md](README_DATA_CLEAN_POLICY.md)** — authoritative clean policy (not in YAML) ([中文版](README_DATA_CLEAN_POLICY_CN.md))

Per-module docs in `docs/`:

- `docs/main.md`
- `docs/reader.md`
- `docs/file_matcher.md`
- `docs/header_detector.md`
- `docs/cleaner.md`
- `docs/validator.md`
- `docs/exporter.md`
- `docs/utils.md`
- `docs/types.md`

