from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from src.reporting import _yn
from src.types import ColumnRule, ProcessingResult
from src.utils import ensure_dir

OUTPUT_DATE_FORMAT = "%Y-%m-%d"


def _format_number_no_sci(value: float) -> str:
    """Write finite floats without scientific notation."""
    if pd.isna(value):
        return ""
    text = f"{value:.15f}".rstrip("0").rstrip(".")
    return text if text else "0"


def _format_cell_for_csv(value: object) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (int,)) or (
        hasattr(value, "dtype") and str(getattr(value, "dtype", "")).startswith("int")
    ):
        return str(int(value))
    if isinstance(value, float):
        return _format_number_no_sci(value)
    if pd.api.types.is_datetime64_any_dtype(type(value)) or isinstance(value, pd.Timestamp):
        return pd.Timestamp(value).strftime(OUTPUT_DATE_FORMAT)
    return str(value)


def _series_to_formatted_date_strings(series: pd.Series, fmt: str) -> pd.Series:
    if pd.api.types.is_datetime64_any_dtype(series):
        parsed = series
    else:
        parsed = pd.to_datetime(series, errors="coerce")
    return parsed.dt.strftime(fmt).where(parsed.notna(), "")


def save_cleaned(
    df: pd.DataFrame,
    output_csv_path: Path,
    column_rules: list[ColumnRule] | None = None,
) -> Path:
    ensure_dir(output_csv_path.parent)
    if not column_rules:
        out = df.copy()
        for col in out.columns:
            out[col] = out[col].map(_format_cell_for_csv)
        out.to_csv(output_csv_path, index=False)
        return output_csv_path

    out = df.copy()
    for rule in column_rules:
        if rule.name not in out.columns:
            continue
        if rule.data_type.lower() in {"date", "datetime"}:
            fmt = rule.date_format or OUTPUT_DATE_FORMAT
            out[rule.name] = _series_to_formatted_date_strings(out[rule.name], fmt)
        elif rule.data_type.lower() in {"int", "integer", "float", "numeric"}:
            out[rule.name] = out[rule.name].map(_format_cell_for_csv)

    out.to_csv(output_csv_path, index=False)
    return output_csv_path


def save_report_excel(results: list[ProcessingResult], reports_dir: Path) -> Path:
    ensure_dir(reports_dir)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = reports_dir / f"report_{ts}.xlsx"

    summary_rows = []
    column_rows = []
    issue_rows = []
    action_rows = []
    action_by_column_rows = []

    for r in results:
        summary_rows.append(
            {
                "file_name": r.file_name,
                "raw_subfolder": r.raw_subfolder,
                "status": r.status,
                "output_written": _yn(r.output_written),
                "layout_status": r.layout_status,
                "clean_status": r.clean_status,
                "status_reason": r.status_reason,
                "header_row_index": r.header_row_index,
                "rows_before": r.rows_before,
                "rows_after": r.rows_after,
                "column_order_match": _yn(r.column_order_match),
                "missing_columns": ", ".join(r.missing_columns),
                "extra_columns": ", ".join(r.extra_columns),
                "error_message": r.error_message or "",
                "output_path": str(r.output_path) if r.output_path else "",
            }
        )

        actions = r.clean_actions.as_dict()
        action_rows.append(
            {
                "file_name": r.file_name,
                "raw_subfolder": r.raw_subfolder,
                "phantom_rows_removed": r.phantom_rows_removed,
                **actions,
            }
        )

        for col, col_actions in sorted(r.clean_actions.by_column.items()):
            counts = {
                "placeholders_cleared": col_actions.placeholders_cleared,
                "currency_stripped": col_actions.currency_stripped,
                "accounting_parens_converted": col_actions.accounting_parens_converted,
                "thousands_commas_removed": col_actions.thousands_commas_removed,
            }
            if any(counts.values()):
                action_by_column_rows.append(
                    {
                        "file_name": r.file_name,
                        "raw_subfolder": r.raw_subfolder,
                        "column": col,
                        **counts,
                    }
                )

        for issue in r.issues:
            sample = issue.get("sample_rows") or []
            issue_rows.append(
                {
                    "file_name": r.file_name,
                    "raw_subfolder": r.raw_subfolder,
                    "phase": issue.get("phase"),
                    "category": issue.get("category"),
                    "severity": issue.get("severity"),
                    "column": issue.get("column") or "",
                    "message": issue.get("message"),
                    "count": issue.get("count"),
                    "sample_rows": ", ".join(str(x) for x in sample),
                    "auto_action": issue.get("auto_action") or "",
                }
            )

        for col, null_count in r.null_count_by_column.items():
            before = r.non_null_before_by_column.get(col, 0)
            after_clean = r.non_null_after_clean_by_column.get(col, 0)
            date_stats = r.date_parse_stats_by_column.get(col)
            column_rows.append(
                {
                    "file_name": r.file_name,
                    "raw_subfolder": r.raw_subfolder,
                    "column_name": col,
                    "non_null_before": before,
                    "non_null_after_clean": after_clean,
                    "null_count_after": null_count,
                    "nulls_introduced_by_clean": max(0, before - after_clean),
                    "type_conversion_issues": r.type_conversion_issues.get(col, 0),
                    "scientific_notation_cells": r.scientific_notation_by_column.get(col, 0),
                    "scientific_preserved_cells": r.scientific_preserved_by_column.get(col, 0),
                    "date_strict_parsed": date_stats.strict_parsed if date_stats else "",
                    "date_alternate_parsed": date_stats.alternate_parsed if date_stats else "",
                    "date_excel_serial_parsed": date_stats.excel_serial_parsed if date_stats else "",
                    "date_inferred_parsed": date_stats.inferred_parsed if date_stats else "",
                    "date_parse_failed": date_stats.failed if date_stats else "",
                }
            )

    with pd.ExcelWriter(report_path, engine="openpyxl") as writer:
        pd.DataFrame(summary_rows).to_excel(writer, index=False, sheet_name="file_summary")
        pd.DataFrame(issue_rows).to_excel(writer, index=False, sheet_name="issues_detail")
        pd.DataFrame(action_rows).to_excel(writer, index=False, sheet_name="clean_actions")
        pd.DataFrame(action_by_column_rows).to_excel(
            writer, index=False, sheet_name="clean_actions_by_column"
        )
        pd.DataFrame(column_rows).to_excel(writer, index=False, sheet_name="column_stats")
    return report_path
