# `audit/main.py`

## Role

Command-line entry for the pre-clean audit: load config, enumerate raw files, call `audit_file` per file, write one timestamped Excel report.

## Flow

1. **`run_audit(base_dir, target_file, max_data_rows)`**
   - Resolves `config/file_rules.yaml` under `base_dir`; raises if missing.
   - **`src.reader.load_rules`** → `rules`, `mappings`, `header_match_threshold`, `defaults`, `raw_prefix_to_standard` (same tuple as the cleaning pipeline).
   - **`raw_dir`** = `base_dir / "raw"` (resolved).
   - **File list**: either a single path from `--file` (must exist and lie under `raw/`), or **`src.utils.iter_raw_files_one_level(raw_dir)`** (top-level files + one subdirectory level).
2. For each file, **`audit.profile.audit_file(...)`** with `max_data_rows` forwarded.
3. **`audit.reporter.write_audit_excel`** → default path under `audit/output/`.

## CLI

Parsed in **`parse_args`**: `--base-dir`, `--file`, `--max-data-rows`. **`main()`** configures logging, runs `run_audit`, logs the output path.

## Dependencies

- `src.reader`, `src.utils` (see [README.md](README.md) index).
