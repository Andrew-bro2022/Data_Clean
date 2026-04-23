# `src/file_matcher.py`

## Purpose
Matches each raw file to the corresponding standard rule.

## Key Function
- `match_rule(raw_file, rules, explicit_mapping, raw_dir)`

## Matching Strategy
1. If `raw_file` is under `raw_dir`, check **`mappings`** for the path relative to `raw/` using forward slashes (for example `teamA/foo.csv`).
2. If no hit, check **`mappings`** for the bare basename (for example `foo.csv`).
3. If still not mapped, check **`raw_prefix_to_standard`**: longest registered prefix wins when the raw **basename** `startswith(prefix)`.
4. If still not mapped, normalize the raw basename and compare with:
   - standard filename
   - configured aliases
5. Return matching `FileRule` or `None`.

## Normalization Source
Uses `normalize_token()` from `src/utils.py`:
- lowercase
- remove version suffix like `_r20260217`
- remove supported date suffixes
- normalize spaces and underscores
