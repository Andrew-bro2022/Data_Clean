# `src/reader.py`

## Purpose
Builds and loads YAML-based file rules from standard CSV files.

## Key Functions
- `_infer_type_and_format(sample_value)`: infers `int`/`float`/`date`/`string` and date format from sample value.
- `build_rules_from_standards(..., merge_existing=True)`: scans standard files and writes `file_rules.yaml`. If the output file already exists and `merge_existing` is true, preserves `mappings`, `raw_prefix_to_standard`, merges extra `aliases` and per-rule `read` blocks, and keeps `header_match_threshold` / `defaults` overlays.
- `load_rules(yaml_path)`: parses YAML (returns rules, mappings, threshold, defaults, and `raw_prefix_to_standard`).

## Type Inference Notes
- Integer if parseable as int without decimal point.
- Float if decimal-based numeric.
- Date if one of supported formats:
  - `%Y-%m-%d`
  - `%m/%d/%Y`
  - `%m/%d/%y`
  - `%m-%d-%Y`
- Scientific notation is not handled specially.

## YAML Shape Produced
- `defaults`
- `header_match_threshold`
- `mappings`
- `raw_prefix_to_standard` (optional: raw **basename** prefix -> exact standard filename under `rules`)
- `rules` (per standard file, including `aliases`, `read`, and `columns`)

## CLI
- `python -m src.reader --base-dir .` — merge when prior `file_rules.yaml` exists (default).
- `python -m src.reader --base-dir . --no-merge` — full reset (empty `mappings` / prefixes, no alias merge).

## Usage Context
Called by `src/main.py` when `config/file_rules.yaml` is missing, or used directly for loading existing config.
