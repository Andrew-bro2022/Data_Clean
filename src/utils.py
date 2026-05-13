from __future__ import annotations

import re
from collections.abc import Sequence
from pathlib import Path

DATE_SUFFIX_PATTERN = re.compile(r"(?:_\d{8}(?:_\d{8})?)$", re.IGNORECASE)
VERSION_SUFFIX_PATTERN = re.compile(r"_r\d+$", re.IGNORECASE)


def normalize_token(name: str) -> str:
    stem = Path(name).stem.strip().lower()
    stem = VERSION_SUFFIX_PATTERN.sub("", stem)
    stem = DATE_SUFFIX_PATTERN.sub("", stem)
    return re.sub(r"[\s_]+", "_", stem).strip("_")


def normalize_header_column_name(name: object) -> str:
    """
    Strip outer whitespace and matching single/double quotes from a column label.

    Examples: ``" Trade_ID "`` -> ``Trade_ID``, ``'Amount'`` -> ``Amount``.
    Repeats while the string is wrapped in the same quote character on both ends.
    """
    text = str(name).strip()
    while len(text) >= 2 and text[0] == text[-1] and text[0] in "\"'":
        text = text[1:-1].strip()
    return text


def canonical_column_key(name: object) -> str:
    """
    Stable key for matching human-formatted headers to standard snake_case names.

    Strips non-alphanumeric (spaces, underscores, parentheses, etc.) after lowercasing,
    so e.g. ``entity id``, ``entity_id``, ``Entity ID`` share one key; ``capital(pre floor)``
    matches ``capital_pre_floor``.
    """
    base = normalize_header_column_name(name)
    folded = re.sub(r"[^a-z0-9]+", "", base.lower())
    return folded if folded else base.lower().strip()


def rename_raw_headers_to_standard(raw_headers: Sequence[str], standard_columns: Sequence[str]) -> list[str]:
    """
    For each raw header, if its canonical key matches exactly one standard column's key,
    use the standard name; otherwise keep the raw header. If two raw columns map to the
    same standard, only the first is renamed (others keep raw names).
    """
    key_to_standard: dict[str, str] = {}
    for s in standard_columns:
        key_to_standard.setdefault(canonical_column_key(s), str(s))

    used_standard: dict[str, int] = {}
    out: list[str] = []
    for raw in raw_headers:
        text = str(raw)
        k = canonical_column_key(text)
        std = key_to_standard.get(k)
        if std is None:
            out.append(text)
            continue
        n = used_standard.get(std, 0) + 1
        used_standard[std] = n
        out.append(std if n == 1 else text)
    return out


def preview_rows_for_header_detection(preview: pd.DataFrame) -> list[list[str]]:
    """Build preview matrix for header detection with column-label normalization per cell."""
    rows = preview.fillna("").astype(str).values.tolist()
    out: list[list[str]] = []
    for row in rows:
        out.append([normalize_header_column_name(c) if str(c).strip() else "" for c in row])
    return out


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def iter_raw_files_one_level(raw_dir: Path) -> list[Path]:
    """Collect files directly under raw/ and one subdirectory level only (no deeper nesting)."""
    out: list[Path] = []
    if not raw_dir.is_dir():
        return out
    for p in sorted(raw_dir.glob("*")):
        if p.is_file():
            out.append(p)
    for p in sorted(raw_dir.glob("*/*")):
        if p.is_file():
            out.append(p)
    return out


def raw_subfolder_under_raw(raw_file: Path, raw_dir: Path) -> str:
    """Immediate folder name under raw/, or empty string when the file sits directly under raw/."""
    try:
        rel = raw_file.resolve().relative_to(raw_dir.resolve())
    except ValueError:
        return ""
    parts = rel.parts
    return parts[0] if len(parts) >= 2 else ""


def mirrored_output_csv_path(raw_file: Path, raw_dir: Path, output_root: Path) -> Path:
    """Mirror raw layout under output_root (e.g. raw/a/x.csv -> output/a/x.csv)."""
    rel = raw_file.resolve().relative_to(raw_dir.resolve())
    return output_root / rel
