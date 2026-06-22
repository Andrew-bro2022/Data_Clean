from __future__ import annotations

import argparse
import logging
from pathlib import Path

from src.blockers import scan_scientific_notation
from src.clean_actions import count_non_null_cells
from src.cleaner import clean_dataframe
from src.exporter import save_cleaned, save_report_excel
from src.file_matcher import match_rule
from src.header_detector import detect_header_row
from src.io import read_csv_raw
from src.reader import build_rules_from_standards, load_rules
from src.reporting import build_duplicate_column_issues, build_layout_fail_issues, enrich_result_metadata
from src.row_filters import remove_phantom_trailer_rows, scan_total_keyword_rows
from src.structure import detect_duplicate_columns, format_duplicate_columns_message, gate_and_align
from src.types import ProcessingResult
from src.utils import (
    iter_raw_files_one_level,
    mirrored_output_csv_path,
    normalize_header_column_name,
    preview_rows_for_header_detection,
    raw_subfolder_under_raw,
    rename_raw_headers_to_standard,
)
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


def _failed_result(
    *,
    file_name: str,
    sf: str,
    header_row_index: int | None,
    message: str,
    missing_columns: list[str] | None = None,
    extra_columns: list[str] | None = None,
    literal_missing: list[str] | None = None,
    literal_extra: list[str] | None = None,
    duplicate_columns: dict[str, list[int]] | None = None,
    rows_before: int = 0,
) -> ProcessingResult:
    issues = []
    if duplicate_columns:
        issues = build_duplicate_column_issues(duplicate_columns)
    elif missing_columns or extra_columns:
        issues = build_layout_fail_issues(
            missing_columns=missing_columns or [],
            extra_columns=extra_columns or [],
            message=message,
        )
    return enrich_result_metadata(
        ProcessingResult(
            file_name=file_name,
            status="failed",
            header_row_index=header_row_index,
            rows_before=rows_before,
            rows_after=0,
            missing_columns=missing_columns or [],
            extra_columns=extra_columns or [],
            literal_missing_columns=literal_missing or [],
            literal_extra_columns=literal_extra or [],
            duplicate_columns=duplicate_columns or {},
            type_conversion_issues={},
            null_count_by_column={},
            raw_subfolder=sf,
            error_message=message,
            issues=issues,
        )
    )


