# Audit package — developer notes

English module-level docs for Python code under `audit/`. For **how to run** the tool, CLI flags, and how to read the Excel workbook, see [`../README_AUDIT.md`](../README_AUDIT.md).

## Modules (Python files)

| File | Doc |
|------|-----|
| `main.py` | [main.md](main.md) — CLI entry, `run_audit`, wiring to `src`. |
| `profile.py` | [profile.md](profile.md) — `audit_file`, CSV reads, `FileAuditResult`, alignment with cleaning. |
| `checks.py` | [checks.md](checks.md) — `run_value_checks`, issue dict shape, categories. |
| `reporter.py` | [reporter.md](reporter.md) — Excel output, summary roll-ups. |
| `constants.py` | [constants.md](constants.md) — thresholds and fallbacks. |
| `generate_test_raw_fixtures.py` | [generate_test_raw_fixtures.md](generate_test_raw_fixtures.md) — synthetic raw files for QA. |
| `__init__.py` | Package marker only; no runtime logic. |

## Relationship to `src/`

Audit **does not** run cleaning. It reuses **`src.reader.load_rules`**, **`src.file_matcher.match_rule`**, **`src.header_detector.detect_header_row`**, and helpers in **`src.utils`** (header preview, column rename, raw layout) so decisions match the main pipeline as far as rules and headers go. See each module doc above for exact imports.
