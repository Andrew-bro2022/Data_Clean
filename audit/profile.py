from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from audit.checks import run_value_checks
from audit.constants import READ_ENCODING_FALLBACKS
from src.file_matcher import match_rule
from src.header_detector import detect_header_row
from src.types import FileRule
from src.utils import raw_subfolder_under_raw


def _analyze_column_count_and_order(
    standard_ordered: list[str],
    raw_ordered: list[str],
) -> dict:
    """
    Compare standard vs raw header by position (left to right).

    - If column counts differ, treat as a layout/order problem and still locate
      the first positional name mismatch if any; otherwise the first difference
      is at position min(n_standard, n_raw)+1 (extra or missing tail).
    - If counts match, first mismatch is the first index where names differ.
    """
    n_s, n_r = len(standard_ordered), len(raw_ordered)
    count_match = n_s == n_r
    pos: int | None = None
    expected = ""
    found = ""

    for i in range(min(n_s, n_r)):
        if standard_ordered[i] != raw_ordered[i]:
            pos = i + 1
            expected = standard_ordered[i]
            found = raw_ordered[i]
            break
    else:
        if n_s != n_r:
            k = min(n_s, n_r)
            pos = k + 1
            if n_r > n_s:
                expected = "(no further standard column)"
                found = raw_ordered[k] if k < n_r else ""
            else:
                expected = standard_ordered[k] if k < n_s else ""
                found = "(no further raw column)"

    layout_ok = count_match and pos is None
    return {
        "standard_n": n_s,
        "raw_n": n_r,
        "count_match": count_match,
        "layout_ok": layout_ok,
        "first_mismatch_1based": pos,
        "expected": expected,
        "found": found,
    }


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
    standard_column_count: int = 0
    raw_column_count: int = 0
    column_count_match: bool | None = None
    column_order_match: bool | None = None
    column_order_first_mismatch_1based: int | None = None
    column_order_mismatch_expected: str = ""
    column_order_mismatch_found: str = ""


def _read_csv_audit(
    path: Path,
    *,
    header: int | None,
    read_opts: dict,
    nrows: int | None = None,
) -> tuple[pd.DataFrame, str]:
    """Read CSV; try YAML encoding first, then READ_ENCODING_FALLBACKS. Returns (df, encoding_used)."""
    delimiter = read_opts.get("delimiter", ",")
    primary = str(read_opts.get("encoding", "utf-8")).strip() or "utf-8"
    skiprows = int(read_opts.get("skiprows", 0))
    candidates = [primary]
    for fb in READ_ENCODING_FALLBACKS:
        if fb.lower() != primary.lower():
            candidates.append(fb)
    last_err: UnicodeDecodeError | None = None
    for enc in candidates:
        try:
            df = pd.read_csv(
                path,
                header=header,
                dtype=str,
                keep_default_na=False,
                sep=delimiter,
                encoding=enc,
                skiprows=skiprows,
                nrows=nrows,
                engine="python",
            )
            return df, enc
        except UnicodeDecodeError as exc:
            last_err = exc
            continue
    if last_err is not None:
        raise last_err
    raise RuntimeError("_read_csv_audit: no encoding candidate succeeded")


def _encoding_fallback_issue(configured: str, actual: str) -> dict:
    return {
        "category": "FILE",
        "severity": "warning",
        "column": None,
        "message": (
            f"CSV decoded with {actual!r} because {configured!r} failed. "
            "Set defaults.encoding or this rule's read.encoding in file_rules.yaml to match the source file."
        ),
        "count": None,
        "sample_rows": [],
    }


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
    configured_encoding = str(read_opts.get("encoding", "utf-8")).strip() or "utf-8"

    try:
        if rule is None:
            df0, enc = _read_csv_audit(raw_path, header=None, read_opts=read_opts, nrows=max_data_rows)
            read_opts["encoding"] = enc
            issues: list[dict] = []
            if enc.lower() != configured_encoding.lower():
                issues.append(_encoding_fallback_issue(configured_encoding, enc))
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

        used_encoding_fallback = False
        preview, enc = _read_csv_audit(raw_path, header=None, read_opts=read_opts, nrows=30)
        read_opts["encoding"] = enc
        if enc.lower() != configured_encoding.lower():
            used_encoding_fallback = True
        header_idx = detect_header_row(
            preview.fillna("").values.tolist(),
            [c.name for c in rule.columns],
            threshold,
        )
        if header_idx is None:
            df0, enc = _read_csv_audit(raw_path, header=None, read_opts=read_opts, nrows=max_data_rows)
            read_opts["encoding"] = enc
            if enc.lower() != configured_encoding.lower():
                used_encoding_fallback = True
            issues = []
            if used_encoding_fallback:
                issues.append(_encoding_fallback_issue(configured_encoding, enc))
            issues.append(
                {
                    "category": "STRUCTURE",
                    "severity": "error",
                    "column": None,
                    "message": "Header row not found (below threshold match to standard columns)",
                    "count": None,
                    "sample_rows": [],
                }
            )
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
                standard_column_count=len(rule.columns),
                raw_column_count=0,
                column_count_match=None,
                column_order_match=None,
                column_order_first_mismatch_1based=None,
                column_order_mismatch_expected="",
                column_order_mismatch_found="",
            )

        df, enc = _read_csv_audit(raw_path, header=header_idx, read_opts=read_opts, nrows=None)
        read_opts["encoding"] = enc
        if enc.lower() != configured_encoding.lower():
            used_encoding_fallback = True
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
        if used_encoding_fallback:
            issues.append(_encoding_fallback_issue(configured_encoding, read_opts["encoding"]))
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

        layout = _analyze_column_count_and_order(standard_cols, header_column_names)
        column_count_match = layout["count_match"]
        column_order_match = layout["layout_ok"]
        if not layout["layout_ok"]:
            issues.append(
                {
                    "category": "COLUMN_LAYOUT",
                    "severity": "warning",
                    "column": None,
                    "message": (
                        f"Column count/order: standard_n={layout['standard_n']} raw_n={layout['raw_n']}; "
                        f"first difference at 1-based position {layout['first_mismatch_1based']}: "
                        f"expected {layout['expected']!r}, found {layout['found']!r}"
                    ),
                    "count": None,
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
            standard_column_count=layout["standard_n"],
            raw_column_count=layout["raw_n"],
            column_count_match=column_count_match,
            column_order_match=column_order_match,
            column_order_first_mismatch_1based=layout["first_mismatch_1based"],
            column_order_mismatch_expected=layout["expected"],
            column_order_mismatch_found=layout["found"],
        )
    except Exception as exc:  # noqa: BLE001
        msg = str(exc)
        low = msg.lower()
        if isinstance(exc, UnicodeDecodeError) or "codec can't decode" in low or "invalid continuation byte" in low:
            msg += (
                " Hint: the file may be Windows-1252 / Latin-1. "
                "Set defaults.encoding or this rule's read.encoding (e.g. cp1252 or latin-1) in file_rules.yaml."
            )
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
            error_message=msg,
        )
