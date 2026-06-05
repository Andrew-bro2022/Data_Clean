from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from audit.profile import FileAuditResult


def _yn_or_blank(value: bool | None) -> str:
    if value is None:
        return ""
    return "Y" if value else "N"


def _sorted_issue_columns(issues: list[dict], category: str) -> str:
    """Distinct non-empty `column` values for issues of a given category."""
    names: set[str] = set()
    for issue in issues:
        if issue.get("category") != category:
            continue
        col = issue.get("column")
        if col is None:
            continue
        text = str(col).strip()
        if text:
            names.add(text)
    return ", ".join(sorted(names))


def _has_category(issues: list[dict], category: str) -> bool:
    return any(i.get("category") == category for i in issues)


def write_audit_excel(results: list[FileAuditResult], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    summary_rows = []
    detail_rows = []
    for r in results:
        err_count = sum(1 for i in r.issues if i.get("severity") == "error")
        warn_count = sum(1 for i in r.issues if i.get("severity") == "warning")
        cats = {}
        for i in r.issues:
            c = i.get("category", "")
            cats[c] = cats.get(c, 0) + 1
        summary_rows.append(
            {
                "file_name": r.file_name,
                "raw_subfolder": r.raw_subfolder,
                "matched_standard": r.standard_file or "",
                "header_row_index": r.header_row_index,
                "data_rows": r.data_rows,
                "data_columns": r.data_columns,
                "missing_columns": ", ".join(r.missing_columns),
                "extra_columns": ", ".join(r.extra_columns),
                "standard_n_columns": r.standard_column_count,
                "raw_n_columns": r.raw_column_count,
                "column_count_match": _yn_or_blank(r.column_count_match),
                "column_order_match": _yn_or_blank(r.column_order_match),
                "column_order_first_mismatch_1based": r.column_order_first_mismatch_1based
                if r.column_order_first_mismatch_1based is not None
                else "",
                "column_order_mismatch_expected": r.column_order_mismatch_expected or "",
                "column_order_mismatch_found": r.column_order_mismatch_found or "",
                "issue_error_count": err_count,
                "issue_warning_count": warn_count,
                "issue_total": len(r.issues),
                "categories": ", ".join(f"{k}:{v}" for k, v in sorted(cats.items())),
                # Per-category column rollups (see issues_detail for row-level detail).
                "date_issue_columns": _sorted_issue_columns(r.issues, "DATE"),
                "numeric_issue_columns": _sorted_issue_columns(r.issues, "NUMERIC"),
                "placeholder_issue_columns": _sorted_issue_columns(r.issues, "PLACEHOLDER"),
                "phantom_issue": "Y" if _has_category(r.issues, "PHANTOM") else "",
                "total_keyword_issue": "Y" if _has_category(r.issues, "TOTAL") else "",
                "read_error": r.error_message or "",
            }
        )
        for issue in r.issues:
            sample = issue.get("sample_rows") or []
            detail_rows.append(
                {
                    "file_name": r.file_name,
                    "raw_subfolder": r.raw_subfolder,
                    "category": issue.get("category"),
                    "severity": issue.get("severity"),
                    "column": issue.get("column") or "",
                    "message": issue.get("message"),
                    "count": issue.get("count"),
                    "sample_rows": ", ".join(str(x) for x in sample),
                }
            )

    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        pd.DataFrame(summary_rows).to_excel(writer, index=False, sheet_name="file_summary")
        pd.DataFrame(detail_rows).to_excel(writer, index=False, sheet_name="issues_detail")
    return output_path


def default_audit_path(base_dir: Path) -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return base_dir / "audit" / "output" / f"audit_{ts}.xlsx"
