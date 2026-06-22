from __future__ import annotations

import re

from src.utils import normalize_header_column_name

# Excel-style scientific notation (aligned with audit/checks.py).
SCIENTIFIC_NOTATION = re.compile(
    r"(?i)^(?:"
    r"(?:\d+\.\d+|\.\d+)[eE][+-]?\d+"
    r"|\d+[eE][+-]\d+"
    r")$"
)

ACCOUNTING_PARENS = re.compile(r"^\s*\(\s*(?:\$?\s*)?[\d,.\s]*\d[\d,.\s]*\s*\)\s*$")

# Numeric-looking string cell: optional $, digits/commas/dots; no letters.
ALL_NUMERIC_STRING_CELL = re.compile(r"^\s*\$?\s*-?[\d,.\s]+\s*$")

EURO_NUMERIC_PATTERN = re.compile(r"^-?\d{1,3}(?:\.\d{3})+,\d+$")
QUOTED_PATTERN = re.compile(r'^["\'](.*)["\']$')


def normalized_cell_text(val: object) -> str:
    if val is None:
        return ""
    return normalize_header_column_name(val)


def is_scientific_notation_text(text: str) -> bool:
    return bool(text) and bool(SCIENTIFIC_NOTATION.match(text.strip()))


def is_accounting_parens_text(text: str) -> bool:
    return bool(text) and bool(ACCOUNTING_PARENS.match(text.strip()))


def is_all_numeric_string_cell(text: str) -> bool:
    """True for cells like 1,234 or $100 — not REF001 or 75512E101."""
    stripped = text.strip()
    if not stripped or not ALL_NUMERIC_STRING_CELL.match(stripped):
        return False
    if not any(ch.isdigit() for ch in stripped):
        return False
    if re.search(r"[a-zA-Z]", stripped):
        return False
    return True
