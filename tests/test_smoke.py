"""Smoke tests: run from project root with `pytest tests/`."""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


def test_iter_raw_files_one_level_includes_nested_csv() -> None:
    from src.utils import iter_raw_files_one_level

    raw = ROOT / "raw"
    paths = iter_raw_files_one_level(raw)
    names = {p.name for p in paths}
    assert "BA_CVA_ALLOCATION_20241031_20250527.csv" in names
    team_a = raw / "teamA" / "BA_CVA_ALLOCATION_20241031_20250527.csv"
    if team_a.is_file():
        assert team_a in paths


def test_raw_subfolder_under_raw() -> None:
    from src.utils import raw_subfolder_under_raw

    raw_dir = ROOT / "raw"
    root_file = raw_dir / "BA_CVA_ALLOCATION_20241031_20250527.csv"
    nested = raw_dir / "teamA" / "BA_CVA_ALLOCATION_20241031_20250527.csv"
    if root_file.is_file():
        assert raw_subfolder_under_raw(root_file, raw_dir) == ""
    if nested.is_file():
        assert raw_subfolder_under_raw(nested, raw_dir) == "teamA"


def test_mirrored_output_path() -> None:
    from src.utils import mirrored_output_csv_path

    raw_dir = ROOT / "raw"
    out_root = ROOT / "output"
    nested = raw_dir / "teamA" / "BA_CVA_ALLOCATION_20241031_20250527.csv"
    if nested.is_file():
        p = mirrored_output_csv_path(nested, raw_dir, out_root)
        assert p == out_root / "teamA" / "BA_CVA_ALLOCATION_20241031_20250527.csv"


def test_match_rule_path_mapping_priority() -> None:
    from src.file_matcher import match_rule
    from src.reader import load_rules
    from src.types import ColumnRule, FileRule

    cfg = ROOT / "config" / "file_rules.yaml"
    if not cfg.is_file():
        pytest.skip("config/file_rules.yaml missing")

    rules, mappings, _, _, _ = load_rules(cfg)
    if not rules:
        pytest.skip("no rules loaded")

    std_key = next(iter(rules))
    rule_a = rules[std_key]
    tiny = {
        std_key: rule_a,
        "Other.csv": FileRule(
            standard_file="Other.csv",
            read={},
            columns=[ColumnRule(name="x", data_type="string")],
        ),
    }
    raw_dir = ROOT / "raw"
    raw_file = raw_dir / "teamA" / "only_by_mapping.csv"
    # basename maps to Other; path-specific maps to real std
    m = {"only_by_mapping.csv": "Other.csv", "teamA/only_by_mapping.csv": std_key}
    assert match_rule(raw_file, tiny, m, raw_dir, {}) is rule_a


def test_match_rule_raw_prefix() -> None:
    from src.file_matcher import match_rule
    from src.types import ColumnRule, FileRule

    raw_dir = ROOT / "raw"
    rules = {
        "Desk_RWA_r20260205.csv": FileRule(
            standard_file="Desk_RWA_r20260205.csv",
            read={},
            columns=[ColumnRule(name="Desk", data_type="string")],
        ),
    }
    prefixes = {"DESK_STANDALONE_RWA_": "Desk_RWA_r20260205.csv"}
    f = raw_dir / "DESK_STANDALONE_RWA_20990101_20991231.csv"
    assert match_rule(f, rules, {}, raw_dir, prefixes) is rules["Desk_RWA_r20260205.csv"]


def test_canonical_column_key_matches_human_headers() -> None:
    from src.utils import canonical_column_key

    pairs = [
        ("entity_id", "entity id"),
        ("capital_pre_floor", "capital(pre floor)"),
        ("capital_floor", "capital (floor)"),
        ("rwa_pre_floor", "rwa (pre floor)"),
    ]
    for std, raw in pairs:
        assert canonical_column_key(std) == canonical_column_key(raw)


def test_rename_raw_headers_to_standard() -> None:
    from src.utils import rename_raw_headers_to_standard

    standard = [
        "desk",
        "entity_id",
        "capital_pre_floor",
        "capital_floor",
        "rwa_pre_floor",
    ]
    raw = [
        "desk",
        "entity id",
        "capital(pre floor)",
        "capital (floor)",
        "rwa (pre floor)",
    ]
    assert rename_raw_headers_to_standard(raw, standard) == standard


def test_literal_header_missing_and_extra_reports_raw_spellings() -> None:
    from src.utils import literal_header_missing_and_extra, rename_raw_headers_to_standard

    standard = [
        "desk",
        "entity_id",
        "capital_pre_floor",
        "capital_floor",
        "rwa_pre_floor",
    ]
    raw = [
        "desk",
        "entity id",
        "capital(pre floor)",
        "capital (floor)",
        "rwa (pre floor)",
    ]
    missing, extra = literal_header_missing_and_extra(raw, standard)
    assert missing == ["entity_id", "capital_pre_floor", "capital_floor", "rwa_pre_floor"]
    assert extra == ["entity id", "capital(pre floor)", "capital (floor)", "rwa (pre floor)"]
    assert rename_raw_headers_to_standard(raw, standard) == standard


def test_detect_header_row_uses_canonical_keys() -> None:
    from src.header_detector import detect_header_row

    standard = [
        "desk",
        "entity_id",
        "capital_pre_floor",
        "capital_floor",
        "rwa_pre_floor",
    ]
    human_row = [
        "desk",
        "entity id",
        "capital(pre floor)",
        "capital (floor)",
        "rwa (pre floor)",
    ]
    rows = [["noise", "a", "b"], human_row, ["1", "2", "3", "4", "5"]]
    assert detect_header_row(rows, standard, 0.6) == 1


def test_save_cleaned_uses_per_column_date_format(tmp_path: Path) -> None:
    import pandas as pd

    from src.exporter import save_cleaned
    from src.types import ColumnRule

    df = pd.DataFrame(
        {
            "iso_col": pd.to_datetime(["2025-01-02", "2025-03-04"]),
            "us_col": pd.to_datetime(["2025-05-06", "2025-07-08"]),
        }
    )
    rules = [
        ColumnRule(name="iso_col", data_type="date", date_format="%Y-%m-%d"),
        ColumnRule(name="us_col", data_type="date", date_format="%m/%d/%Y"),
    ]
    out = tmp_path / "t.csv"
    save_cleaned(df, out, rules)
    lines = out.read_text(encoding="utf-8").strip().splitlines()
    assert lines[0] == "iso_col,us_col"
    assert lines[1].startswith("2025-01-02,") and lines[1].endswith("05/06/2025")
    assert lines[2].startswith("2025-03-04,") and lines[2].endswith("07/08/2025")
