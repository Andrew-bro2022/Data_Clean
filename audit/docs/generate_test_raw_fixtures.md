# `audit/generate_test_raw_fixtures.py`

## Role

One-off **generator** of small CSV (and optionally XLSX) files under **`raw/_audit_fixtures/`** for manual or automated regression of audit behavior. Not invoked by `audit.main` during a normal audit run.

## How to run

From repository root:

```text
python -m audit.generate_test_raw_fixtures
```

## Output

Creates or overwrites fixtures such as `audit_clean_ok.csv`, `audit_bad_date.csv`, `audit_quoted_numeric.csv`, etc. These paths are typically wired in **`config/file_rules.yaml`** → `mappings` so audit runs against a known standard rule.

## Note

The main cleaning pipeline is configured to **skip** `raw/_audit_fixtures/` so fixtures do not pollute production `output/`.
