from __future__ import annotations

from src.clean_actions import CleanActionStats
from src.io import encoding_fallback_message
from src.structure import format_duplicate_columns_message
from src.types import ColumnDateParseStats, ProcessingResult


def _yn(value: bool | None) -> str:
    if value is None:
        return ""
    return "Y" if value else "N"


def issue_row(
    *,
    phase: str,
    category: str,
    severity: str,
    message: str,
    column: str | None = None,
    count: int | None = None,
    sample_rows: list[int] | None = None,
    auto_action: str = "",
) -> dict:
    return {
        "phase": phase,
        "category": category,
        "severity": severity,
        "column": column or "",
        "message": message,
        "count": count,
        "sample_rows": sample_rows or [],
        "auto_action": auto_action,
    }


def build_pre_clean_issues(
    *,
    column_order_realigned: bool,
    scientific_notation_by_column: dict[str, int],
    total_keyword_rows: list[int],
) -> list[dict]:
    issues: list[dict] = []
    if column_order_realigned:
        issues.append(
            issue_row(
                phase="pre_clean",
                category="LAYOUT",
                severity="warning",
                message="Column order differed from YAML; realigned before value cleaning",
                auto_action="reorder_to_yaml",
            )
        )
    for col, n in sorted(scientific_notation_by_column.items()):
        issues.append(
            issue_row(
                phase="pre_clean",
                category="SCIENTIFIC",
                severity="warning",
                column=col,
                count=n,
                message="Excel-style scientific notation in source cells (float columns written as literal text)",
                auto_action="kept_literal_string",
            )
        )
    if total_keyword_rows:
        issues.append(
            issue_row(
                phase="pre_clean",
                category="TOTAL",
                severity="warning",
                count=len(total_keyword_rows),
                sample_rows=total_keyword_rows,
                message="Total-like keyword in tail rows — review manually (rows not removed)",
                auto_action="not_removed_review",
            )
        )
    return issues


def build_post_clean_issues(
    *,
    type_conversion_issues: dict[str, int],
    date_stats: dict[str, ColumnDateParseStats] | None = None,
    scientific_preserved: dict[str, int] | None = None,
) -> list[dict]:
    issues: list[dict] = []
    for col, n in sorted(type_conversion_issues.items()):
        if n:
            issues.append(
                issue_row(
                    phase="post_clean",
                    category="TYPE",
                    severity="warning",
                    column=col,
                    count=n,
                    message="Type conversion failed for non-empty cells",
                    auto_action="coerced_or_null",
                )
            )
    for col, stats in sorted((date_stats or {}).items()):
        if stats.recovered_non_strict:
            parts: list[str] = []
            if stats.alternate_parsed:
                parts.append(f"alternate format {stats.alternate_parsed}")
            if stats.excel_serial_parsed:
                parts.append(f"Excel serial {stats.excel_serial_parsed}")
            if stats.inferred_parsed:
                parts.append(f"inferred {stats.inferred_parsed}")
            issues.append(
                issue_row(
                    phase="post_clean",
                    category="DATE",
                    severity="warning",
                    column=col,
                    count=stats.recovered_non_strict,
                    message=(
                        f"Date parsed outside strict YAML format — {', '.join(parts)}; "
                        "output normalized to YAML date_format"
                    ),
                    auto_action="parsed_non_strict",
                )
            )
    for col, n in sorted((scientific_preserved or {}).items()):
        if n:
            issues.append(
                issue_row(
                    phase="post_clean",
                    category="SCIENTIFIC",
                    severity="info",
                    column=col,
                    count=n,
                    message="Scientific notation cells preserved as source text in output CSV",
                    auto_action="kept_literal_string",
                )
            )
    return issues


