from __future__ import annotations

import re

import pandas as pd

NULL_TOKENS = {"", "-", "null", "n/a", "na"}
EURO_NUMERIC_PATTERN = re.compile(r"^-?\d{1,3}(?:\.\d{3})+,\d+$")
QUOTED_PATTERN = re.compile(r'^["\'](.*)["\']$')


def _clean_scalar(value: object) -> str | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None

    text = str(value).strip()
    match = QUOTED_PATTERN.match(text)
    if match:
        text = match.group(1).strip()

    if text.lower() in NULL_TOKENS:
        return None

    text = text.replace("$", "")
    if EURO_NUMERIC_PATTERN.match(text):
        text = text.replace(".", "").replace(",", ".")
    else:
        text = text.replace(",", "")

    text = text.strip()
    if text.lower() in NULL_TOKENS:
        return None
    return text


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    cleaned = df.map(_clean_scalar)
    cleaned = cleaned.dropna(axis=0, how="all")
    cleaned = cleaned.dropna(axis=1, how="all")
    return cleaned
