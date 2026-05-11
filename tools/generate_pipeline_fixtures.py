from __future__ import annotations

from pathlib import Path

import pandas as pd


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    d = root / "raw" / "pipeline_tests"
    d.mkdir(parents=True, exist_ok=True)

    # 1) Success: quotes + commas + $ get cleaned before numeric conversion.
    write_text(
        d / "BA_CVA_Allocation_r20260217_good.csv",
        "Trade_ID,As_Of_Date,Amount,Currency\n"
        '1,2025-01-15,"1,234.56",USD\n'
        '2,2025-01-16,"$2,345.00",CAD\n',
    )

    # 2) Warning: float conversion issue
    write_text(
        d / "BA_CVA_Allocation_r20260217_bad_amount.csv",
        "Trade_ID,As_Of_Date,Amount,Currency\n" "1,2025-01-15,ABC,USD\n",
    )

    # 3) Warning: int conversion issue
    write_text(
        d / "BA_CVA_Allocation_r20260217_bad_trade_id.csv",
        "Trade_ID,As_Of_Date,Amount,Currency\n" "X,2025-01-15,10.0,USD\n",
    )

    # 4) Success (structure notes only: missing Currency + extra column)
    write_text(
        d / "BA_CVA_Allocation_r20260217_missing_and_extra_cols.csv",
        "Trade_ID,As_Of_Date,Amount,Extra_Col\n" "1,2025-01-15,10.0,note\n",
    )

    # 4b) Multiple extra columns vs BA_CVA
    write_text(
        d / "BA_CVA_Allocation_r20260217_multi_extra.csv",
        "Trade_ID,As_Of_Date,Amount,Currency,Extra_A,Extra_B,Extra_C\n"
        "1,2025-01-15,10.0,USD,a1,b1,c1\n",
    )

    # 4c–e) Wide standard (10 cols): multi missing / multi extra / both (same as audit fixtures)
    write_text(
        d / "Test_Wide_multi_missing.csv",
        "Col_01,Col_02,Col_03,Col_04,Col_05,Col_06\n" "a1,a2,a3,a4,a5,a6\n",
    )
    write_text(
        d / "Test_Wide_multi_extra.csv",
        "Col_01,Col_02,Col_03,Col_04,Col_05,Col_06,Col_07,Col_08,Col_09,Col_10,Extra_A,Extra_B,Extra_C\n"
        "b1,b2,b3,b4,b5,b6,b7,b8,b9,b10,x,y,z\n",
    )
    write_text(
        d / "Test_Wide_multi_missing_and_extra.csv",
        "Col_01,Col_02,Col_03,Col_04,Col_05,Col_06,Extra_A,Extra_B\n" "c1,c2,c3,c4,c5,c6,xa,xb\n",
    )

    write_text(
        d / "Test_Multi_many_date_numeric_issues.csv",
        "Date_A,Date_B,Date_C,Num_A,Num_B,Num_C\n"
        "01/15/2025,01/16/2025,01/17/2025,$10,$20,$30\n",
    )

    for stale in (
        d / "BA_CVA_Allocation_r20260217_multi_missing.csv",
        d / "BA_CVA_Allocation_r20260217_multi_missing_and_extra.csv",
    ):
        if stale.exists():
            stale.unlink()

    # 5) Success: Desk RWA (matches DESK_STANDALONE_RWA_ prefix). Date is MM/DD/YYYY and should parse via inference.
    write_text(
        d / "DESK_STANDALONE_RWA_20260101_20260131.csv",
        "Desk,Reporting_Date,RWA_Value\n" 'ALPHA,01/15/2025,"1,000.50"\n',
    )

    # 6) Failed: header not found (header occurs after preview nrows=30)
    junk = "\n".join(["junk1,junk2,junk3,junk4"] * 40)
    write_text(
        d / "BA_CVA_Allocation_r20260217_header_not_found.csv",
        junk
        + "\n"
        + "Trade_ID,As_Of_Date,Amount,Currency\n"
        + "1,2025-01-15,10.0,USD\n",
    )

    # 7) Failed: no matching standard
    write_text(d / "NO_STANDARD_MATCH_20260101.csv", "A,B,C\n1,2,3\n")

    # 8) Skipped: xlsx
    pd.DataFrame({"A": [1]}).to_excel(d / "SKIPPED_XLSX_TEST.xlsx", index=False)

    # 9) Deeper nesting: should not be processed (raw/*/* only)
    write_text(
        d / "sub" / "BA_CVA_Allocation_r20260217_deep.csv",
        "Trade_ID,As_Of_Date,Amount,Currency\n" "1,2025-01-15,10.0,USD\n",
    )

    print(f"Wrote pipeline fixtures under {d}")


if __name__ == "__main__":
    main()

