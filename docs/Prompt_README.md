# Data Cleaning Pipeline (Python)

## 1. Project Overview

This project aims to build a **Python-based data cleaning pipeline** to process a batch of raw financial data files and generate clean, validated outputs.

### Input
- Around **60 raw files** located in a `raw/` directory
- File types:
  - Mostly `.csv`
  - Some `.xlsx` (temporarily skipped)
- File sizes range from **1MB to 100MB**
- Row count up to **100–70,000 rows**

### Output
- Cleaned `.csv` files saved to `output/`
- Validation reports saved to `reports/`
- Output file name must be **exactly the same as the original raw file name**

---

## 2. Standard Files

Each raw file is associated with a **standard file**, which defines:

- Expected **column names**
- Expected **data types**
- Date format for date columns

### Standard File Format

- Standard files are `.csv` files under `standards/`
- Row 1: column names
- Row 2: sample values (used for type/date-format inference)

### Standard Metadata Generation

- Build a script to read all standard CSV files and generate a single YAML config: `config/file_rules.yaml`
- This YAML is the runtime source of truth for:
  - file mapping rules
  - per-column target types
  - per-column date formats
  - per-file read settings (encoding, delimiter, etc.)

### Matching Rule

Raw files should be matched to standard files using a **normalized prefix**:

Example:

| Raw File | Standard File |
|--------|-------------|
| BA_CVA_ALLOCATION_20241031_20250527.csv | BA_CVA_Allocation_r20260217.csv |

Matching logic:
- Ignore case
- Remove version suffix (e.g., `_r20260217`)
- Remove date suffix only for:
  - `_YYYYMMDD`
  - `_YYYYMMDD_YYYYMMDD`
- Normalize underscores and spacing
- If normalized matching is ambiguous or fails, use explicit mapping from section 7 / `file_rules.yaml`

---

## 3. Data Cleaning Requirements

### 3.1 File-Level Issues
- File names may contain extra spaces
- Some files are `.xlsx`
  - These should be **skipped**
  - Log them in the report as `"skipped_xlsx"`
  - They will be manually converted later

---

### 3.2 Header Issues
- Header row may not be the first row
- There may be irrelevant rows above header

Solution:
- Automatically detect header row by matching against standard file column names
- Rule: `matched_columns / standard_columns >= 60%` is considered a valid header row
- Recommend adding a configurable threshold in YAML (default `0.6`)

---

### 3.3 Structural Issues
- Missing columns may exist
- Extra columns may exist
- Blank rows at bottom (phantom rows)
- Blank columns on the right

Handling:
- Remove fully blank rows and columns
- Do NOT fail on missing/extra columns
- Record them in the report

---

### 3.4 Value-Level Issues

Clean the following:

- Remove leading/trailing spaces
- Convert `-`, empty strings, `" "`, `NULL`, `N/A` → NULL
- Remove commas in numbers (e.g., `1,234`)
- Remove quotes around values
- Remove `$` from currency
- Normalize European numeric format to North American format first (e.g., `1.234,56` -> `1234.56`), then remove thousand separators
- Normalize dates

---

## 4. Data Type Handling

- Use **standard file** to determine expected data types
- All raw data should initially be loaded as **string**
- Apply cleaning BEFORE type conversion
- Convert to target types afterward:
  - numeric
  - date
  - string

### Type Inference from Standard Row 2 (for YAML generation)

- Numeric:
  - If sample value contains decimal point, infer `float`
  - Otherwise infer `int`
- Scientific notation values (e.g., `1e-3`) are **not handled specially** in inference rules
- Date:
  - Infer only from a fixed candidate format set (e.g., `%Y-%m-%d`, `%m/%d/%Y`, `%m/%d/%y`, `%m-%d-%Y`)
  - Different standard files may use different date formats
  - Final chosen date format is stored per column in YAML

### Date Format
- For raw processing, date conversion is applied only when:
  - the raw column name matches a date column defined in YAML
  - then convert using that column's YAML date format

---

## 5. Validation Rules

For each file, generate a report including:

- file name
- processing status:
  - `success`
  - `warning`
  - `failed`
  - `skipped_xlsx`
- detected header row index
- total rows (before / after cleaning)
- missing columns
- extra columns
- type conversion issues (if any)
- null count per column

### Status Definition

- `success`: processed successfully; missing/extra columns are allowed
- `warning`: partially successful, with type conversion issues in some cells
- `failed`: header detection failed, file is unreadable/corrupted, or unrecoverable runtime error
- `skipped_xlsx`: file is `.xlsx` and skipped by design

