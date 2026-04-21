from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

import pandas as pd
import yaml

from src.types import ColumnRule, FileRule

DATE_FORMATS = ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%m-%d-%Y")


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


def build_rules_from_standards(standards_dir: Path, output_yaml: Path, default_read: dict[str, object]) -> dict[str, FileRule]:
    rules: dict[str, FileRule] = {}
    payload: dict[str, object] = {
        "defaults": default_read,
        "header_match_threshold": 0.6,
        "mappings": {},
        "rules": {},
    }

    for path in sorted(standards_dir.glob("*.csv")):
        frame = pd.read_csv(path, header=None, nrows=2, dtype=str)
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

        file_rule = FileRule(
            standard_file=path.name,
            read=dict(default_read),
            columns=column_rules,
            aliases=[path.stem],
        )
        rules[path.name] = file_rule
        payload["rules"][path.name] = {
            "aliases": [path.stem],
            "read": dict(default_read),
            "columns": yaml_columns,
        }

    output_yaml.parent.mkdir(parents=True, exist_ok=True)
    with output_yaml.open("w", encoding="utf-8") as f:
        yaml.safe_dump(payload, f, sort_keys=False, allow_unicode=False)
    return rules


def load_rules(yaml_path: Path) -> tuple[dict[str, FileRule], dict[str, str], float, dict[str, object]]:
    with yaml_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    defaults = data.get("defaults", {})
    mappings = data.get("mappings", {})
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

    return rules, mappings, threshold, defaults


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate config/file_rules.yaml from standards CSV files")
    parser.add_argument("--base-dir", type=Path, default=Path.cwd(), help="Project root directory")
    parser.add_argument("--standards-dir", type=Path, default=None, help="Override standards directory path")
    parser.add_argument("--output-yaml", type=Path, default=None, help="Override output YAML path")
    parser.add_argument("--encoding", type=str, default="utf-8", help="Default CSV encoding")
    parser.add_argument("--delimiter", type=str, default=",", help="Default CSV delimiter")
    parser.add_argument("--skiprows", type=int, default=0, help="Default CSV skiprows")
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
    rules = build_rules_from_standards(standards_dir, output_yaml, default_read)
    print(f"Generated {output_yaml} with {len(rules)} standard rule(s).")


if __name__ == "__main__":
    main()