def build_clean_action_issues(
    *,
    phantom_rows_removed: int,
    actions: CleanActionStats,
) -> list[dict]:
    issues: list[dict] = []
    if phantom_rows_removed:
        issues.append(
            issue_row(
                phase="clean_action",
                category="PHANTOM",
                severity="info",
                count=phantom_rows_removed,
                message="Trailing phantom rows removed",
                auto_action=f"rows_removed:{phantom_rows_removed}",
            )
        )
    mapping = [
        (actions.placeholders_cleared, "PLACEHOLDER", "Null placeholders cleared to empty", "cleared_to_empty"),
        (actions.currency_stripped, "CURRENCY", "Currency symbol ($) stripped", "strip_dollar"),
        (
            actions.accounting_parens_converted,
            "ACCOUNTING",
            "Accounting parentheses converted to negative (accounting convention)",
            "parens_to_negative",
        ),
        (
            actions.thousands_commas_removed,
            "NUMERIC",
            "Thousands separators (commas) removed from numeric cells",
            "remove_commas",
        ),
        (actions.all_blank_rows_dropped, "ROW", "All-blank rows dropped", "drop_blank_rows"),
    ]
    for n, category, message, auto_action in mapping:
        if n:
            issues.append(
                issue_row(
                    phase="clean_action",
                    category=category,
                    severity="info",
                    count=n,
                    message=message,
                    auto_action=auto_action,
                )
            )
    for col, col_actions in sorted(actions.by_column.items()):
        for field, category, message, auto_action in [
            (col_actions.placeholders_cleared, "PLACEHOLDER", "Null placeholders cleared", "cleared_to_empty"),
            (col_actions.currency_stripped, "CURRENCY", "Currency symbol ($) stripped", "strip_dollar"),
            (
                col_actions.accounting_parens_converted,
                "ACCOUNTING",
                "Accounting parentheses → negative",
                "parens_to_negative",
            ),
            (
                col_actions.thousands_commas_removed,
                "NUMERIC",
                "Thousands commas removed",
                "remove_commas",
            ),
        ]:
            if field:
                issues.append(
                    issue_row(
                        phase="clean_action",
                        category=category,
                        severity="info",
                        column=col,
                        count=field,
                        message=message,
                        auto_action=auto_action,
                    )
                )
    return issues


def build_read_phase_issues(
    *,
    encoding_configured: str,
    encoding_used: str,
    parse_notes: list[str],
    bad_line_numbers: list[int],
) -> list[dict]:
    issues: list[dict] = []
    if encoding_used and encoding_configured and encoding_used.lower() != encoding_configured.lower():
        issues.append(
            issue_row(
                phase="pre_clean",
                category="FILE",
                severity="warning",
                message=encoding_fallback_message(encoding_configured, encoding_used),
                auto_action="encoding_fallback",
            )
        )
    if parse_notes or bad_line_numbers:
        detail = "; ".join(parse_notes) if parse_notes else "Ragged CSV rows skipped during read"
        if bad_line_numbers:
            sample = bad_line_numbers[:10]
            detail += f" — affected file line(s): {', '.join(str(n) for n in sample)}"
        issues.append(
            issue_row(
                phase="pre_clean",
                category="STRUCTURE",
                severity="warning",
                message=detail,
                count=len(bad_line_numbers) if bad_line_numbers else None,
                sample_rows=bad_line_numbers[:10],
                auto_action="skipped_bad_lines_review",
            )
        )
    return issues


def build_duplicate_column_issues(dups: dict[str, list[int]]) -> list[dict]:
    if not dups:
        return []
    return [
        issue_row(
            phase="pre_clean",
            category="STRUCTURE",
            severity="error",
            message=format_duplicate_columns_message(dups),
            count=sum(len(v) for v in dups.values()),
            auto_action="blocked_no_output",
        )
    ]


def build_layout_fail_issues(
    *,
    missing_columns: list[str],
    extra_columns: list[str],
    message: str,
) -> list[dict]:
    issues: list[dict] = []
    if missing_columns:
        issues.append(
            issue_row(
                phase="pre_clean",
                category="LAYOUT",
                severity="error",
                count=len(missing_columns),
                message=f"Missing columns vs standard: {', '.join(missing_columns)}",
                auto_action="blocked_no_output",
            )
        )
    if extra_columns:
        issues.append(
            issue_row(
                phase="pre_clean",
                category="LAYOUT",
                severity="error",
                count=len(extra_columns),
                message=f"Extra columns vs standard: {', '.join(extra_columns)}",
                auto_action="blocked_no_output",
            )
        )
    if not issues:
        issues.append(
            issue_row(
                phase="pre_clean",
                category="LAYOUT",
                severity="error",
                message=message,
                auto_action="blocked_no_output",
            )
        )
    return issues


