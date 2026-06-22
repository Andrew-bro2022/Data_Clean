from __future__ import annotations

import re
import warnings
from dataclasses import dataclass, field

import pandas as pd

from audit.constants import READ_ENCODING_FALLBACKS

_PARSER_LINE_RE = re.compile(r"line\s+(\d+)", re.IGNORECASE)


@dataclass
class CsvReadResult:
    frame: pd.DataFrame
    encoding_used: str
    configured_encoding: str
    parse_notes: list[str] = field(default_factory=list)
    bad_line_numbers: list[int] = field(default_factory=list)


def extract_line_numbers_from_messages(messages: list[str]) -> list[int]:
    lines: list[int] = []
    for msg in messages:
        for match in _PARSER_LINE_RE.finditer(str(msg)):
            lines.append(int(match.group(1)))
    return sorted(set(lines))


def encoding_fallback_message(configured: str, actual: str) -> str:
    return (
        f"CSV decoded with {actual!r} because {configured!r} failed. "
        "Set defaults.encoding or this rule's read.encoding in file_rules.yaml to match the source file."
    )


def _read_once(
    path,
    *,
    header: int | None,
    delimiter: str,
    encoding: str,
    skiprows: int,
    nrows: int | None,
    on_bad_lines,
) -> pd.DataFrame:
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
        on_bad_lines=on_bad_lines,
    )


def read_csv_raw(
    path,
    *,
    header: int | None,
    read_opts: dict,
    nrows: int | None = None,
) -> CsvReadResult:
    """
    Read CSV as strings. Tries YAML encoding then audit fallbacks.

    On ParserError, retries with ``on_bad_lines="warn"`` and records line-level notes
    for STRUCTURE reporting (ragged rows / unquoted commas).
    """
    delimiter = read_opts.get("delimiter", ",")
    configured = str(read_opts.get("encoding", "utf-8")).strip() or "utf-8"
    skiprows = int(read_opts.get("skiprows", 0))
    candidates = [configured]
    for fb in READ_ENCODING_FALLBACKS:
        if fb.lower() != configured.lower():
            candidates.append(fb)

    last_decode: UnicodeDecodeError | None = None
    parse_notes: list[str] = []

    for enc in candidates:
        try:
            df = _read_once(
                path,
                header=header,
                delimiter=delimiter,
                encoding=enc,
                skiprows=skiprows,
                nrows=nrows,
                on_bad_lines="error",
            )
            return CsvReadResult(
                frame=df,
                encoding_used=enc,
                configured_encoding=configured,
                parse_notes=parse_notes,
                bad_line_numbers=extract_line_numbers_from_messages(parse_notes),
            )
        except UnicodeDecodeError as exc:
            last_decode = exc
            continue
        except pd.errors.ParserError as exc:
            strict_msg = str(exc).strip()
            warn_messages: list[str] = [f"Strict CSV parse failed: {strict_msg}"]
            try:
                with warnings.catch_warnings(record=True) as caught:
                    warnings.simplefilter("always", category=pd.errors.ParserWarning)
                    df = _read_once(
                        path,
                        header=header,
                        delimiter=delimiter,
                        encoding=enc,
                        skiprows=skiprows,
                        nrows=nrows,
                        on_bad_lines="warn",
                    )
                for item in caught:
                    warn_messages.append(str(item.message).strip())
                parse_notes = warn_messages
                return CsvReadResult(
                    frame=df,
                    encoding_used=enc,
                    configured_encoding=configured,
                    parse_notes=parse_notes,
                    bad_line_numbers=extract_line_numbers_from_messages(parse_notes),
                )
            except Exception as retry_exc:  # noqa: BLE001
                parse_notes.append(f"Strict CSV parse failed: {strict_msg}")
                parse_notes.append(f"Recovery read failed: {retry_exc}")
                raise pd.errors.ParserError("\n".join(parse_notes)) from exc

    if last_decode is not None:
        raise last_decode
    raise RuntimeError("read_csv_raw: no encoding candidate succeeded")
