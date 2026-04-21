from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


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
    error_message: str | None = None
    output_path: Path | None = None
