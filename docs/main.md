# `src/main.py`

## Purpose
Entrypoint for running the data cleaning pipeline in batch mode or single-file debug mode.

**Policy:** [README_DATA_CLEAN_POLICY.md](../README_DATA_CLEAN_POLICY.md)  
**Guide:** [clean_pipeline.md](clean_pipeline.md)

## Key Functions
- `setup_logging(log_dir)`: configures file + console logging.
- `process_file(raw_file, rule, threshold, raw_dir, output_root)`: processes one raw file end-to-end.
- `run_pipeline(base_dir, target_file)`: orchestrates file discovery, rule matching, processing, and report export.
- `parse_args()`: CLI argument parser.

## Pipeline order (per file)
1. `read_csv_raw` — encoding fallback; ragged rows warn + line numbers
2. `detect_header_row` — fail if not found
3. `rename_raw_headers_to_standard`
4. `detect_duplicate_columns` — fail on duplicate standard assignment
5. `gate_and_align` — fail on missing/extra; reorder + warn on order-only mismatch
6. `scan_scientific_notation` — warning
7. `remove_phantom_trailer_rows` / `scan_total_keyword_rows` — phantom removed; total reported only
8. `clean_dataframe`
9. `convert_types` — returns `TypeConversionMeta` (issues, date stats, scientific preserved)
10. `save_cleaned` + `enrich_result_metadata` → Excel report

## Inputs
- `raw/` (`.csv`; `.xlsx` skipped; `_audit_fixtures/` skipped)
- `config/file_rules.yaml`
- Optional: `--file <path under raw/>`

## Outputs
- Cleaned CSV under `output/` (mirrors `raw/` paths one level deep)
- `reports/report_YYYYMMDD_HHMMSS.xlsx` (5 sheets)
- `logs/pipeline.log`

## CLI Usage
```bash
python -m src.main --base-dir .
python -m src.main --base-dir . --file raw/teamA/foo.csv
```

## Status Behavior
- `.xlsx` → `skipped_xlsx`
- No rule / header not found / layout fail / duplicate columns / exception → `failed` (no output)
- Warnings (output still written): column reorder, scientific notation, non-strict dates, type conversion issues, encoding fallback, ragged CSV, total-like rows, etc.
- `success` when no warnings

See `derive_status` in `src/validator.py` and [README_DATA_CLEAN_POLICY.md](../README_DATA_CLEAN_POLICY.md).

## Layout gate (not “allow extra in output”)

- **missing_columns** or **extra_columns** vs YAML → `failed`, `output_written = N`
- Column set complete but wrong order → realign to YAML, `warning`
- **literal_missing_columns** / **literal_extra_columns** still recorded for reports (raw header spelling vs standard)
