from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ColumnCleanActionCounts:
    placeholders_cleared: int = 0
    currency_stripped: int = 0
    accounting_parens_converted: int = 0
    thousands_commas_removed: int = 0


@dataclass
class CleanActionStats:
    placeholders_cleared: int = 0
    currency_stripped: int = 0
    accounting_parens_converted: int = 0
    thousands_commas_removed: int = 0
    all_blank_rows_dropped: int = 0
    by_column: dict[str, ColumnCleanActionCounts] = field(default_factory=dict)

    def record(self, column: str, action: str, n: int = 1) -> None:
        total = getattr(self, action, None)
        if total is None:
            return
        setattr(self, action, total + n)
        col_stats = self.by_column.setdefault(column, ColumnCleanActionCounts())
        setattr(col_stats, action, getattr(col_stats, action) + n)

    def as_dict(self) -> dict[str, int]:
        return {
            "placeholders_cleared": self.placeholders_cleared,
            "currency_stripped": self.currency_stripped,
            "accounting_parens_converted": self.accounting_parens_converted,
            "thousands_commas_removed": self.thousands_commas_removed,
            "all_blank_rows_dropped": self.all_blank_rows_dropped,
        }


def count_non_null_cells(series) -> int:
    """Non-empty cells in a string series (before or after clean)."""
    import pandas as pd

    if series is None or len(series) == 0:
        return 0
    s = series.fillna("").astype(str).str.strip()
    return int((s != "").sum())
