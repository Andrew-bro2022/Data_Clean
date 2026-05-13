from __future__ import annotations

from collections.abc import Sequence

from src.utils import canonical_column_key


def detect_header_row(preview_rows: list[list[str]], standard_columns: Sequence[str], threshold: float) -> int | None:
    normalized_standard = {canonical_column_key(c) for c in standard_columns}
    required_denominator = max(len(normalized_standard), 1)

    best_index = None
    best_ratio = -1.0
    for idx, row in enumerate(preview_rows):
        row_set = {canonical_column_key(cell) for cell in row if cell and str(cell).strip()}
        matched = len(normalized_standard & row_set)
        ratio = matched / required_denominator
        if ratio > best_ratio:
            best_ratio = ratio
            best_index = idx

    if best_index is None or best_ratio < threshold:
        return None
    return best_index
