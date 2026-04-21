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
- Cleaned CSV files in `output/`
- Run report Excel file in `reports/`
- Runtime log in `logs/pipeline.log`

## CLI Usage
```bash
python -m src.main --base-dir .
python -m src.main --base-dir . --file BA_CVA_ALLOCATION_20241031_20250527.csv
```

## Status Behavior
- `.xlsx` -> `skipped_xlsx`
- Header not detected / exceptions / no matching rule -> `failed`
- Type conversion issues -> `warning`
- Otherwise -> `success`
