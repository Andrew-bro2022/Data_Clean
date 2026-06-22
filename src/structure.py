from __future__ import annotations

import re
from dataclasses import dataclass

import pandas as pd

from src.utils import canonical_column_key, literal_header_missing_and_extra

_PANDAS_DUP_SUFFIX = re.compile(r"^(?P<base>.+)\.(?P<idx>\d+)$")


def analyze_column_count_and_order(
    standard_ordered: list[str],
    raw_ordered: list[str],
) -> dict:
    """Compare standard vs raw header by position (same semantics as audit.profile)."""
    n_s, n_r = len(standard_ordered), len(raw_ordered)
    count_match = n_s == n_r
    pos: int | None = None
    expected = ""
    found = ""

    for i in range(min(n_s, n_r)):
        if standard_ordered[i] != raw_ordered[i]:
            pos = i + 1
            expected = standard_ordered[i]
            found = raw_ordered[i]
            break
    else:
        if n_s != n_r:
            k = min(n_s, n_r)
            pos = k + 1
            if n_r > n_s:
                expected = "(no further standard column)"
                found = raw_ordered[k] if k < n_r else ""
            else:
                expected = standard_ordered[k] if k < n_s else ""
                found = "(no further raw column)"

    layout_ok = count_match and pos is None
    return {
        "standard_n": n_s,
        "raw_n": n_r,
        "count_match": count_match,
        "layout_ok": layout_ok,
        "first_mismatch_1based": pos,
        "expected": expected,
        "found": found,
    }


def duplicate_column_positions(columns: list[str]) -> dict[str, list[int]]:
    """Map column name -> 1-based positions; only names that appear more than once."""
    by_name: dict[str, list[int]] = {}
    for i, name in enumerate(columns, start=1):
        by_name.setdefault(str(name), []).append(i)
    return {name: pos for name, pos in by_name.items() if len(pos) > 1}


def _effective_header_for_matching(name: str) -> str:
    """Treat pandas duplicate suffixes (``Col.1``) as the same header as ``Col``."""
    m = _PANDAS_DUP_SUFFIX.match(str(name))
    return m.group("base") if m else str(name)


def standard_column_collisions(
    raw_headers: list[str],
    standard_columns: list[str],
) -> dict[str, list[int]]:
    """Multiple raw columns map to the same YAML standard name (post-rename collision)."""
    key_to_standard: dict[str, str] = {}
    for col in standard_columns:
        key_to_standard.setdefault(canonical_column_key(col), str(col))

    by_standard: dict[str, list[int]] = {}
    for i, raw in enumerate(raw_headers, start=1):
        effective = _effective_header_for_matching(raw)
        std = key_to_standard.get(canonical_column_key(effective))
        if std is None:
            continue
        by_standard.setdefault(std, []).append(i)
    return {name: pos for name, pos in by_standard.items() if len(pos) > 1}


def detect_duplicate_columns(
    raw_headers: list[str],
    standard_columns: list[str],
    renamed_headers: list[str],
) -> dict[str, list[int]]:
    """Fail when rename would yield two columns for one standard, or exact duplicate names."""
    collisions = standard_column_collisions(raw_headers, standard_columns)
    for name, positions in duplicate_column_positions(renamed_headers).items():
        if name in collisions:
            collisions[name] = sorted(set(collisions[name]) | set(positions))
        else:
            collisions[name] = positions
    return collisions


def format_duplicate_columns_message(dups: dict[str, list[int]]) -> str:
    parts = [
        f"{name} (columns {', '.join(str(p) for p in positions)})"
        for name, positions in sorted(dups.items())
    ]
    return "Duplicate column names after header rename: " + "; ".join(parts)


def structural_missing_and_extra(
    renamed_columns: list[str],
    standard_columns: list[str],
) -> tuple[list[str], list[str]]:
    """After canonical rename: standard columns absent from df, or df columns not in standard."""
    standard_list = [str(s) for s in standard_columns]
    standard_set = set(standard_list)
    renamed_list = [str(c) for c in renamed_columns]
    missing = [s for s in standard_list if s not in set(renamed_list)]
    extra: list[str] = []
    seen: set[str] = set()
    for c in renamed_list:
        if c not in standard_set and c not in seen:
            extra.append(c)
            seen.add(c)
    return missing, extra


@dataclass
class LayoutGateResult:
    ok: bool
    aligned: pd.DataFrame | None
    missing_columns: list[str]
    extra_columns: list[str]
    literal_missing_columns: list[str]
    literal_extra_columns: list[str]
    column_order_realigned: bool
    error_message: str | None = None


def gate_and_align(
    df: pd.DataFrame,
    *,
    raw_exact_headers: list[str],
    standard_columns: list[str],
) -> LayoutGateResult:
    """
    Fail on missing/extra columns (post-rename). On success, return df with only
    standard columns in YAML order (reorder when the set matches but order differs).
    """
    literal_missing, literal_extra = literal_header_missing_and_extra(
        raw_exact_headers, standard_columns
    )
    renamed_headers = [str(c) for c in df.columns]
    missing, extra = structural_missing_and_extra(renamed_headers, standard_columns)

    if missing:
        return LayoutGateResult(
            ok=False,
            aligned=None,
            missing_columns=missing,
            extra_columns=extra,
            literal_missing_columns=literal_missing,
            literal_extra_columns=literal_extra,
            column_order_realigned=False,
            error_message=f"Missing columns vs standard: {', '.join(missing)}",
        )
    if extra:
        return LayoutGateResult(
            ok=False,
            aligned=None,
            missing_columns=missing,
            extra_columns=extra,
            literal_missing_columns=literal_missing,
            literal_extra_columns=literal_extra,
            column_order_realigned=False,
            error_message=f"Extra columns vs standard: {', '.join(extra)}",
        )

    layout = analyze_column_count_and_order(standard_columns, renamed_headers)
    aligned = df[standard_columns].copy()
    return LayoutGateResult(
        ok=True,
        aligned=aligned,
        missing_columns=[],
        extra_columns=[],
        literal_missing_columns=literal_missing,
        literal_extra_columns=literal_extra,
        column_order_realigned=not layout["layout_ok"],
    )
