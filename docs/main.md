# `src/main.py`

## Purpose
Entrypoint for running the data cleaning pipeline in batch mode or single-file debug mode.

## Key Functions
- `setup_logging(log_dir)`: configures file + console logging.
- `process_file(raw_file, rule, threshold, output_dir)`: processes one raw file end-to-end.
- `run_pipeline(base_dir, target_file)`: orchestrates file discovery, rule matching, processing, and report export.
- `parse_args()`: CLI argument parser.

## Inputs
- `raw/` folder files (`.csv`, `.xlsx`)
- `config/file_rules.yaml`
- Optional CLI argument: `--file <raw_filename>`

## Outputs
- Cleaned CSV files in `output/` (**mirrors** paths under `raw/` for files in a subfolder one level deep)
- Run report Excel file in `reports/`
- Runtime log in `logs/pipeline.log`

## CLI Usage
```bash
python -m src.main --base-dir .
python -m src.main --base-dir . --file raw/teamA/foo.csv
```

## Status Behavior
- `.xlsx` -> `skipped_xlsx`
- Header not detected / exceptions / no matching rule -> `failed`
- Type conversion issues -> `warning`
- Otherwise -> `success`

## Missing vs Extra Columns (Reporting)

- **missing_columns**: standard columns from YAML that **do not appear** in the raw file's **detected header row**. Entirely empty columns that still appear in the header are **not** missing.
- **extra_columns**: header column names that are **not** listed in the standard YAML rules for that file.
- **Output**: fully blank columns from the raw header are **retained** in `output/` (no longer dropped during cleaning).
