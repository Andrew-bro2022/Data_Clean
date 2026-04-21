from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from src.types import ProcessingResult
from src.utils import ensure_dir


def save_cleaned(df: pd.DataFrame, output_dir: Path, raw_filename: str) -> Path:
    ensure_dir(output_dir)
    target = output_dir / raw_filename
    df.to_csv(target, index=False)
    return target


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
                    "column_name": col,
                    "null_count": null_count,
                    "type_conversion_issues": r.type_conversion_issues.get(col, 0),
                }
            )

    with pd.ExcelWriter(report_path, engine="openpyxl") as writer:
        pd.DataFrame(summary_rows).to_excel(writer, index=False, sheet_name="file_summary")
        pd.DataFrame(column_rows).to_excel(writer, index=False, sheet_name="column_stats")
    return report_path
