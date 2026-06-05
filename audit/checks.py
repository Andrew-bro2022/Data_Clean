from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

import pandas as pd

from audit.constants import (
    PHANTOM_EMPTY_CELL_RATIO,
    PHANTOM_MIN_COLUMNS,
    PHANTOM_MIN_CONSECUTIVE,
    SAMPLE_ROW_LIMIT,
    TAIL_KEYWORD_SCAN_ROWS,
    TOTAL_KEYWORDS,
)
from src.types import ColumnRule
from src.utils import canonical_column_key, normalize_header_column_name

QUOTED_NUMERIC = re.compile(r'^\s*"\s*[\d$.,\s]+\s*"\s*$')
# Quoted chunk containing comma between digits (e.g. "1,234")
QUOTED_COMMA_NUMBER = re.compile(r'"[^"]*\d[^"]*,\s*\d[^"]*"')
# Mantissa with exponent (e.g. 1.23e+05, 2E-3, 1e6); case-insensitive e/E
SCIENTIFIC_NOTATION = re.compile(r"(?i)^(?:\d+\.?\d*|\.\d+)[eE][+-]?\d+$")
# Accounting negative: parentheses around optional $ and digits (e.g. (5000), ($2,364))
ACCOUNTING_PARENS = re.compile(r"^\s*\(\s*(?:\$?\s*)?[\d,.\s]*\d[\d,.\s]*\s*\)\s*$")
DASH_PLACEHOLDERS = frozenset({"-", "–", "—"})
TEXT_NULL_PLACEHOLDERS = frozenset({"null", "n/a", "na"})


def _sample_rows(rows: list[int]) -> list[int]:
    return sorted(set(rows))[:SAMPLE_ROW_LIMIT]


def _cell_text_for_scientific_check(val: object) -> str:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return ""
    return normalize_header_column_name(val)


def _is_null_placeholder_token(text: str) -> bool:
    stripped = text.strip()
    if stripped in DASH_PLACEHOLDERS:
        return True
    return stripped.lower() in TEXT_NULL_PLACEHOLDERS


def check_placeholder_tokens(series: pd.Series, col_name: str) -> list[dict]:
    """Flag dash / null / n/a / na placeholders (aligned with cleaner NULL_TOKENS, minus empty)."""
    bad_rows: list[int] = []
    for i, val in enumerate(series, start=1):
        if val is None or (isinstance(val, float) and pd.isna(val)):
            continue
        text = normalize_header_column_name(val)
        if text == "":
            continue
        if _is_null_placeholder_token(text):
            bad_rows.append(i)
    if not bad_rows:
        return []
    return [
        {
            "category": "PLACEHOLDER",
            "severity": "error",
            "column": col_name,
            "message": (
                "Cell is null/missing placeholder (e.g. -, –, —, null, n/a) "
                "— will be cleaned as empty"
            ),
            "count": len(bad_rows),
            "sample_rows": _sample_rows(bad_rows),
        }
    ]


def check_scientific_notation(series: pd.Series, col_name: str) -> list[dict]:
    """Flag cells whose value is scientific notation (common after Excel re-save of CSV)."""
    normalized = series.map(_cell_text_for_scientific_check)
    non_empty = normalized.str.len() > 0
    hits = normalized.str.match(SCIENTIFIC_NOTATION, na=False) & non_empty
    if not hits.any():
        return []
    bad_rows = [i + 1 for i, flag in enumerate(hits) if flag]
    return [
        {
            "category": "NUMERIC",
            "severity": "warning",
            "column": col_name,
            "message": (
                "Scientific notation (e.g. 1.23e+05) — often from Excel CSV export; "
                "use plain decimal digits or restore the original file"
            ),
            "count": len(bad_rows),
            "sample_rows": _sample_rows(bad_rows),
        }
    ]


def check_dates_strict(series: pd.Series, col_name: str, fmt: str) -> list[dict]:
    issues: list[dict] = []
    bad_rows: list[int] = []
    for i, val in enumerate(series, start=1):
        if val is None or (isinstance(val, float) and pd.isna(val)):
            continue
        text = str(val).strip()
        if text == "":
            continue
        try:
            datetime.strptime(text, fmt)
        except ValueError:
            bad_rows.append(i)
    if bad_rows:
        issues.append(
            {
                "category": "DATE",
                "severity": "warning",
                "column": col_name,
                "message": f"Strict parse failed for date_format={fmt!r}",
                "count": len(bad_rows),
                "sample_rows": _sample_rows(bad_rows),
            }
        )
    return issues


