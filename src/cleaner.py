from __future__ import annotations

import pandas as pd

from src.clean_actions import CleanActionStats
from src.types import ColumnRule
from src.utils import normalize_header_column_name
from src.value_patterns import (
    ACCOUNTING_PARENS,
    EURO_NUMERIC_PATTERN,
    QUOTED_PATTERN,
    is_all_numeric_string_cell,
)

NULL_TOKENS = {"", "-", "–", "—", "null", "n/a", "na"}
_NUMERIC_TYPES = {"int", "integer", "float", "numeric"}
_TEXT_NULLS = {"null", "n/a", "na"}


def _is_null_token(text: str) -> bool:
    if text in NULL_TOKENS:
        return True
    return text.lower() in _TEXT_NULLS


def _unwrap_accounting_parens(text: str) -> str:
    inner = text.strip()[1:-1].strip().replace("$", "").replace(",", "")
    return f"-{inner}" if inner else ""


def _clean_scalar(
    value: object,
    data_type: str,
    stats: CleanActionStats,
    column: str,
) -> str | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None

    raw = str(value).strip()
    text = raw
    match = QUOTED_PATTERN.match(text)
    if match:
        text = match.group(1).strip()

    if _is_null_token(text):
        stats.record(column, "placeholders_cleared")
        return None

    dtype = data_type.lower()
    is_numeric_col = dtype in _NUMERIC_TYPES
    apply_numeric_rules = is_numeric_col or (dtype == "string" and is_all_numeric_string_cell(text))

    if apply_numeric_rules and ACCOUNTING_PARENS.match(text):
        stats.record(column, "accounting_parens_converted")
        text = _unwrap_accounting_parens(text)
        if not text or text == "-":
            return None

    if apply_numeric_rules:
        if "$" in text:
            stats.record(column, "currency_stripped")
        text = text.replace("$", "")
        if EURO_NUMERIC_PATTERN.match(text):
            text = text.replace(".", "").replace(",", ".")
        elif "," in text:
            stats.record(column, "thousands_commas_removed")
            text = text.replace(",", "")

    text = text.strip()
    if text == "" or _is_null_token(text):
        return None
    return text


def _type_by_column(column_rules: list[ColumnRule]) -> dict[str, str]:
    return {rule.name: rule.data_type for rule in column_rules}


def clean_dataframe(
    df: pd.DataFrame,
    column_rules: list[ColumnRule],
) -> tuple[pd.DataFrame, CleanActionStats]:
    out = df.copy()
    out.columns = [normalize_header_column_name(c) for c in out.columns]
    types = _type_by_column(column_rules)
    stats = CleanActionStats()
    cleaned = pd.DataFrame(index=out.index)
    for col in out.columns:
        dtype = types.get(str(col), "string")
        cleaned[col] = out[col].map(lambda v, d=dtype, c=str(col): _clean_scalar(v, d, stats, c))
    rows_before = len(cleaned)
    cleaned = cleaned.dropna(axis=0, how="all")
    stats.all_blank_rows_dropped += rows_before - len(cleaned)
    return cleaned, stats