def process_file(raw_file: Path, rule, threshold: float, raw_dir: Path, output_root: Path) -> ProcessingResult:
    sf = raw_subfolder_under_raw(raw_file, raw_dir)
    if raw_file.suffix.lower() == ".xlsx":
        return enrich_result_metadata(
            ProcessingResult(
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
        )

    try:
        read_opts = dict(rule.read)
        standard_cols = [c.name for c in rule.columns]

        preview_result = read_csv_raw(
            raw_file,
            header=None,
            read_opts=read_opts,
            nrows=30,
        )
        preview = preview_result.frame
        header_idx = detect_header_row(
            preview_rows_for_header_detection(preview),
            standard_cols,
            threshold,
        )
        if header_idx is None:
            return _failed_result(
                file_name=raw_file.name,
                sf=sf,
                header_row_index=None,
                message="Header row not found",
            )

        read_result = read_csv_raw(raw_file, header=header_idx, read_opts=read_opts)
        df = read_result.frame
        read_opts["encoding"] = read_result.encoding_used

        raw_exact_headers = [normalize_header_column_name(c) for c in df.columns]
        df.columns = rename_raw_headers_to_standard(raw_exact_headers, standard_cols)

        dups = detect_duplicate_columns(
            raw_exact_headers,
            standard_cols,
            list(df.columns),
        )
        if dups:
            return _failed_result(
                file_name=raw_file.name,
                sf=sf,
                header_row_index=header_idx,
                message=format_duplicate_columns_message(dups),
                duplicate_columns=dups,
                rows_before=len(df),
            )

        layout = gate_and_align(
            df,
            raw_exact_headers=raw_exact_headers,
            standard_columns=standard_cols,
        )
        if not layout.ok:
            return _failed_result(
                file_name=raw_file.name,
                sf=sf,
                header_row_index=header_idx,
                message=layout.error_message or "Layout gate failed",
                missing_columns=layout.missing_columns,
                extra_columns=layout.extra_columns,
                literal_missing=layout.literal_missing_columns,
                literal_extra=layout.literal_extra_columns,
                rows_before=len(df),
            )

        aligned = layout.aligned
        assert aligned is not None

        sci_counts = scan_scientific_notation(aligned, rule.columns)
        non_null_before = {col: count_non_null_cells(aligned[col]) for col in aligned.columns}

        rows_before = len(aligned)
        total_keyword_rows = scan_total_keyword_rows(aligned)
        aligned, phantom_removed = remove_phantom_trailer_rows(aligned)

        cleaned, clean_stats = clean_dataframe(aligned, rule.columns)
        non_null_after_clean = {col: count_non_null_cells(cleaned[col]) for col in cleaned.columns}

        converted, conv_meta = convert_types(cleaned, rule.columns)
        issues = conv_meta.type_issues
        has_date_inference = any(
            stats.recovered_non_strict > 0 for stats in conv_meta.date_stats.values()
        )
        null_counts = converted.isna().sum().astype(int).to_dict()
        status = derive_status(
            header_row_found=True,
            failed=False,
            has_conversion_issue=bool(issues),
            column_order_realigned=layout.column_order_realigned,
            total_keyword_rows=total_keyword_rows,
            scientific_notation_by_column=sci_counts,
            encoding_configured=read_result.configured_encoding,
            encoding_used=read_result.encoding_used,
            csv_bad_line_numbers=read_result.bad_line_numbers,
            has_date_inference=has_date_inference,
        )
        output_csv = mirrored_output_csv_path(raw_file, raw_dir, output_root)
        output_path = save_cleaned(converted, output_csv, rule.columns)

        return enrich_result_metadata(
            ProcessingResult(
                file_name=raw_file.name,
                status=status,
                header_row_index=header_idx,
                rows_before=rows_before,
                rows_after=len(converted),
                missing_columns=layout.missing_columns,
                extra_columns=layout.extra_columns,
                literal_missing_columns=layout.literal_missing_columns,
                literal_extra_columns=layout.literal_extra_columns,
                column_order_realigned=layout.column_order_realigned,
                phantom_rows_removed=phantom_removed,
                total_keyword_rows=total_keyword_rows,
                scientific_notation_by_column=sci_counts,
                encoding_configured=read_result.configured_encoding,
                encoding_used=read_result.encoding_used,
                csv_parse_notes=read_result.parse_notes,
                csv_bad_line_numbers=read_result.bad_line_numbers,
                type_conversion_issues=issues,
                date_parse_stats_by_column=conv_meta.date_stats,
                scientific_preserved_by_column=conv_meta.scientific_preserved,
                null_count_by_column=null_counts,
                non_null_before_by_column=non_null_before,
                non_null_after_clean_by_column=non_null_after_clean,
                clean_actions=clean_stats,
                raw_subfolder=sf,
                output_path=output_path,
            )
        )
    except Exception as exc:  # noqa: BLE001
        return _failed_result(
            file_name=raw_file.name,
            sf=sf,
            header_row_index=None,
            message=str(exc),
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
                _failed_result(
                    file_name=Path(target_file).name,
                    sf="",
                    header_row_index=None,
                    message="File not found",
                )
            )
            return save_report_excel(results, reports_dir)
        try:
            candidate.relative_to(raw_dir)
        except ValueError:
            results.append(
                _failed_result(
                    file_name=candidate.name,
                    sf="",
                    header_row_index=None,
                    message="Path must be under raw/ (relative to base-dir)",
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
        if sf == "_audit_fixtures":
            continue
        if raw_file.suffix.lower() == ".xlsx":
            results.append(
                enrich_result_metadata(
                    ProcessingResult(
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
                )
            )
            continue

        rule = match_rule(raw_file, rules, mappings, raw_dir, prefix_to_standard)
        if rule is None:
            results.append(
                _failed_result(
                    file_name=raw_file.name,
                    sf=sf,
                    header_row_index=None,
                    message="No matching standard rule",
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
