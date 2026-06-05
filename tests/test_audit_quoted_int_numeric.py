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
    # Comma path wins over generic double-quote warning (if/elif in checks.py).
    assert not any("double quotes" in str(i.get("message", "")).lower() for i in numeric_issues)


def test_audit_flags_quoted_multi_group_thousands_comma(tmp_path: Path) -> None:
    """Raw cell \"2,123,631\" triggers NUMERIC error (quoted comma), not only double-quote warning."""
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    raw_path = raw_dir / "quoted_multi_comma.csv"
    raw_path.write_text(
        "trade_id,desk\n"
        '"2,123,631",DESK_A\n'
        '"10,500",DESK_B\n',
        encoding="utf-8",
    )

    std_key = "Standard.csv"
    rules: dict[str, FileRule] = {
        std_key: FileRule(
            standard_file=std_key,
            read={"encoding": "utf-8", "delimiter": ",", "skiprows": 0},
            columns=[
                ColumnRule(name="trade_id", data_type="int"),
                ColumnRule(name="desk", data_type="string"),
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

    assert not result.error_message
    assert result.header_row_index == 0
    trade_issues = [
        i for i in result.issues if i.get("category") == "NUMERIC" and i.get("column") == "trade_id"
    ]
    assert trade_issues, f"expected NUMERIC on trade_id, got issues: {result.issues!r}"
    comma_err = [i for i in trade_issues if "comma" in str(i.get("message", "")).lower()]
    assert comma_err, "expected quoted-comma error message"
    assert comma_err[0].get("severity") == "error"
    assert comma_err[0].get("count") == 2
    assert not any("double quotes" in str(i.get("message", "")).lower() for i in trade_issues)


def test_collect_numeric_quoting_detects_comma_inside_quotes(tmp_path: Path) -> None:
    """Direct raw-line scan: \"2,123,631\" -> quoted_comma bucket, not quoted_warn."""
    from audit.checks import collect_numeric_quoting_issues_from_raw

    raw_path = tmp_path / "cell.csv"
    raw_path.write_text('amount\n"2,123,631"\n', encoding="utf-8")
    out = collect_numeric_quoting_issues_from_raw(
        raw_path,
        delimiter=",",
        encoding="utf-8",
        skiprows=0,
        header_row_index=0,
        numeric_column_names={"amount"},
    )
    assert out["amount"]["quoted_comma"] == [1]
    assert out["amount"]["quoted_warn"] == []


def test_audit_unquoted_thousands_comma_not_flagged_by_raw_scan(tmp_path: Path) -> None:
    """Unquoted 1,234 as a single field (pipe-delimited) is not matched by current NUMERIC raw regexes."""
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    raw_path = raw_dir / "unquoted_comma.csv"
    raw_path.write_text(
        "amount|name\n"
        "1,234|a\n",
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
    assert not numeric_on_amount, (
        "current audit raw-line NUMERIC checks only cover $, quoted-numeric, and quoted-comma patterns; "
        "plain 1,234 in one field is not flagged"
    )
