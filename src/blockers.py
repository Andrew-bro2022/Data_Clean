from __future__ import annotations

import pandas as pd

from src.types import ColumnRule
from src.value_patterns import is_scientific_notation_text, normalized_cell_text

_NUMERIC_TYPES = {"int", "integer", "float", "numeric"}
_SAMPLE_LIMIT = 10


def scan_scientific_notation(
    df: pd.DataFrame,
    column_rules: list[ColumnRule],
) -> dict[str, int]:
    """
    Count cells in numeric or string YAML columns that use Excel-style scientific
    notation. Values are left unchanged; callers record warnings in the report.
    """
    check_types = _NUMERIC_TYPES | {"string"}
    counts: dict[str, int] = {}

    for rule in column_rules:
        if rule.data_type.lower() not in check_types:
            continue
        if rule.name not in df.columns:
            continue
        n = 0
        for val in df[rule.name]:
            text = normalized_cell_text(val)
            if text and is_scientific_notation_text(text):
                n += 1
        if n:
            counts[rule.name] = n

    return counts


def scientific_notation_warning_message(counts: dict[str, int]) -> str:
    if not counts:
        return ""
    parts = [f"{col} ({n})" for col, n in sorted(counts.items())]
    return (
        "Scientific notation present (float columns written as literal source text): "
        + ", ".join(parts)
    )
