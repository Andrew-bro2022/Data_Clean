from __future__ import annotations

import re
from pathlib import Path

DATE_SUFFIX_PATTERN = re.compile(r"(?:_\d{8}(?:_\d{8})?)$", re.IGNORECASE)
VERSION_SUFFIX_PATTERN = re.compile(r"_r\d+$", re.IGNORECASE)


def normalize_token(name: str) -> str:
    stem = Path(name).stem.strip().lower()
    stem = VERSION_SUFFIX_PATTERN.sub("", stem)
    stem = DATE_SUFFIX_PATTERN.sub("", stem)
    return re.sub(r"[\s_]+", "_", stem).strip("_")


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
