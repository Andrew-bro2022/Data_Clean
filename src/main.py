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
from src.utils import iter_raw_files_one_level, mirrored_output_csv_path, raw_subfolder_under_raw
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


def process_file(raw_file: Path, rule, threshold: float, raw_dir: Path, output_root: Path) -> ProcessingResult:
    sf = raw_subfolder_under_raw(raw_file, raw_dir)
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
            raw_subfolder=sf,
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
                raw_subfolder=sf,
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
        # Column presence for reporting: use names from the detected header row only (not post-clean drops).
        header_column_names = [str(c) for c in df.columns]
        header_set = set(header_column_names)

        rows_before = len(df)
        cleaned = clean_dataframe(df)
        cleaned.columns = [str(c) for c in cleaned.columns]

        standard_cols = [c.name for c in rule.columns]
        standard_set = set(standard_cols)
        missing = [c for c in standard_cols if c not in header_set]
        extra: list[str] = []
        seen_extra: set[str] = set()
        for name in header_column_names:
            if name not in standard_set and name not in seen_extra:
                extra.append(name)
                seen_extra.add(name)

        ordered_standard = [c for c in standard_cols if c in cleaned.columns]
        extra_ordered = [c for c in cleaned.columns if c not in standard_set]
        aligned = cleaned[ordered_standard + extra_ordered]

        converted, issues = convert_types(aligned, rule.columns)
        null_counts = converted.isna().sum().astype(int).to_dict()
        status = derive_status(header_row_found=True, has_conversion_issue=bool(issues), failed=False)
        output_csv = mirrored_output_csv_path(raw_file, raw_dir, output_root)
        output_path = save_cleaned(converted, output_csv)

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
            raw_subfolder=sf,
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
            raw_subfolder=sf,
            error_message=str(exc),
        )


def run_pipeline(base_dir: Path, target_file: str | None) -> Path:
    raw_dir = (base_dir / "raw").resolve()
    standards_dir = base_dir / "standards"
    output_root = base_dir / "output"
    reports_dir = base_dir / "reports"
    config_path = base_dir / "config" / "file_rules.yaml"

    if not config_path.exists():
        default_read = {"encoding": "utf-8", "delimiter": ",", "skiprows": 0}
        build_rules_from_standards(standards_dir, config_path, default_read, merge_existing=False)

    rules, mappings, threshold, _, prefix_to_standard = load_rules(config_path)

    results: list[ProcessingResult] = []

    if target_file:
        candidate = (base_dir / Path(target_file)).resolve()
        if not candidate.exists() or not candidate.is_file():
            results.append(
                ProcessingResult(
                    file_name=Path(target_file).name,
                    status="failed",
                    header_row_index=None,
                    rows_before=0,
                    rows_after=0,
                    missing_columns=[],
                    extra_columns=[],
                    type_conversion_issues={},
                    null_count_by_column={},
                    raw_subfolder="",
                    error_message="File not found",
                )
            )
            return save_report_excel(results, reports_dir)
        try:
            candidate.relative_to(raw_dir)
        except ValueError:
            results.append(
                ProcessingResult(
                    file_name=candidate.name,
                    status="failed",
                    header_row_index=None,
                    rows_before=0,
                    rows_after=0,
                    missing_columns=[],
                    extra_columns=[],
                    type_conversion_issues={},
                    null_count_by_column={},
                    raw_subfolder="",
                    error_message="Path must be under raw/ (relative to base-dir)",
                )
            )
            return save_report_excel(results, reports_dir)
        files = [candidate]
    else:
        files = iter_raw_files_one_level(raw_dir)

    for raw_file in files:
        sf = raw_subfolder_under_raw(raw_file, raw_dir)

        if not raw_file.exists() or raw_file.is_dir():
            continue

        rule = match_rule(raw_file, rules, mappings, raw_dir, prefix_to_standard)
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
                    raw_subfolder=sf,
                    error_message="No matching standard rule",
                )
            )
            continue
        results.append(process_file(raw_file, rule, threshold, raw_dir, output_root))

    return save_report_excel(results, reports_dir)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Financial data cleaning pipeline")
    parser.add_argument("--base-dir", type=Path, default=Path.cwd())
    parser.add_argument(
        "--file",
        type=str,
        default=None,
        help="Single file relative to base-dir (e.g. raw/teamA/foo.csv)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    setup_logging(args.base_dir / "logs")
    report = run_pipeline(args.base_dir, args.file)
    logging.info("Pipeline completed. Report saved to %s", report)
