# `src/reader.py`

## Purpose
Builds and loads YAML-based file rules from standard CSV files.

## Key Functions
- `_infer_type_and_format(sample_value)`: infers `int`/`float`/`date`/`string` and date format from sample value.
- `build_rules_from_standards(standards_dir, output_yaml, default_read)`: scans standard files and generates one YAML config.
- `load_rules(yaml_path)`: parses YAML into runtime dataclasses.

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
- `rules` (per standard file, including `aliases`, `read`, and `columns`)

## Usage Context
Called by `src/main.py` when `config/file_rules.yaml` is missing, or used directly for loading existing config.
