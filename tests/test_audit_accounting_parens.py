"""Audit flags accounting parentheses on numeric columns (parsed dataframe)."""

from __future__ import annotations

from pathlib import Path

from audit.checks import check_numeric_column
from audit.profile import audit_file
from src.types import ColumnRule, FileRule
import pandas as pd


def test_check_numeric_column_accounting_parens_unit() -> None:
    s = pd.Series(["5000", "(5000)", "($2,364)", "(note 5)", "($)"])
    issues = check_numeric_column(s, "amount")
    paren_issues = [i for i in issues if "parentheses" in i["message"].lower()]
    assert len(paren_issues) == 1
    assert paren_issues[0]["severity"] == "error"
    assert paren_issues[0]["count"] == 2
    assert set(paren_issues[0]["sample_rows"]) == {2, 3}

    dollar_issues = [i for i in issues if "currency" in i["message"].lower()]
    assert len(dollar_issues) == 1
    assert dollar_issues[0]["severity"] == "warning"
    assert dollar_issues[0]["count"] == 2
    assert set(dollar_issues[0]["sample_rows"]) == {3, 5}


def test_audit_accounting_parens_on_float_column(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    raw_path = raw_dir / "paren_amount.csv"
    raw_path.write_text(
        "amount,name\n"
        "(5000),ok\n"
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
    paren = [
        i
        for i in result.issues
        if i.get("category") == "NUMERIC"
        and i.get("column") == "amount"
        and "parentheses" in str(i.get("message", "")).lower()
    ]
    assert paren
    assert paren[0].get("severity") == "error"
    assert paren[0].get("count") == 1


def test_audit_quoted_paren_cell_detected_after_parse(tmp_path: Path) -> None:
    """Quoted \"($5,001,234)\" is unquoted by pandas; $ warning + parentheses error."""
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    raw_path = raw_dir / "quoted_paren.csv"
    raw_path.write_text(
        "amount,name\n"
        '"($5,001,234)",a\n'
        "200,b\n",
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
    amount_numeric = [i for i in result.issues if i.get("column") == "amount" and i.get("category") == "NUMERIC"]
    paren = [i for i in amount_numeric if "parentheses" in str(i.get("message", "")).lower()]
    dollar = [i for i in amount_numeric if "currency" in str(i.get("message", "")).lower()]
    assert paren and paren[0].get("severity") == "error"
    assert dollar and dollar[0].get("severity") == "warning"
