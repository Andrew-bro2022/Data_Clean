# Audit → clean workflow

How to run **pre-clean audit** and the **main clean pipeline** together on a production batch.  
This doc is the operational guide; details live in linked references.

| Topic | Document |
|-------|----------|
| Audit CLI and report sheets | [audit/README_AUDIT.md](../audit/README_AUDIT.md) · [中文版](../audit/README_AUDIT_CN.md) |
| Clean flow and reading `reports/` | [clean_pipeline.md](clean_pipeline.md) |
| Clean policy (fail vs warn, value rules) | [README_DATA_CLEAN_POLICY.md](../README_DATA_CLEAN_POLICY.md) · [中文版](../README_DATA_CLEAN_POLICY_CN.md) |
| YAML schema and mappings | [config/README.md](../config/README.md) |

---

## Recommended batch workflow

```text
1. Prepare
   └─ raw files in raw/
   └─ config/file_rules.yaml reviewed (mappings, encoding, types)

2. Audit (optional but recommended for new batches)
   └─ python -m audit.main --base-dir .
   └─ Open audit/output/audit_YYYYMMDD_HHMMSS.xlsx

3. Review audit report
   └─ file_summary: filter files with errors / failed status
   └─ issues_detail: structure, dates, placeholders, numeric, phantom, total
   └─ Fix source files or YAML where needed; note accepted risks

4. Clean
   └─ python -m src.main --base-dir .
   └─ Open reports/report_YYYYMMDD_HHMMSS.xlsx

5. Review clean report
   └─ file_summary: failed (no output) vs warning (output written) vs success
   └─ issues_detail: what was auto-fixed vs what needs human review
   └─ output/: use cleaned CSVs downstream

6. Archive (manual today)
   └─ Keep both Excel paths in your run notes (timestamps differ; no shared batch_id yet)
```

### Single-file debug

```bash
python -m audit.main --base-dir . --file raw/teamA/foo.csv
python -m src.main --base-dir . --file raw/teamA/foo.csv
```

### Large files (audit only)

For very large CSVs, audit supports sampling:

```bash
python -m audit.main --base-dir . --max-data-rows 50000
```

Phantom/total checks use the same row window. Re-run without the cap when you need a full-file tail review. Clean reads the full file unless you split inputs yourself.

---

## Where reports go

| Step | Command | Report path |
|------|---------|-------------|
| Audit | `python -m audit.main` | `audit/output/audit_YYYYMMDD_HHMMSS.xlsx` |
| Clean | `python -m src.main` | `reports/report_YYYYMMDD_HHMMSS.xlsx` |

Both use `file_summary` + `issues_detail`. Clean adds `clean_actions`, `clean_actions_by_column`, and `column_stats`.

**Folders skipped by clean (not by audit):** `raw/_audit_fixtures/` is skipped in clean runs; audit can still target it via `--file` or if files appear in the normal raw scan.

---

## How to read audit before clean

### `file_summary` (audit)

Start with roll-up columns:

- `missing_columns` / `extra_columns` — same semantics as clean; clean will **fail** if these are wrong.
- `date_issue_columns`, `numeric_issue_columns`, `placeholder_issue_columns` — quick column lists; drill into `issues_detail`.
- `phantom_issue` / `total_keyword_issue` — `Y` when tail checks fired.
- Note if **sampling** was applied (`max_data_rows`).

### `issues_detail` (audit)

Filter by `severity` = `error` first. Each row has `category`, `column`, `message`, and often sample row numbers.

Use this to decide: **fix file**, **fix YAML**, or **proceed to clean** (see table below).

---

## How to read clean after audit

### `file_summary` (clean)

| `status` | `output_written` | Meaning |
|----------|------------------|---------|
| `failed` | N | No CSV in `output/` — fix and re-run |
| `warning` | Y | CSV written — review `status_reason` |
| `success` | Y | No warnings |
| `skipped_xlsx` | N | Convert to CSV |

Also check `layout_status`, `clean_status`.

### `issues_detail` (clean)

| `phase` | Typical content |
|---------|-----------------|
| `pre_clean` | Layout, read/encoding, scientific notation, total-like rows |
| `clean_action` | Placeholders cleared, `$`, parens, phantom removed |
| `post_clean` | Date non-strict parse, type conversion, scientific preserved in output |

---

## Audit vs clean — same issue, different behavior

This is the main reason to run **both**: audit is a **strict pre-check**; clean is **production output** with auto-fixes per [README_DATA_CLEAN_POLICY.md](../README_DATA_CLEAN_POLICY.md).

| Finding | Audit | Clean | Proceed to clean? |
|---------|-------|-------|-------------------|
| Missing / extra column | Error / reported | **`failed`, no output** | Fix file or YAML first |
| No matching rule | Reported | **`failed`** | Add mapping or standard |
| Header not found | Reported | **`failed`** | Fix file |
| Duplicate column (two `Trade_ID`) | May appear in structure | **`failed`** | Fix headers |
| `-`, `null`, `n/a` (PLACEHOLDER) | **Warning** (clean will clear) | **Cleared to empty** (not a fail) | **Yes** |
| Accounting `(5000)`, `($2,364)` | **Error** on numeric cols | **Converted to negative** | **Yes** — clean fixes this |
| `$` on numeric | Warning | Stripped | Yes |
| Scientific notation | Warning | Warning; float literal kept in output | Yes — verify values |
| Date not strict YAML format | **Error** (strict parse) | Parsed via alternate/serial/infer + **warning** | Yes — verify dates in output |
| Phantom trailer rows | Reported | **Removed** | Yes |
| Total / Grand Total row | Reported | **Kept**, warning only | Yes — confirm not double-counting |
| CSV ragged row / bad line | Reported (structure) | Warn + line numbers, continues | Yes if layout OK |
| Encoding fallback | FILE warning | FILE warning | Yes — consider YAML `encoding` |

**Takeaway:** Audit **errors** on placeholders and accounting parens do **not** mean you must block clean — they mean “raw still has this; clean will transform it.” Audit **structure** errors usually mean clean will **fail** anyway.

---

## Optional hard gate (not implemented)

A future `--require-audit-pass` could block clean when audit has **structure** errors (missing/extra columns, no rule). It should **not** block on PLACEHOLDER or accounting-paren errors that clean is designed to fix.

Today there is **no** automated gate — use the audit report manually before clean.

---

## Optional future improvements (P2)

Not in the repo yet; documented for planning:

| Idea | Benefit |
|------|---------|
| Shared `batch_id` on both reports | Easier to pair audit and clean runs |
| `tools/run_audit_then_clean.py` | One command, two reports, same batch id |
| Merged Excel workbook | Single file for reviewers |

---

## Quick checklist

**Before clean**

- [ ] `file_rules.yaml` mappings match this batch’s raw files  
- [ ] Audit run reviewed (or consciously skipped for a re-clean only)  
- [ ] Structure errors in audit addressed (missing/extra columns)  
- [ ] Accepted: placeholders / parens will change in clean output  

**After clean**

- [ ] No unexpected `failed` in `file_summary`  
- [ ] `warning` rows reviewed (`issues_detail`)  
- [ ] Spot-check `output/` against policy (dates, Trade_ID strings, amounts)  
- [ ] Run notes record both report paths  
