from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from audit.checks import run_value_checks
from src.file_matcher import match_rule
from src.header_detector import detect_header_row
from src.types import FileRule
from src.utils import raw_subfolder_under_raw


@dataclass
class FileAuditResult:
    file_name: str
    raw_subfolder: str
    matched: bool
    standard_file: str | None
    header_row_index: int | None
    data_rows: int
    data_columns: int
    missing_columns: list[str]
    extra_columns: list[str]
    issues: list[dict] = field(default_factory=list)
    error_message: str | None = None


def _read_csv_audit(
    path: Path,
    *,
    header: int | None,
    read_opts: dict,
    nrows: int | None = None,
) -> pd.DataFrame:
    delimiter = read_opts.get("delimiter", ",")
    encoding = read_opts.get("encoding", "utf-8")
    skiprows = int(read_opts.get("skiprows", 0))
    return pd.read_csv(
        path,
        header=header,
        dtype=str,
        keep_default_na=False,
        sep=delimiter,
        encoding=encoding,
        skiprows=skiprows,
        nrows=nrows,
        engine="python",
    )


def audit_file(
    raw_path: Path,
    raw_dir: Path,
    rules: dict[str, FileRule],
    mappings: dict[str, str],
    prefix_map: dict[str, str],
    threshold: float,
    defaults: dict,
    max_data_rows: int | None = None,
) -> FileAuditResult:
    sf = raw_subfolder_under_raw(raw_path, raw_dir)
    name = raw_path.name

    if raw_path.suffix.lower() == ".xlsx":
        return FileAuditResult(
            file_name=name,
            raw_subfolder=sf,
            matched=False,
            standard_file=None,
            header_row_index=None,
            data_rows=0,
            data_columns=0,
            missing_columns=[],
            extra_columns=[],
            issues=[
                {
                    "category": "FILE",
                    "severity": "info",
                    "column": None,
                    "message": "xlsx skipped in audit (same as clean pipeline)",
                    "count": None,
                    "sample_rows": [],
                }
            ],
        )

    read_opts = dict(defaults)
    rule = match_rule(raw_path, rules, mappings, raw_dir, prefix_map)
    if rule is not None:
        read_opts.update(rule.read)

    try:
        if rule is None:
            df0 = _read_csv_audit(raw_path, header=None, read_opts=read_opts, nrows=max_data_rows)
            issues: list[dict] = []
            issues.extend(run_value_checks(df0, []))
            return FileAuditResult(
                file_name=name,
                raw_subfolder=sf,
                matched=False,
                standard_file=None,
                header_row_index=None,
                data_rows=len(df0),
                data_columns=len(df0.columns),
                missing_columns=[],
                extra_columns=[],
                issues=issues,
            )

        preview = _read_csv_audit(raw_path, header=None, read_opts=read_opts, nrows=30)
        header_idx = detect_header_row(
            preview.fillna("").values.tolist(),
            [c.name for c in rule.columns],
            threshold,
        )
        if header_idx is None:
            df0 = _read_csv_audit(raw_path, header=None, read_opts=read_opts, nrows=max_data_rows)
            issues = [
                {
                    "category": "STRUCTURE",
                    "severity": "error",
                    "column": None,
                    "message": "Header row not found (below threshold match to standard columns)",
                    "count": None,
                    "sample_rows": [],
                }
            ]
            issues.extend(run_value_checks(df0, []))
            return FileAuditResult(
                file_name=name,
                raw_subfolder=sf,
                matched=True,
                standard_file=rule.standard_file,
                header_row_index=None,
                data_rows=len(df0),
                data_columns=len(df0.columns),
                missing_columns=[],
                extra_columns=[],
                issues=issues,
            )

        df = _read_csv_audit(raw_path, header=header_idx, read_opts=read_opts, nrows=None)
        if max_data_rows is not None:
            df = df.head(max_data_rows)

        header_column_names = [str(c) for c in df.columns]
        header_set = set(header_column_names)
        standard_cols = [c.name for c in rule.columns]
        standard_set = set(standard_cols)
        missing = [c for c in standard_cols if c not in header_set]
        extra: list[str] = []
        seen: set[str] = set()
        for col in header_column_names:
            if col not in standard_set and col not in seen:
                extra.append(col)
                seen.add(col)

        issues = []
        if missing:
            issues.append(
                {
                    "category": "STRUCTURE",
                    "severity": "warning",
                    "column": None,
                    "message": f"Missing columns vs standard: {', '.join(missing)}",
                    "count": len(missing),
                    "sample_rows": [],
                }
            )
        if extra:
            issues.append(
                {
                    "category": "STRUCTURE",
                    "severity": "info",
                    "column": None,
                    "message": f"Extra columns vs standard: {', '.join(extra)}",
                    "count": len(extra),
                    "sample_rows": [],
                }
            )

        issues.extend(
            run_value_checks(
                df,
                rule.columns,
                raw_path=raw_path,
                read_opts=read_opts,
                header_row_index=header_idx,
            )
        )

        return FileAuditResult(
            file_name=name,
            raw_subfolder=sf,
            matched=True,
            standard_file=rule.standard_file,
            header_row_index=header_idx,
            data_rows=len(df),
            data_columns=len(df.columns),
            missing_columns=missing,
            extra_columns=extra,
            issues=issues,
        )
    except Exception as exc:  # noqa: BLE001
        return FileAuditResult(
            file_name=name,
            raw_subfolder=sf,
            matched=rule is not None,
            standard_file=rule.standard_file if rule else None,
            header_row_index=None,
            data_rows=0,
            data_columns=0,
            missing_columns=[],
            extra_columns=[],
            issues=[],
            error_message=str(exc),
        )