---

## 6. Output Rules

- Cleaned files:
  - saved in `output/`
  - file name must be identical to original raw file
- Reports:
  - saved in `reports/`
  - format: Excel (`.xlsx`)
  - one report per run, named by timestamp:
    - `report_YYYYMMDD_HHMMSS.xlsx`

### Output Column Policy

- Align columns in standard-file order for the standard-defined part
- Keep extra columns in output (and report them as `extra columns`)
- Do not create missing columns in output (but report them as `missing columns`)

---

## 7. File Mapping Reference

| Standard File | Raw File |
|---|---|
| BA_CVA_Allocation_r20260217.csv | BA_CVA_ALLOCATION_20241031_20250527.csv |
| Book_Sensitivities_r20260205.csv | BOOK_SENSITIVITIES_20241031_20250411.csv |
| Desk_RWA_r20260205.csv | DESK_STANDALONE_RWA_20260227_20260312.csv |
| GBM_Attributed_Capital.csv | GBM_ATTRIBUTED_CAPITAL_20260131_20260219.xlsx |
| GBM_Daily_Transmission.csv | GBM_DAILY_TRANSMISSION_20260227_20260323.xlsx |
| MRC_Book_Reallocated_r20260205.csv | MRC_BOOK_REALLOCATED_20260227_20260312.csv |
| MRC_Book_RWA_r20260205.csv | MRC_BOOK_STANDALONE_RWA_20260227_20260312.csv |
| MRC_BL_RWA_r20260205.csv | MRC_BUSINESS_LINE_STANDALONE_RWA_20251231_20260115.csv |
| Netting_Impact_r20251224.csv | NETTING_IMPACT_20260227_20260330.csv |
| SA_CVA_Allocation_r20260217.csv | SA_CVA_ALLOCATION_20241031_20250821.csv |
| SACVA_Sensitivity_BNS_r20260217.csv | SACVA_SENSITIVITY_PREAGGREG_BNS_EXCL_GT_20250430_20250620.csv |
| SACVA_Sensitivity_ENT_r20260217.csv | SACVA_SENSITIVITY_PREAGGREG_ENTERPRISE_20260227_20260316.csv |
| T_COLL_r20260219.csv | T_COLL_20260227_20260309.csv |
| T_DER_EAD_r20260219.csv | T_DER_EAD_20260227_20260309.csv |
| T_NETSET_r20260219.csv | T_NETSET_20260331_20260415.csv |
| T_SFT_EAD_r20260219.csv | T_SFT_EAD_20260227_20260309.csv |
| T_TRADE_RWA_r20260219.csv | T_TRADE_RWA_20260331_20260415.csv |
| V_SFT_NETSEC_r20260219.csv | V_SFT_NETSEC_NS_20260227_20260309.csv |
| V_SFT_NFX_r20260219.csv | V_SFT_NFX_IN_OUT_20260227_20260309.csv |

---

## 8. Technical Requirements

Use Python with:

- `pandas`
- `pathlib`
- `logging`
- `yaml` or `json` for configuration
- Python `3.10+`

---

## 9. Suggested Project Structure
```
project/
│
├─ raw/
├─ standards/
├─ output/
├─ reports/
├─ config/
│ └─ file_rules.yaml
│
├─ src/
│ ├─ main.py
│ ├─ file_matcher.py
│ ├─ reader.py
│ ├─ header_detector.py
│ ├─ cleaner.py
│ ├─ validator.py
│ ├─ exporter.py
│ └─ utils.py
│
└─ logs/
```


---

## 10. Functional Requirements

The program must:

1. Scan all files in `raw/`
2. Skip `.xlsx` files and log them
3. Match raw files to standard files
4. Load CSV files (as string)
5. Detect header row automatically
6. Clean data
7. Align with standard columns while preserving extra columns
8. Convert types
9. Validate structure
10. Save cleaned file
11. Generate report
12. Generate/update `config/file_rules.yaml` from standard CSV files

---

## 11. Coding Requirements

- Modular design (no monolithic script)
- Use type hints
- Add docstrings
- Include logging
- Handle exceptions gracefully
- Support:
  - batch mode (all files)
  - single file debug mode

---

## 12. Important Constraints

- Do NOT fail entire pipeline due to one file
- Continue processing other files
- All issues must be recorded in reports

---

## 13. Expected Deliverables

Generate:

- Full Python implementation
- Sample config file
- Example usage in `main.py`
