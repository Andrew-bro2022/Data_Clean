# Data clean policy

This document is the **authoritative policy** for the main cleaning pipeline (`python -m src.main`). Policies are **implemented in code** today; they are **not** stored in `config/file_rules.yaml`. YAML continues to define schema only (column names, types, `date_format`, read options, mappings).

When behavior changes, update this file and the corresponding code/tests together.

**中文版：** [README_DATA_CLEAN_POLICY_CN.md](README_DATA_CLEAN_POLICY_CN.md)

**Related docs:** [docs/clean_pipeline.md](docs/clean_pipeline.md) (flow and reports), [docs/audit_clean_workflow.md](docs/audit_clean_workflow.md) (audit → clean batch workflow), [audit/README_AUDIT.md](audit/README_AUDIT.md) (pre-clean audit).

---

## Policy vs configuration

| Layer | Where it lives | What it controls |
|-------|----------------|------------------|
| **Schema** | `config/file_rules.yaml` | Column names, `type`, `date_format`, `read`, `mappings`, prefixes |
| **Clean policy** | This file + `src/` | How values are cleaned, when to fail/warn, row filters, report semantics |

Future idea (not implemented): per-rule overrides in YAML (e.g. `allow_extra` during a transition). Until then, policies below apply to **all** files.

---

## Pipeline order (per file)

1. Read CSV (`src/io.py`) — encoding fallback; ragged rows → warn + continue with line numbers  
2. Detect header row (`src/header_detector.py`)  
3. Rename headers to standard names (`src/utils.py`)  
4. **Duplicate column gate** — fail if two columns map to the same standard name  
5. **Layout gate** (`src/structure.py`) — missing/extra columns → **fail**; column order mismatch → realign + **warning**  
6. Scientific notation scan — **warning** only (no block)  
7. Phantom trailer rows — **remove** automatically  
8. Total-like keyword rows — **report warning**, rows **not** removed  
9. Value clean (`src/cleaner.py`)  
10. Type convert (`src/validator.py`)  
11. Write `output/` CSV + Excel report (`src/exporter.py`)

Files under `raw/_audit_fixtures/` are skipped. `.xlsx` → `skipped_xlsx` (no output).

---

## Layout and structure

| Situation | Policy | Status | Output written? |
|-----------|--------|--------|-----------------|
| No matching YAML rule | Fail | `failed` | No |
| Header row not found | Fail | `failed` | No |
| Missing standard column (after rename) | Fail | `failed` | No |
| Extra column vs standard | Fail | `failed` | No |
| Duplicate standard assignment (e.g. two `Trade_ID`) | Fail | `failed` | No |
| Column set OK, order differs from YAML | Realign to YAML order | `warning` | Yes |
| CSV ragged row / `ParserError` on read | Skip bad line(s), continue | `warning` | Yes (if rest passes) |
| Encoding fallback (e.g. utf-8 → cp1252) | Continue | `warning` | Yes |

**Rationale:** Wrong column set means wrong semantics; fail fast and fix YAML or the source file. Order-only issues are safe to auto-fix.

---

## Row filters

| Situation | Policy |
|-----------|--------|
| **Phantom rows** (trailing rows that are mostly empty commas) | **Remove** — thresholds aligned with `audit/constants.py` |
| **Total / Grand Total** keyword rows | **Keep** — report in `issues_detail` for manual review |
| All-blank rows (after cell clean) | **Drop** |

---

## Value cleaning (`src/cleaner.py`)

Applies per column according to YAML `type`.

| Input pattern | Policy | Notes |
|---------------|--------|-------|
| `-`, `–`, `—`, `null`, `n/a`, `na` | Clear to empty | Not a pipeline failure |
| `$` on numeric or numeric-looking string cells | Strip | |
| Thousands commas (`1,234.56`) | Remove commas | European `1.234,56` → `1234.56` |
| Surrounding quotes | Strip | |
| Accounting parentheses `(5000)`, `($2,364)` | Convert to **negative** numeric text | Accounting convention; same as audit numeric checks |
| **String** columns (`type: string`) | Alpha IDs preserved (`REF001`, `75512E101`) | Numeric-looking strings still get `$`/comma clean per cell |

---

## Scientific notation

| Stage | Policy |
|-------|--------|
| Pre-clean scan | **Warning** if cell matches Excel-style scientific notation (not letter-suffix IDs like `75512E101`) |
| Float / numeric columns at type convert | **Do not** coerce to float — **preserve source literal** in output CSV |
| Other numeric cells | Convert normally; CSV write avoids scientific notation for plain floats |

---

## Dates

| Stage | Policy |
|-------|--------|
| Parse order | 1) YAML `date_format` strict → 2) Excel serial number → 3) common alternate formats → 4) pandas infer |
| Output | Always format using **that column’s YAML `date_format`** (default `%Y-%m-%d` if omitted) |
| Non-strict parse success | **Warning** in report (`DATE` category) with counts: alternate / Excel serial / inferred |
| Parse failure (non-empty cell) | **Warning** (`TYPE` conversion issue); cell empty in output |

Raw files may mix `2025-01-15`, `1/16/2025`, and serial `45674` in one column; all normalize to the YAML format on output.

---

## Type conversion summary

| YAML `type` | Behavior |
|-------------|----------|
| `int` / `integer` | `to_numeric`, round, nullable `Int64` |
| `float` / `numeric` | `to_numeric` except scientific literals (kept as string) |
| `date` / `datetime` | Flexible parse (above), normalized midnight |
| `string` | String dtype |

Conversion failures on non-empty cells → `warning`, counted in `type_conversion_issues`.

---

## Run status (`file_summary.status`)

| Status | Meaning |
|--------|---------|
| `success` | Processed; no warnings |
| `warning` | Output written; review `status_reason` and `issues_detail` |
| `failed` | No output; fix rule, file, or standard |
| `skipped_xlsx` | Convert to CSV first |

Warnings are raised for (non-exhaustive): column reorder, scientific notation, non-strict dates, type conversion issues, phantom removed (info), total-like rows, encoding fallback, ragged CSV lines.

---

## Excel report (5 sheets)

| Sheet | Contents |
|-------|----------|
| `file_summary` | Per file: `status`, `output_written`, `layout_status`, `clean_status`, `status_reason`, row counts, paths |
| `issues_detail` | Per issue: `phase` (`pre_clean` / `clean_action` / `post_clean`), `category`, `severity`, `column`, `message`, `sample_rows` |
| `clean_actions` | File-level counts: placeholders, `$`, parens, commas, blank rows dropped |
| `clean_actions_by_column` | Same actions broken down by column |
| `column_stats` | Per column: nulls, conversion issues, scientific notation, date parse breakdown |

---

## Manual type edits in YAML

`python -m src.reader` **re-infers** column `type` from standard row-2 samples on each regenerate. It **does** merge `mappings`, prefixes, `aliases`, and `read`. It does **not** preserve hand-edited `type` (e.g. `Trade_ID: string`). After regenerate, re-check critical columns or fix standard row-2 samples (e.g. use `REF001` not `1234567`).

---

## Changing policy

1. Agree change here (and with audit owners if audit should stay aligned).  
2. Implement in `src/`.  
3. Update `tools/generate_pipeline_fixtures.py` and tests under `tests/`.  
4. Update [docs/clean_pipeline.md](docs/clean_pipeline.md) and README files if user-facing behavior changes.

Do **not** add `clean_policy` keys to YAML unless the team later adopts per-rule overrides in code.
