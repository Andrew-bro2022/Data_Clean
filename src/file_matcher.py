from __future__ import annotations

from pathlib import Path

from src.types import FileRule
from src.utils import normalize_token


def match_rule(
    raw_file: Path,
    rules: dict[str, FileRule],
    explicit_mapping: dict[str, str],
    raw_dir: Path,
    prefix_to_standard: dict[str, str] | None = None,
) -> FileRule | None:
    try:
        rel_posix = raw_file.resolve().relative_to(raw_dir.resolve()).as_posix()
    except ValueError:
        rel_posix = ""

    if rel_posix and rel_posix in explicit_mapping:
        std_name = explicit_mapping[rel_posix]
        return rules.get(std_name)

    raw_name = raw_file.name
    if raw_name in explicit_mapping:
        std_name = explicit_mapping[raw_name]
        return rules.get(std_name)

    if prefix_to_standard:
        for prefix in sorted(prefix_to_standard.keys(), key=len, reverse=True):
            if raw_name.startswith(prefix):
                std_name = prefix_to_standard[prefix]
                hit = rules.get(std_name)
                if hit is not None:
                    return hit

    raw_norm = normalize_token(raw_name)
    for rule in rules.values():
        candidates = [rule.standard_file, *rule.aliases]
        if any(normalize_token(candidate) == raw_norm for candidate in candidates):
            return rule
    return None
