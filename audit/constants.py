from __future__ import annotations

# Phantom: consecutive rows at file bottom that are mostly empty / comma padding
PHANTOM_MIN_CONSECUTIVE = 6  # "more than 5" rows
PHANTOM_EMPTY_CELL_RATIO = 0.8
PHANTOM_MIN_COLUMNS = 4

# Total-like rows: scan last N data rows (after header) for keywords
TAIL_KEYWORD_SCAN_ROWS = 25
TOTAL_KEYWORDS = ("total", "grand total", "sum")

# Sample at most this many row numbers per issue (1-based data rows)
SAMPLE_ROW_LIMIT = 10
