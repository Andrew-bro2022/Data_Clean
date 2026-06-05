"""Audit flags null/missing placeholder tokens on all YAML columns."""

from __future__ import annotations

from pathlib import Path

from audit.checks import check_placeholder_tokens
from audit.profile import audit_file
from src.types import ColumnRule, FileRule
import pandas as pd


def test_check_placeholder_tokens_unit() -> None:
    s = pd.Series(["100", "-", "–", "—", "null", "N/A", "na", "REF001", ""])
    issues = check_placeholder_tokens(s, "col")
    assert len(issues) == 1
    assert issues[0]["category"] == "PLACEHOLDER"
    assert issues[0]["severity"] == "error"
    assert issues[0]["count"] == 6
    assert set(issues[0]["sample_rows"]) == {2, 3, 4, 5, 6, 7}


def test_audit_placeholder_on_numeric_and_string_columns(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    raw_path = raw_dir / "placeholders.csv"
    raw_path.write_text(
        "amount,desk\n"
        "-,DESK_A\n"
        "100,n/a\n",
        encoding="utf-8",
    )

    std_key = "Standard.csv"
    rules = {
        std_key: FileRule(
            standard_file=std_key,
            read={"encoding": "utf-8", "delimiter": ",", "skiprows": 0},
            columns=[
                ColumnRule(name="amount", data_type="float"),
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
    placeholder = [i for i in result.issues if i.get("category") == "PLACEHOLDER"]
    assert len(placeholder) == 2
    by_col = {i["column"]: i for i in placeholder}
    assert by_col["amount"]["count"] == 1
    assert by_col["desk"]["count"] == 1
    assert all(i["severity"] == "error" for i in placeholder)


def test_audit_quoted_dash_detected_after_parse(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    raw_path = raw_dir / "quoted_dash.csv"
    raw_path.write_text(
        "amount,name\n"
        '"-",ok\n',
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
    placeholder = [i for i in result.issues if i.get("category") == "PLACEHOLDER" and i.get("column") == "amount"]
    assert placeholder
    assert placeholder[0]["count"] == 1
