from __future__ import annotations

import pandas as pd

from audit.constants import (
    PHANTOM_EMPTY_CELL_RATIO,
    PHANTOM_MIN_COLUMNS,
    PHANTOM_MIN_CONSECUTIVE,
    SAMPLE_ROW_LIMIT,
    TAIL_KEYWORD_SCAN_ROWS,
    TOTAL_KEYWORDS,
)


def is_phantom_row(values: list[str]) -> bool:
    if len(values) < PHANTOM_MIN_COLUMNS:
        return False
    non_empty = sum(1 for v in values if str(v).strip() != "")
    ratio_empty = 1.0 - (non_empty / len(values))
    return non_empty <= 1 or ratio_empty >= PHANTOM_EMPTY_CELL_RATIO


def remove_phantom_trailer_rows(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Drop a consecutive phantom run at the bottom (same heuristic as audit)."""
    if df.empty:
        return df, 0
    values = df.fillna("").astype(str).values.tolist()
    n = len(values)
    run = 0
    for i in range(n - 1, -1, -1):
        if is_phantom_row(values[i]):
            run += 1
        else:
            break
    if run < PHANTOM_MIN_CONSECUTIVE:
        return df, 0
    trimmed = df.iloc[: n - run].copy()
    return trimmed, run


def scan_total_keyword_rows(df: pd.DataFrame) -> list[int]:
    """1-based row indices in df with total-like keywords (report only; do not drop)."""
    if df.empty:
        return []
    hits: list[int] = []
    n = len(df)
    start = max(0, n - TAIL_KEYWORD_SCAN_ROWS)
    for r in range(start, n):
        row = df.iloc[r]
        parts = " ".join(str(x).lower() for x in row if str(x).strip())
        for kw in TOTAL_KEYWORDS:
            if kw in parts:
                hits.append(r + 1)
                break
    return hits[:SAMPLE_ROW_LIMIT]
