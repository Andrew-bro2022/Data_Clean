"""Audit detects quoted numeric cells in raw CSV for YAML int columns."""

from __future__ import annotations

from pathlib import Path

from audit.profile import audit_file
from src.types import ColumnRule, FileRule


def test_audit_flags_quoted_int_in_raw_for_numeric_column(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    raw_path = raw_dir / "quoted_int.csv"
    raw_path.write_text(
        "amount,name\n"
        '"42",hello\n'
        '"99",world\n',
        encoding="utf-8",
    )

    std_key = "Standard.csv"
    rules: dict[str, FileRule] = {
        std_key: FileRule(
            standard_file=std_key,
            read={"encoding": "utf-8", "delimiter": ",", "skiprows": 0},
            columns=[
                ColumnRule(name="amount", data_type="int"),
                ColumnRule(name="name", data_type="string"),
            ],
        ),
    }
    mappings = {raw_path.name: std_key}
    defaults = {"encoding": "utf-8", "delimiter": ",", "skiprows": 0}

    result = audit_file(
        raw_path,
        raw_dir,
        rules,
        mappings,
        prefix_map={},
        threshold=0.6,
        defaults=defaults,
        max_data_rows=None,
    )

    assert result.header_row_index == 0
    assert result.matched is True
    numeric_issues = [i for i in result.issues if i.get("category") == "NUMERIC"]
    assert numeric_issues, "expected at least one NUMERIC issue for quoted int cells"
    amount_issues = [i for i in numeric_issues if i.get("column") == "amount"]
    assert amount_issues, f"expected NUMERIC on column 'amount', got {numeric_issues!r}"
    assert any("double quotes" in str(i.get("message", "")).lower() for i in amount_issues)


def test_audit_flags_quoted_thousands_comma_in_numeric_column(tmp_path: Path) -> None:
    """Raw cell \"1,234\" triggers NUMERIC error (quoted comma) for int column."""
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    raw_path = raw_dir / "quoted_comma.csv"
    raw_path.write_text(
        "amount,name\n"
        '"1,234",a\n'
        '"5,678",b\n',
        encoding="utf-8",
    )

    std_key = "Standard.csv"
    rules: dict[str, FileRule] = {
        std_key: FileRule(
            standard_file=std_key,
            read={"encoding": "utf-8", "delimiter": ",", "skiprows": 0},
            columns=[
                ColumnRule(name="amount", data_type="int"),
                ColumnRule(name="name", data_type="string"),
            ],
        ),
    }
    mappings = {raw_path.name: std_key}
    defaults = {"encoding": "utf-8", "delimiter": ",", "skiprows": 0}

    result = audit_file(
        raw_path,
        raw_dir,
        rules,
        mappings,
        prefix_map={},
        threshold=0.6,
        defaults=defaults,
        max_data_rows=None,
    )

    assert result.header_row_index == 0
    numeric_issues = [i for i in result.issues if i.get("category") == "NUMERIC" and i.get("column") == "amount"]
    assert numeric_issues, "expected NUMERIC issues on amount for quoted thousands"
    assert any(i.get("severity") == "error" for i in numeric_issues)
    assert any("comma" in str(i.get("message", "")).lower() for i in numeric_issues)


def test_audit_flags_unquoted_thousands_comma_pipe_delimited(tmp_path: Path) -> None:
    """Unquoted 1,234 as one field (pipe delimiter) is flagged as unquoted thousands."""
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    raw_path = raw_dir / "unquoted_comma.csv"
    raw_path.write_text(
        "amount|name\n"
        "1,234|a\n"
        "12,345.67|b\n",
        encoding="utf-8",
    )

    std_key = "Standard.csv"
    rules: dict[str, FileRule] = {
        std_key: FileRule(
            standard_file=std_key,
            read={"encoding": "utf-8", "delimiter": "|", "skiprows": 0},
            columns=[
                ColumnRule(name="amount", data_type="int"),
                ColumnRule(name="name", data_type="string"),
            ],
        ),
    }
    mappings = {raw_path.name: std_key}
    defaults = {"encoding": "utf-8", "delimiter": "|", "skiprows": 0}

    result = audit_file(
        raw_path,
        raw_dir,
        rules,
        mappings,
        prefix_map={},
        threshold=0.6,
        defaults=defaults,
        max_data_rows=None,
    )

    assert result.header_row_index == 0
    numeric_on_amount = [
        i for i in result.issues if i.get("category") == "NUMERIC" and i.get("column") == "amount"
    ]
    assert numeric_on_amount
    assert any(
        "unquoted thousands" in str(i.get("message", "")).lower() for i in numeric_on_amount
    )
    unq = [i for i in numeric_on_amount if "unquoted thousands" in str(i.get("message", "")).lower()]
    assert unq and unq[0].get("count") == 2