def build_status_reason(result: ProcessingResult) -> str:
    if result.status == "skipped_xlsx":
        return "Convert to CSV before cleaning"
    if result.status == "failed":
        return result.error_message or "Processing failed"
    parts: list[str] = []
    if result.column_order_realigned:
        parts.append("columns realigned to YAML order")
    for col, n in sorted(result.scientific_notation_by_column.items()):
        parts.append(f"scientific notation in {col} ({n})")
    if result.total_keyword_rows:
        rows = ",".join(str(r) for r in result.total_keyword_rows[:5])
        parts.append(f"total-like rows at {rows}")
    for col, n in sorted(result.type_conversion_issues.items()):
        if n:
            parts.append(f"type conversion issues in {col} ({n})")
    for col, stats in sorted(result.date_parse_stats_by_column.items()):
        if stats.recovered_non_strict:
            parts.append(f"date non-strict parse in {col} ({stats.recovered_non_strict})")
    if result.phantom_rows_removed:
        parts.append(f"phantom rows removed ({result.phantom_rows_removed})")
    if result.csv_bad_line_numbers:
        lines = ",".join(str(n) for n in result.csv_bad_line_numbers[:5])
        parts.append(f"ragged CSV line(s) {lines}")
    if (
        result.encoding_used
        and result.encoding_configured
        and result.encoding_used.lower() != result.encoding_configured.lower()
    ):
        parts.append(f"encoding fallback {result.encoding_used}")
    return "; ".join(parts) if parts else "No issues"


def enrich_result_metadata(result: ProcessingResult) -> ProcessingResult:
    """Set output_written, layout/clean status, status_reason, and merge issue lists."""
    if result.status == "skipped_xlsx":
        result.output_written = False
        result.layout_status = "n/a"
        result.clean_status = "n/a"
        result.column_order_match = None
        result.status_reason = build_status_reason(result)
        return result

    if result.status == "failed":
        result.output_written = False
        if result.duplicate_columns:
            result.layout_status = "fail"
            result.clean_status = "n/a"
            if not result.issues:
                result.issues = build_duplicate_column_issues(result.duplicate_columns)
        elif result.missing_columns or result.extra_columns:
            result.layout_status = "fail"
            result.clean_status = "n/a"
            if not result.issues:
                result.issues = build_layout_fail_issues(
                    missing_columns=result.missing_columns,
                    extra_columns=result.extra_columns,
                    message=result.error_message or "Layout gate failed",
                )
        elif result.header_row_index is None:
            result.layout_status = "n/a"
            result.clean_status = "n/a"
        else:
            result.layout_status = "pass"
            result.clean_status = "fail"
        result.column_order_match = None
        result.status_reason = build_status_reason(result)
        return result

    result.output_written = result.output_path is not None
    result.layout_status = "pass"
    result.clean_status = "warning" if result.status == "warning" else "pass"
    result.column_order_match = not result.column_order_realigned

    read_issues = build_read_phase_issues(
        encoding_configured=result.encoding_configured,
        encoding_used=result.encoding_used,
        parse_notes=result.csv_parse_notes,
        bad_line_numbers=result.csv_bad_line_numbers,
    )
    pre = read_issues + build_pre_clean_issues(
        column_order_realigned=result.column_order_realigned,
        scientific_notation_by_column=result.scientific_notation_by_column,
        total_keyword_rows=result.total_keyword_rows,
    )
    post = build_post_clean_issues(
        type_conversion_issues=result.type_conversion_issues,
        date_stats=result.date_parse_stats_by_column,
        scientific_preserved=result.scientific_preserved_by_column,
    )
    actions = build_clean_action_issues(
        phantom_rows_removed=result.phantom_rows_removed,
        actions=result.clean_actions,
    )
    result.issues = pre + actions + post
    result.status_reason = build_status_reason(result)
    return result