def split_csv_raw_fields(line: str, delimiter: str) -> list[str]:
    """Split one CSV row into raw field strings while preserving enclosing double quotes."""
    fields: list[str] = []
    field: list[str] = []
    i = 0
    n = len(line.rstrip("\r\n"))
    dl = len(delimiter)

    def push() -> None:
        fields.append("".join(field))
        field.clear()

    while i < n:
        ch = line[i]
        if ch == '"':
            field.append('"')
            i += 1
            while i < n:
                field.append(line[i])
                if line[i] == '"':
                    i += 1
                    break
                i += 1
            continue
        if i + dl <= n and line[i : i + dl] == delimiter:
            push()
            i += dl
            continue
        field.append(ch)
        i += 1
    push()
    return fields


def collect_numeric_quoting_issues_from_raw(
    path: Path,
    *,
    delimiter: str,
    encoding: str,
    skiprows: int,
    header_row_index: int,
    numeric_column_names: set[str],
) -> dict[str, dict[str, list[int]]]:
    """
    Map column -> {'quoted_comma': rows, 'quoted_warn': rows}.
    Rows are 1-based indices aligned with dataframe data rows after the header row.

    Scientific notation is checked on the parsed dataframe (see ``check_scientific_notation``).
    """
    text = path.read_text(encoding=encoding, errors="replace")
    lines = [ln.rstrip("\r\n") for ln in text.splitlines()]
    body = lines[skiprows:]
    if header_row_index < 0 or header_row_index >= len(body):
        return {}

    header_fields = split_csv_raw_fields(body[header_row_index], delimiter)
    pos_by_canonical: dict[str, int] = {}
    for idx, h in enumerate(header_fields):
        pos_by_canonical[canonical_column_key(normalize_header_column_name(h))] = idx

    per_col: dict[str, dict[str, list[int]]] = {c: {"quoted_comma": [], "quoted_warn": []} for c in numeric_column_names}

    for row_i, line in enumerate(body[header_row_index + 1 :], start=1):
        if not line.strip():
            continue
        fields = split_csv_raw_fields(line, delimiter)
        for col_name in numeric_column_names:
            pos = pos_by_canonical.get(canonical_column_key(col_name))
            if pos is None or pos >= len(fields):
                continue
            raw_cell = fields[pos]
            if QUOTED_COMMA_NUMBER.search(raw_cell):
                per_col[col_name]["quoted_comma"].append(row_i)
            elif QUOTED_NUMERIC.match(raw_cell.strip()):
                per_col[col_name]["quoted_warn"].append(row_i)
    return per_col


def check_numeric_column(series: pd.Series, col_name: str) -> list[dict]:
    """`$`, accounting parentheses, etc. from parsed cells. Quoted findings use raw line scan."""
    issues: list[dict] = []
    dollar_warn: list[int] = []
    accounting_paren_err: list[int] = []

    for i, val in enumerate(series, start=1):
        if val is None or (isinstance(val, float) and pd.isna(val)):
            continue
        text = str(val).strip()
        if text == "":
            continue
        if "$" in text:
            dollar_warn.append(i)
        if ACCOUNTING_PARENS.match(text):
            accounting_paren_err.append(i)

    if dollar_warn:
        issues.append(
            {
                "category": "NUMERIC",
                "severity": "warning",
                "column": col_name,
                "message": "Cell contains $ (currency) in numeric column",
                "count": len(dollar_warn),
                "sample_rows": _sample_rows(dollar_warn),
            }
        )
    if accounting_paren_err:
        issues.append(
            {
                "category": "NUMERIC",
                "severity": "error",
                "column": col_name,
                "message": (
                    "Cell uses accounting parentheses for negative amount "
                    "(e.g. (5000) or ($2,364))"
                ),
                "count": len(accounting_paren_err),
                "sample_rows": _sample_rows(accounting_paren_err),
            }
        )
    return issues


def is_phantom_row(values: list[str]) -> bool:
    if len(values) < PHANTOM_MIN_COLUMNS:
        return False
    non_empty = sum(1 for v in values if str(v).strip() != "")
    ratio_empty = 1.0 - (non_empty / len(values))
    return non_empty <= 1 or ratio_empty >= PHANTOM_EMPTY_CELL_RATIO


