# `src/types.py`

## Purpose
Defines typed dataclasses that represent configuration and processing outputs.

## Dataclasses
- `ColumnRule`
  - `name`
  - `data_type`
  - `date_format` (optional)
- `FileRule`
  - `standard_file`
  - `read` options (`encoding`, `delimiter`, `skiprows`, etc.)
  - `columns` (list of `ColumnRule`)
  - `aliases`
- `ProcessingResult`
  - per-file status, row stats, missing/extra columns, conversion issues, null counts, error and output path

## Usage Context
Imported by most modules to keep interfaces explicit and consistent.
