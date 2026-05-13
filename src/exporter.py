from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from src.types import ColumnRule, ProcessingResult
from src.utils import ensure_dir

# Used when a rule has type date/datetime but no date_format, or when save_cleaned is called without rules.
OUTPUT_DATE_FORMAT = "%Y-%m-%d"


def _series_to_formatted_date_strings(series: pd.Series, fmt: str) -> pd.Series:
    """Format values as date strings using strftime codes; empty string for null/NaT."""
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
        df.to_csv(output_csv_path, index=False, date_format=OUTPUT_DATE_FORMAT)
        return output_csv_path

    out = df.copy()
    for rule in column_rules:
        if rule.name not in out.columns:
            continue
        if rule.data_type.lower() not in {"date", "datetime"}:
            continue
        fmt = rule.date_format or OUTPUT_DATE_FORMAT
        out[rule.name] = _series_to_formatted_date_strings(out[rule.name], fmt)

    out.to_csv(output_csv_path, index=False, date_format=OUTPUT_DATE_FORMAT)
    return output_csv_path


def save_report_excel(results: list[ProcessingResult], reports_dir: Path) -> Path:
    ensure_dir(reports_dir)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = reports_dir / f"report_{ts}.xlsx"

    summary_rows = []
    column_rows = []
    for r in results:
        summary_rows.append(
            {
                "file_name": r.file_name,
                "raw_subfolder": r.raw_subfolder,
                "status": r.status,
                "header_row_index": r.header_row_index,
                "rows_before": r.rows_before,
                "rows_after": r.rows_after,
                "missing_columns": ", ".join(r.missing_columns),
                "extra_columns": ", ".join(r.extra_columns),
                "error_message": r.error_message or "",
                "output_path": str(r.output_path) if r.output_path else "",
            }
        )
        for col, null_count in r.null_count_by_column.items():
            column_rows.append(
                {
                    "file_name": r.file_name,
                    "raw_subfolder": r.raw_subfolder,
                    "column_name": col,
                    "null_count": null_count,
                    "type_conversion_issues": r.type_conversion_issues.get(col, 0),
                }
            )

    with pd.ExcelWriter(report_path, engine="openpyxl") as writer:
        pd.DataFrame(summary_rows).to_excel(writer, index=False, sheet_name="file_summary")
        pd.DataFrame(column_rows).to_excel(writer, index=False, sheet_name="column_stats")
    return report_path