def check_phantom_trailer(df: pd.DataFrame) -> list[dict]:
    if df.empty or len(df.columns) < PHANTOM_MIN_COLUMNS:
        return []
    issues: list[dict] = []
    values_matrix = df.fillna("").astype(str).values.tolist()
    n = len(values_matrix)
    consecutive = 0
    phantom_indices: list[int] = []
    for r in range(n - 1, -1, -1):
        row_vals = list(values_matrix[r])
        if is_phantom_row(row_vals):
            consecutive += 1
            phantom_indices.append(r + 1)
        else:
            break
    if consecutive >= PHANTOM_MIN_CONSECUTIVE:
        issues.append(
            {
                "category": "PHANTOM",
                "severity": "warning",
                "column": None,
                "message": f"Trailing block of {consecutive} mostly-empty / comma-padding rows (bottom of file)",
                "count": consecutive,
                "sample_rows": sorted(phantom_indices)[:SAMPLE_ROW_LIMIT],
            }
        )
    return issues


def check_total_keywords(df: pd.DataFrame) -> list[dict]:
    if df.empty:
        return []
    issues: list[dict] = []
    n = len(df)
    start = max(0, n - TAIL_KEYWORD_SCAN_ROWS)
    hits: list[tuple[int, str]] = []
    for r in range(start, n):
        row = df.iloc[r]
        parts = " ".join(str(x).lower() for x in row if str(x).strip())
        for kw in TOTAL_KEYWORDS:
            if kw in parts:
                hits.append((r + 1, kw))
                break
    if hits:
        sample = hits[:SAMPLE_ROW_LIMIT]
        issues.append(
            {
                "category": "TOTAL",
                "severity": "info",
                "column": None,
                "message": f"Keyword match in last {TAIL_KEYWORD_SCAN_ROWS} rows: {TOTAL_KEYWORDS}",
                "count": len(hits),
                "sample_rows": [h[0] for h in sample],
            }
        )
    return issues


def run_value_checks(
    df: pd.DataFrame,
    column_rules: list[ColumnRule],
    *,
    raw_path: Path | None = None,
    read_opts: dict | None = None,
    header_row_index: int | None = None,
) -> list[dict]:
    all_issues: list[dict] = []
    numeric_types = {"int", "integer", "float", "numeric"}
    numeric_names: set[str] = set()
    scientific_names: set[str] = set()

    for rule in column_rules:
        if rule.name not in df.columns:
            continue
        s = df[rule.name]
        t = rule.data_type.lower()
        if t in {"date", "datetime"} and rule.date_format:
            all_issues.extend(check_dates_strict(s, rule.name, rule.date_format))
        all_issues.extend(check_placeholder_tokens(s, rule.name))
        if t in numeric_types:
            numeric_names.add(rule.name)
            scientific_names.add(rule.name)
            all_issues.extend(check_numeric_column(s, rule.name))
            all_issues.extend(check_scientific_notation(s, rule.name))
        elif t == "string":
            scientific_names.add(rule.name)
            all_issues.extend(check_scientific_notation(s, rule.name))

    if (
        raw_path is not None
        and read_opts is not None
        and header_row_index is not None
        and numeric_names
        and raw_path.is_file()
    ):
        delim = str(read_opts.get("delimiter", ","))
        encoding = str(read_opts.get("encoding", "utf-8"))
        skiprows = int(read_opts.get("skiprows", 0))
        raw_quoting = collect_numeric_quoting_issues_from_raw(
            raw_path,
            delimiter=delim,
            encoding=encoding,
            skiprows=skiprows,
            header_row_index=header_row_index,
            numeric_column_names=numeric_names,
        )
        for col_name, buckets in raw_quoting.items():
            quoted_comma = buckets["quoted_comma"]
            quoted_warn = buckets["quoted_warn"]
            if quoted_comma:
                all_issues.append(
                    {
                        "category": "NUMERIC",
                        "severity": "error",
                        "column": col_name,
                        "message": 'Quoted numeric contains comma (e.g. "1,234") — escalate review',
                        "count": len(quoted_comma),
                        "sample_rows": _sample_rows(quoted_comma),
                    }
                )
            if quoted_warn:
                all_issues.append(
                    {
                        "category": "NUMERIC",
                        "severity": "warning",
                        "column": col_name,
                        "message": "Numeric-looking value wrapped in double quotes",
                        "count": len(quoted_warn),
                        "sample_rows": _sample_rows(quoted_warn),
                    }
                )
    all_issues.extend(check_phantom_trailer(df))
    all_issues.extend(check_total_keywords(df))
    return all_issues
