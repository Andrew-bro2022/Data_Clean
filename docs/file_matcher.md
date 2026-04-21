# `src/file_matcher.py`

## Purpose
Matches each raw file to the corresponding standard rule.

## Key Function
- `match_rule(raw_file, rules, explicit_mapping)`

## Matching Strategy
1. Check exact raw filename in explicit mapping (`mappings` from YAML).
2. If not mapped, normalize raw filename and compare with:
   - standard filename
   - configured aliases
3. Return matching `FileRule` or `None`.

## Normalization Source
Uses `normalize_token()` from `src/utils.py`:
- lowercase
- remove version suffix like `_r20260217`
- remove supported date suffixes
- normalize spaces and underscores
