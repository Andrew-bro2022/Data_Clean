"""Audit flags scientific notation on numeric and string columns."""

from __future__ import annotations

from pathlib import Path

from audit.checks import check_scientific_notation
from audit.profile import audit_file
from src.types import ColumnRule, FileRule
import pandas as pd


def test_check_scientific_notation_vectorized() -> None:
    s = pd.Series(["12345", "1.23e+05", "REF001", '"2.5E-3"'])
    issues = check_scientific_notation(s, "col")
    assert len(issues) == 1
    assert issues[0]["count"] == 2
    assert issues[0]["severity"] == "warning"
    assert "scientific" in issues[0]["message"].lower()


def test_audit_scientific_on_float_column(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    raw_path = raw_dir / "sci_float.csv"
    raw_path.write_text(
        "amount,name\n"
        "1.23e+05,ok\n"
        "100,normal\n",
        encoding="utf-8",
    )

    std_key = "Standard.csv"
    rules = {
        std_key: FileRule(
            standard_file=std_key,
            read={"encoding": "utf-8", "delimiter": ",", "skiprows": 0},
            columns=[
                ColumnRule(name="amount", data_type="float"),
                ColumnRule(name="name", data_type="string"),
            ],
        ),
    }
    result = audit_file(
        raw_path,
        raw_dir,
        rules,
        {raw_path.name: std_key},
        {},
        0.6,
        {"encoding": "utf-8", "delimiter": ",", "skiprows": 0},
    )
    sci = [
        i
        for i in result.issues
        if i.get("category") == "NUMERIC"
        and i.get("column") == "amount"
        and "scientific" in str(i.get("message", "")).lower()
    ]
    assert sci
    assert sci[0].get("count") == 1


def test_audit_scientific_on_string_trade_id_not_letters(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    raw_path = raw_dir / "sci_id.csv"
    raw_path.write_text(
        "trade_id,desk\n"
        "2.123631E+06,DESK_A\n"
        "REF001,DESK_B\n",
        encoding="utf-8",
    )

    std_key = "Standard.csv"
    rules = {
        std_key: FileRule(
            standard_file=std_key,
            read={"encoding": "utf-8", "delimiter": ",", "skiprows": 0},
            columns=[
                ColumnRule(name="trade_id", data_type="string"),
                ColumnRule(name="desk", data_type="string"),
            ],
        ),
    }
    result = audit_file(
        raw_path,
        raw_dir,
        rules,
        {raw_path.name: std_key},
        {},
        0.6,
        {"encoding": "utf-8", "delimiter": ",", "skiprows": 0},
    )
    sci = [
        i
        for i in result.issues
        if i.get("category") == "NUMERIC"
        and i.get("column") == "trade_id"
        and "scientific" in str(i.get("message", "")).lower()
    ]
    assert sci
    assert sci[0].get("count") == 1
    desk_sci = [i for i in result.issues if i.get("column") == "desk" and "scientific" in str(i.get("message", "")).lower()]
    assert not desk_sci
