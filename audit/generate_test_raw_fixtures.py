"""One-off generator: writes CSV/XLSX under raw/_audit_fixtures for audit QA.
Run from repo root: python -m audit.generate_test_raw_fixtures"""
from __future__ import annotations

from pathlib import Path

import pandas as pd


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    d = root / "raw" / "_audit_fixtures"
    d.mkdir(parents=True, exist_ok=True)

    (d / "audit_clean_ok.csv").write_text(
        "Trade_ID,As_Of_Date,Amount,Currency\n"
        "1,2025-01-15,1234.56,USD\n"
        "2,2025-01-16,1234.56,CAD\n",
        encoding="utf-8",
    )

    (d / "audit_bad_date.csv").write_text(
        "Trade_ID,As_Of_Date,Amount,Currency\n"
        "1,01/15/2025,100.0,USD\n",
        encoding="utf-8",
    )

    (d / "audit_quoted_numeric.csv").write_text(
        'Trade_ID,As_Of_Date,Amount,Currency\n'
        '1,2025-01-15,"100",USD\n',
        encoding="utf-8",
    )

    (d / "audit_quoted_comma_numeric.csv").write_text(
        'Trade_ID,As_Of_Date,Amount,Currency\n'
        '1,2025-01-15,"1,234.56",USD\n',
        encoding="utf-8",
    )

    (d / "audit_dollar_amount.csv").write_text(
        "Trade_ID,As_Of_Date,Amount,Currency\n"
        "1,2025-01-15,$100.00,USD\n",
        encoding="utf-8",
    )

    (d / "audit_missing_currency.csv").write_text(
        "Trade_ID,As_Of_Date,Amount\n"
        "1,2025-01-15,10.0\n",
        encoding="utf-8",
    )

    (d / "audit_extra_column.csv").write_text(
        "Trade_ID,As_Of_Date,Amount,Currency,Extra_Col\n"
        "1,2025-01-15,10.0,USD,note\n",
        encoding="utf-8",
    )

    # Four columns ⇒ three commas per empty trailing row (not four — that would parse as five fields).
    phantom_rows = "\n".join([",,,"] * 7)
    (d / "audit_phantom_tail.csv").write_text(
        "Trade_ID,As_Of_Date,Amount,Currency\n"
        "1,2025-01-15,1.0,USD\n"
        "2,2025-01-16,2.0,CAD\n"
        f"{phantom_rows}\n",
        encoding="utf-8",
    )

    (d / "audit_total_keyword.csv").write_text(
        "Trade_ID,As_Of_Date,Amount,Currency\n"
        "1,2025-01-15,10.0,USD\n"
        "Grand Total,,,\n",
        encoding="utf-8",
    )

    junk_lines = "\n".join(["junk_a,junk_b,junk_c,junk_d"] * 30)
    (d / "audit_header_not_found.csv").write_text(
        f"{junk_lines}\n"
        "Trade_ID,As_Of_Date,Amount,Currency\n"
        "1,2025-01-15,1.0,USD\n",
        encoding="utf-8",
    )

    # Multiple extra columns vs BA_CVA (4 standard cols + 3 extras).
    (d / "audit_multi_extra.csv").write_text(
        "Trade_ID,As_Of_Date,Amount,Currency,Extra_A,Extra_B,Extra_C\n"
        "1,2025-01-15,10.0,USD,a1,b1,c1\n",
        encoding="utf-8",
    )

    # Wide standard (10 string cols): header match 6/10 >= 0.6 → 4 missing (Col_07–Col_10).
    (d / "audit_wide_multi_missing.csv").write_text(
        "Col_01,Col_02,Col_03,Col_04,Col_05,Col_06\n"
        "a1,a2,a3,a4,a5,a6\n",
        encoding="utf-8",
    )

    (d / "audit_wide_multi_extra.csv").write_text(
        "Col_01,Col_02,Col_03,Col_04,Col_05,Col_06,Col_07,Col_08,Col_09,Col_10,Extra_A,Extra_B,Extra_C\n"
        "b1,b2,b3,b4,b5,b6,b7,b8,b9,b10,x,y,z\n",
        encoding="utf-8",
    )

    (d / "audit_wide_multi_missing_and_extra.csv").write_text(
        "Col_01,Col_02,Col_03,Col_04,Col_05,Col_06,Extra_A,Extra_B\n"
        "c1,c2,c3,c4,c5,c6,xa,xb\n",
        encoding="utf-8",
    )

    # Three date columns with strict-parse failures; three float columns with $ (numeric warnings).
    (d / "audit_many_date_and_numeric_issues.csv").write_text(
        "Date_A,Date_B,Date_C,Num_A,Num_B,Num_C\n"
        "01/15/2025,01/16/2025,01/17/2025,$10,$20,$30\n",
        encoding="utf-8",
    )

    for stale in ("audit_multi_missing.csv", "audit_multi_missing_and_extra.csv"):
        p = d / stale
        if p.exists():
            p.unlink()

    phantom_unmatched = "\n".join([",,,"] * 7)
    (d / "AUDIT_ZZZ_NO_STANDARD_MATCH_20260101.csv").write_text(
        "Col_A,Col_B,Col_C,Col_D\n"
        "x1,x2,x3,x4\n"
        "Grand Total,,,\n"
        f"{phantom_unmatched}\n",
        encoding="utf-8",
    )

    pd.DataFrame({"Sheet1_Col": [1]}).to_excel(d / "audit_skipped.xlsx", index=False)

    print(f"Wrote fixtures under {d}")


if __name__ == "__main__":
    main()
