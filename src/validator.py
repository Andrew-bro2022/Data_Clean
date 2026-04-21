from __future__ import annotations

import pandas as pd

from src.types import ColumnRule


def convert_types(df: pd.DataFrame, column_rules: list[ColumnRule]) -> tuple[pd.DataFrame, dict[str, int]]:
    converted = df.copy()
    issues: dict[str, int] = {}

    for rule in column_rules:
        if rule.name not in converted.columns:
            continue

        source = converted[rule.name]
        non_null_before = source.notna()

        if rule.data_type.lower() in {"int", "integer", "float", "numeric"}:
            numeric = pd.to_numeric(source, errors="coerce")
            if rule.data_type.lower() in {"int", "integer"}:
                numeric = numeric.round().astype("Int64")
            converted[rule.name] = numeric
            issues[rule.name] = int((non_null_before & numeric.isna()).sum())
        elif rule.data_type.lower() in {"date", "datetime"}:
            fmt = rule.date_format if rule.date_format else None
            parsed = pd.to_datetime(source, format=fmt, errors="coerce")
            converted[rule.name] = parsed
            issues[rule.name] = int((non_null_before & parsed.isna()).sum())
        else:
            converted[rule.name] = source.astype("string")
            issues[rule.name] = 0

    return converted, {k: v for k, v in issues.items() if v > 0}


def derive_status(header_row_found: bool, has_conversion_issue: bool, failed: bool) -> str:
    if failed or not header_row_found:
        return "failed"
    if has_conversion_issue:
        return "warning"
    return "success"
