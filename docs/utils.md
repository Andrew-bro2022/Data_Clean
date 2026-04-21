# `src/utils.py`

## Purpose
Shared utility helpers used across modules.

## Key Functions
- `normalize_token(name)`: normalizes filenames/tokens for robust matching.
- `ensure_dir(path)`: creates directory tree if it does not exist.

## `normalize_token` Behavior
- Removes file extension.
- Lowercases and trims.
- Removes version suffix pattern: `_r<digits>`.
- Removes date suffix patterns:
  - `_YYYYMMDD`
  - `_YYYYMMDD_YYYYMMDD`
- Normalizes spaces/underscores into single underscore.
