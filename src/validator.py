from __future__ import annotations

import re

import pandas as pd

from src.types import ColumnDateParseStats, ColumnRule, TypeConversionMeta
from src.value_patterns import is_scientific_notation_text

OUTPUT_DATE_FORMAT = "%Y-%m-%d"
_NUMERIC_TYPES = {"int", "integer", "float", "numeric"}

_COMMON_DATE_FORMATS: tuple[str, ...] = (
    "%Y-%m-%d",
    "%m/%d/%Y",
    "%m/%d/%y",
    "%d/%m/%Y",
    "%d/%m/%y",
    "%Y/%m/%d",
    "%m-%d-%Y",
    "%m-%d-%y",
    "%d-%m-%Y",
    "%Y%m%d",
    "%m%d%Y",
    "%m%d%y",
)

_EXCEL_SERIAL_RE = re.compile(r"^-?\d+(?:\.\d+)?$")


def _alternate_date_formats(primary_fmt: str | None) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    if primary_fmt:
        seen.add(primary_fmt)
    for fmt in _COMMON_DATE_FORMATS:
        if fmt not in seen:
            seen.add(fmt)
            out.append(fmt)
    return out


def _try_excel_serial(text: str) -> pd.Timestamp | None:
    stripped = text.strip().replace(",", "")
    if not _EXCEL_SERIAL_RE.match(stripped):
        return None
    try:
        n = float(stripped)
    except ValueError:
        return None
    if n < 1 or n >= 1_000_000:
        return None
    parsed = pd.to_datetime(n, unit="D", origin="1899-12-30", errors="coerce")
    if pd.isna(parsed):
        return None
    return pd.Timestamp(parsed).normalize()


def _parse_date_cell(text: str, primary_fmt: str | None, stats: ColumnDateParseStats) -> pd.Timestamp:
    stripped = str(text).strip()
    if not stripped:
        return pd.NaT

    if primary_fmt:
        strict = pd.to_datetime(stripped, format=primary_fmt, errors="coerce")
        if pd.notna(strict):
            stats.strict_parsed += 1
            return strict.normalize()

    serial = _try_excel_serial(stripped)
    if serial is not None:
        stats.excel_serial_parsed += 1
        return serial

    for fmt in _alternate_date_formats(primary_fmt):
        parsed = pd.to_datetime(stripped, format=fmt, errors="coerce")
        if pd.notna(parsed):
            stats.alternate_parsed += 1
            return parsed.normalize()

    inferred = pd.to_datetime(stripped, errors="coerce", dayfirst=False)
    if pd.notna(inferred):
        stats.inferred_parsed += 1
        return inferred.normalize()

    stats.failed += 1
    return pd.NaT


def _parse_flexible_dates(
    series: pd.Series,
    primary_fmt: str | None,
) -> tuple[pd.Series, ColumnDateParseStats]:
    s = series.astype("string")
    stats = ColumnDateParseStats()
    parsed = s.map(lambda v: _parse_date_cell(v, primary_fmt, stats))
    return parsed, stats


def _convert_numeric_series(
    source: pd.Series,
    *,
    as_integer: bool,
    preserve_scientific_literals: bool,
) -> tuple[pd.Series, int, int]:
    """Convert to numeric; preserve Excel scientific-notation source text in float columns."""
    preserved = 0
    failed = 0
    out: list[object] = []

    for val in source:
        if val is None or (isinstance(val, float) and pd.isna(val)):
            out.append(pd.NA)
            continue
        text = str(val).strip()
        if not text or text.lower() == "nan":
            out.append(pd.NA)
            continue
        if preserve_scientific_literals and is_scientific_notation_text(text):
            out.append(text)
            preserved += 1
            continue
        num = pd.to_numeric(text, errors="coerce")
        if pd.isna(num):
            failed += 1
            out.append(pd.NA)
            continue
        if as_integer:
            out.append(int(round(float(num))))
        else:
            out.append(float(num))

    dtype: object = "Int64" if as_integer else "object"
    if as_integer and preserved == 0:
        return pd.Series(out, index=source.index, dtype="Int64"), preserved, failed
    return pd.Series(out, index=source.index, dtype=dtype), preserved, failed


def convert_types(
    df: pd.DataFrame,
    column_rules: list[ColumnRule],
) -> tuple[pd.DataFrame, TypeConversionMeta]:
    converted = df.copy()
    issues: dict[str, int] = {}
    date_stats: dict[str, ColumnDateParseStats] = {}
    scientific_preserved: dict[str, int] = {}

    for rule in column_rules:
        if rule.name not in converted.columns:
            continue

        source = converted[rule.name]
        non_null_before = source.notna()
        dtype = rule.data_type.lower()

        if dtype in _NUMERIC_TYPES:
            as_integer = dtype in {"int", "integer"}
            preserve_sci = dtype in {"float", "numeric"}
            numeric, preserved, failed = _convert_numeric_series(
                source,
                as_integer=as_integer,
                preserve_scientific_literals=preserve_sci,
            )
            converted[rule.name] = numeric
            if preserved:
                scientific_preserved[rule.name] = preserved
            if failed:
                issues[rule.name] = failed
        elif dtype in {"date", "datetime"}:
            fmt = rule.date_format if rule.date_format else None
            parsed, stats = _parse_flexible_dates(source, fmt)
            converted[rule.name] = parsed
            date_stats[rule.name] = stats
            failed = int((non_null_before & parsed.isna()).sum())
            if failed:
                issues[rule.name] = failed
        else:
            converted[rule.name] = source.astype("string")

    meta = TypeConversionMeta(
        type_issues={k: v for k, v in issues.items() if v > 0},
        date_stats=date_stats,
        scientific_preserved=scientific_preserved,
    )
    return converted, meta


def derive_status(
    *,
    header_row_found: bool,
    failed: bool,
    has_conversion_issue: bool,
    column_order_realigned: bool = False,
    total_keyword_rows: list[int] | None = None,
    scientific_notation_by_column: dict[str, int] | None = None,
    encoding_configured: str = "",
    encoding_used: str = "",
    csv_bad_line_numbers: list[int] | None = None,
    has_date_inference: bool = False,
) -> str:
    if failed or not header_row_found:
        return "failed"
    encoding_fallback = bool(
        encoding_used
        and encoding_configured
        and encoding_used.lower() != encoding_configured.lower()
    )
    if (
        has_conversion_issue
        or column_order_realigned
        or (total_keyword_rows or [])
        or (scientific_notation_by_column or {})
        or encoding_fallback
        or (csv_bad_line_numbers or [])
        or has_date_inference
    ):
        return "warning"
    return "success"
