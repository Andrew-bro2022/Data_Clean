from __future__ import annotations

import argparse
import logging
from pathlib import Path

import pandas as pd

from src.cleaner import clean_dataframe
from src.exporter import save_cleaned, save_report_excel
from src.file_matcher import match_rule
from src.header_detector import detect_header_row
from src.reader import build_rules_from_standards, load_rules
from src.types import ProcessingResult
from src.validator import convert_types, derive_status


def setup_logging(log_dir: Path) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(log_dir / "pipeline.log", encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )


def process_file(raw_file: Path, rule, threshold: float, output_dir: Path) -> ProcessingResult:
    if raw_file.suffix.lower() == ".xlsx":
        return ProcessingResult(
            file_name=raw_file.name,
            status="skipped_xlsx",
            header_row_index=None,
            rows_before=0,
            rows_after=0,
            missing_columns=[],
            extra_columns=[],
            type_conversion_issues={},
            null_count_by_column={},
        )

    try:
        read_opts = dict(rule.read)
        delimiter = read_opts.get("delimiter", ",")
        encoding = read_opts.get("encoding", "utf-8")
        skiprows = int(read_opts.get("skiprows", 0))

        preview = pd.read_csv(
            raw_file,
            header=None,
            dtype=str,
            nrows=30,
            keep_default_na=False,
            sep=delimiter,
            encoding=encoding,
            skiprows=skiprows,
        )
        header_idx = detect_header_row(preview.fillna("").values.tolist(), [c.name for c in rule.columns], threshold)
        if header_idx is None:
            return ProcessingResult(
                file_name=raw_file.name,
                status="failed",
                header_row_index=None,
                rows_before=0,
                rows_after=0,
                missing_columns=[],
                extra_columns=[],
                type_conversion_issues={},
                null_count_by_column={},
                error_message="Header row not found",
            )

        df = pd.read_csv(
            raw_file,
            dtype=str,
            header=header_idx,
            keep_default_na=False,
            sep=delimiter,
            encoding=encoding,
            skiprows=skiprows,
        )
        rows_before = len(df)
        cleaned = clean_dataframe(df)

        standard_cols = [c.name for c in rule.columns]
        missing = [c for c in standard_cols if c not in cleaned.columns]
        extra = [c for c in cleaned.columns if c not in standard_cols]

        ordered = [c for c in standard_cols if c in cleaned.columns]
        aligned = cleaned[ordered + extra]

        converted, issues = convert_types(aligned, rule.columns)
        null_counts = converted.isna().sum().astype(int).to_dict()
        status = derive_status(header_row_found=True, has_conversion_issue=bool(issues), failed=False)
        output_path = save_cleaned(converted, output_dir, raw_file.name)

        return ProcessingResult(
            file_name=raw_file.name,
            status=status,
            header_row_index=header_idx,
            rows_before=rows_before,
            rows_after=len(converted),
            missing_columns=missing,
            extra_columns=extra,
            type_conversion_issues=issues,
            null_count_by_column=null_counts,
            output_path=output_path,
        )
    except Exception as exc:  # noqa: BLE001
        return ProcessingResult(
            file_name=raw_file.name,
            status="failed",
            header_row_index=None,
            rows_before=0,
            rows_after=0,
            missing_columns=[],
            extra_columns=[],
            type_conversion_issues={},
            null_count_by_column={},
            error_message=str(exc),
        )


def run_pipeline(base_dir: Path, target_file: str | None) -> Path:
    raw_dir = base_dir / "raw"
    standards_dir = base_dir / "standards"
    output_dir = base_dir / "output"
    reports_dir = base_dir / "reports"
    config_path = base_dir / "config" / "file_rules.yaml"

    if not config_path.exists():
        default_read = {"encoding": "utf-8", "delimiter": ",", "skiprows": 0}
        build_rules_from_standards(standards_dir, config_path, default_read)

    rules, mappings, threshold, _ = load_rules(config_path)
    files = [raw_dir / target_file] if target_file else sorted(raw_dir.glob("*"))
    results: list[ProcessingResult] = []

    for raw_file in files:
        if not raw_file.exists() or raw_file.is_dir():
            continue
        rule = match_rule(raw_file, rules, mappings)
        if rule is None:
            results.append(
                ProcessingResult(
                    file_name=raw_file.name,
                    status="failed",
                    header_row_index=None,
                    rows_before=0,
                    rows_after=0,
                    missing_columns=[],
                    extra_columns=[],
                    type_conversion_issues={},
                    null_count_by_column={},
                    error_message="No matching standard rule",
                )
            )
            continue
        results.append(process_file(raw_file, rule, threshold, output_dir))

    return save_report_excel(results, reports_dir)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Financial data cleaning pipeline")
    parser.add_argument("--base-dir", type=Path, default=Path.cwd())
    parser.add_argument("--file", type=str, default=None, help="Run single file debug mode")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    setup_logging(args.base_dir / "logs")
    report = run_pipeline(args.base_dir, args.file)
    logging.info("Pipeline completed. Report saved to %s", report)
