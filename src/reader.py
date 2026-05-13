from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

import pandas as pd
import yaml

from src.types import ColumnRule, FileRule

# Prefer %Y-%m-%d first: canonical standard for new standard-file row-2 samples.
DATE_FORMATS = ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%m-%d-%Y")


def _mapping_or_empty(value: object) -> dict:
    """Normalize YAML mapping keys: None, explicit null, or non-dict -> {}."""
    if value is None or not isinstance(value, dict):
        return {}
    return dict(value)


def _infer_type_and_format(sample_value: str) -> tuple[str, str | None]:
    text = str(sample_value).strip()
    if "." in text:
        try:
            float(text.replace(",", ""))
            return "float", None
        except ValueError:
            pass
    else:
        try:
            int(text.replace(",", ""))
            return "int", None
        except ValueError:
            pass

    for fmt in DATE_FORMATS:
        try:
            datetime.strptime(text, fmt)
            return "date", fmt
        except ValueError:
            continue
    return "string", None


def build_rules_from_standards(
    standards_dir: Path,
    output_yaml: Path,
    default_read: dict[str, object],
    *,
    merge_existing: bool = True,
) -> tuple[dict[str, FileRule], bool]:
    rules: dict[str, FileRule] = {}
    old_data: dict = {}
    if merge_existing and output_yaml.exists():
        with output_yaml.open("r", encoding="utf-8") as f:
            old_data = yaml.safe_load(f) or {}

    merged_defaults = dict(old_data.get("defaults", {}))
    merged_defaults.update(default_read)

    preserved_mappings = _mapping_or_empty(old_data.get("mappings")) if merge_existing else {}
    preserved_prefixes = _mapping_or_empty(old_data.get("raw_prefix_to_standard")) if merge_existing else {}

    encoding = str(merged_defaults.get("encoding", "utf-8"))
    sep = str(merged_defaults.get("delimiter", ","))
    skiprows = int(merged_defaults.get("skiprows", 0))

    payload: dict[str, object] = {
        "defaults": merged_defaults,
        "header_match_threshold": float(old_data.get("header_match_threshold", 0.6)),
        "mappings": preserved_mappings,
        "raw_prefix_to_standard": preserved_prefixes,
        "rules": {},
    }

    old_rules: dict = old_data.get("rules", {}) if merge_existing else {}

    for path in sorted(standards_dir.glob("*.csv")):
        frame = pd.read_csv(
            path,
            header=None,
            nrows=2,
            dtype=str,
            encoding=encoding,
            sep=sep,
            skiprows=skiprows,
            keep_default_na=False,
        )
        if frame.empty or len(frame) < 2:
            continue
        columns = frame.iloc[0].fillna("").tolist()
        samples = frame.iloc[1].fillna("").tolist()

        column_rules: list[ColumnRule] = []
        yaml_columns: list[dict[str, object]] = []
        for col_name, sample in zip(columns, samples):
            inferred_type, date_format = _infer_type_and_format(sample)
            column_rules.append(ColumnRule(name=col_name, data_type=inferred_type, date_format=date_format))
            item: dict[str, object] = {"name": col_name, "type": inferred_type}
            if date_format:
                item["date_format"] = date_format
            yaml_columns.append(item)

        old_r = old_rules.get(path.name, {})
        read_opts = dict(merged_defaults)
        read_opts.update(old_r.get("read", {}))

        aliases: list[str] = [path.stem]
        for a in old_r.get("aliases", []):
            if a not in aliases:
                aliases.append(a)

        file_rule = FileRule(
            standard_file=path.name,
            read=read_opts,
            columns=column_rules,
            aliases=aliases,
        )
        rules[path.name] = file_rule
        payload["rules"][path.name] = {
            "aliases": aliases,
            "read": read_opts,
            "columns": yaml_columns,
        }

    output_yaml.parent.mkdir(parents=True, exist_ok=True)
    with output_yaml.open("w", encoding="utf-8") as f:
        yaml.safe_dump(payload, f, sort_keys=False, allow_unicode=False)
    if merge_existing:
        print(
            f"Preserved mappings: {len(preserved_mappings)} key(s), "
            f"raw_prefix_to_standard: {len(preserved_prefixes)} key(s)."
        )
    return rules, bool(old_data) and merge_existing


def load_rules(yaml_path: Path) -> tuple[dict[str, FileRule], dict[str, str], float, dict[str, object], dict[str, str]]:
    with yaml_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    defaults = data.get("defaults", {})
    mappings = _mapping_or_empty(data.get("mappings"))
    prefix_to_standard = _mapping_or_empty(data.get("raw_prefix_to_standard"))
    prefix_to_standard = {str(k): str(v) for k, v in prefix_to_standard.items()}
    threshold = float(data.get("header_match_threshold", 0.6))

    raw_rules = data.get("rules", {})
    rules: dict[str, FileRule] = {}
    for standard_file, rule in raw_rules.items():
        cols = []
        for item in rule.get("columns", []):
            cols.append(
                ColumnRule(
                    name=item["name"],
                    data_type=item.get("type", "string"),
                    date_format=item.get("date_format"),
                )
            )

        read_opts = dict(defaults)
        read_opts.update(rule.get("read", {}))
        rules[standard_file] = FileRule(
            standard_file=standard_file,
            read=read_opts,
            columns=cols,
            aliases=rule.get("aliases", []),
        )

    return rules, mappings, threshold, defaults, prefix_to_standard


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate config/file_rules.yaml from standards CSV files")
    parser.add_argument("--base-dir", type=Path, default=Path.cwd(), help="Project root directory")
    parser.add_argument("--standards-dir", type=Path, default=None, help="Override standards directory path")
    parser.add_argument("--output-yaml", type=Path, default=None, help="Override output YAML path")
    parser.add_argument("--encoding", type=str, default="utf-8", help="Default CSV encoding")
    parser.add_argument("--delimiter", type=str, default=",", help="Default CSV delimiter")
    parser.add_argument("--skiprows", type=int, default=0, help="Default CSV skiprows")
    parser.add_argument(
        "--no-merge",
        action="store_true",
        help="Ignore existing file_rules.yaml (reset mappings, raw_prefix_to_standard, and rule merges)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    standards_dir = args.standards_dir or (args.base_dir / "standards")
    output_yaml = args.output_yaml or (args.base_dir / "config" / "file_rules.yaml")
    default_read = {
        "encoding": args.encoding,
        "delimiter": args.delimiter,
        "skiprows": args.skiprows,
    }
    rules, did_merge = build_rules_from_standards(
        standards_dir,
        output_yaml,
        default_read,
        merge_existing=not args.no_merge,
    )
    print(f"Generated {output_yaml} with {len(rules)} standard rule(s).")
    if did_merge:
        print("Merged prior mappings, raw_prefix_to_standard, aliases, read, defaults, and header_match_threshold.")


if __name__ == "__main__":
    main()
