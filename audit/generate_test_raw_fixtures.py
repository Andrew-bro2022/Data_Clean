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
