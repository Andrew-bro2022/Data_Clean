from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.clean_actions import CleanActionStats


@dataclass
class ColumnDateParseStats:
    strict_parsed: int = 0
    alternate_parsed: int = 0
    excel_serial_parsed: int = 0
    inferred_parsed: int = 0
    failed: int = 0

    @property
    def recovered_non_strict(self) -> int:
        return self.alternate_parsed + self.excel_serial_parsed + self.inferred_parsed

    def as_dict(self) -> dict[str, int]:
        return {
            "strict_parsed": self.strict_parsed,
            "alternate_parsed": self.alternate_parsed,
            "excel_serial_parsed": self.excel_serial_parsed,
            "inferred_parsed": self.inferred_parsed,
            "failed": self.failed,
        }


@dataclass
class TypeConversionMeta:
    type_issues: dict[str, int] = field(default_factory=dict)
    date_stats: dict[str, ColumnDateParseStats] = field(default_factory=dict)
    scientific_preserved: dict[str, int] = field(default_factory=dict)


@dataclass
class ColumnRule:
    name: str
    data_type: str
    date_format: str | None = None


@dataclass
class FileRule:
    standard_file: str
    read: dict[str, Any]
    columns: list[ColumnRule]
    aliases: list[str] = field(default_factory=list)


@dataclass
class ProcessingResult:
    file_name: str
    status: str
    header_row_index: int | None
    rows_before: int
    rows_after: int
    missing_columns: list[str]
    extra_columns: list[str]
    type_conversion_issues: dict[str, int]
    null_count_by_column: dict[str, int]
    raw_subfolder: str = ""
    error_message: str | None = None
    output_path: Path | None = None
    literal_missing_columns: list[str] = field(default_factory=list)
    literal_extra_columns: list[str] = field(default_factory=list)
    column_order_realigned: bool = False
    phantom_rows_removed: int = 0
    total_keyword_rows: list[int] = field(default_factory=list)
    scientific_notation_by_column: dict[str, int] = field(default_factory=dict)
    scientific_preserved_by_column: dict[str, int] = field(default_factory=dict)
    date_parse_stats_by_column: dict[str, ColumnDateParseStats] = field(default_factory=dict)
    encoding_configured: str = ""
    encoding_used: str = ""
    csv_parse_notes: list[str] = field(default_factory=list)
    csv_bad_line_numbers: list[int] = field(default_factory=list)
    duplicate_columns: dict[str, list[int]] = field(default_factory=dict)
    output_written: bool = False
    layout_status: str = ""
    clean_status: str = ""
    status_reason: str = ""
    column_order_match: bool | None = None
    issues: list[dict] = field(default_factory=list)
    clean_actions: CleanActionStats = field(default_factory=CleanActionStats)
    non_null_before_by_column: dict[str, int] = field(default_factory=dict)
    non_null_after_clean_by_column: dict[str, int] = field(default_factory=dict)
