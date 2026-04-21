from __future__ import annotations

from pathlib import Path

from src.types import FileRule
from src.utils import normalize_token


def match_rule(raw_file: Path, rules: dict[str, FileRule], explicit_mapping: dict[str, str]) -> FileRule | None:
    raw_name = raw_file.name
    if raw_name in explicit_mapping:
        std_name = explicit_mapping[raw_name]
        return rules.get(std_name)

    raw_norm = normalize_token(raw_name)
    for rule in rules.values():
        candidates = [rule.standard_file, *rule.aliases]
        if any(normalize_token(candidate) == raw_norm for candidate in candidates):
            return rule
    return None
