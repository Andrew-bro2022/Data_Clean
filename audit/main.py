from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from audit.profile import audit_file
from audit.reporter import default_audit_path, write_audit_excel
from src.reader import load_rules
from src.utils import iter_raw_files_one_level, raw_subfolder_under_raw


def setup_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def run_audit(base_dir: Path, target_file: str | None, max_data_rows: int | None) -> Path:
    config_path = base_dir / "config" / "file_rules.yaml"
    if not config_path.is_file():
        raise FileNotFoundError(f"Missing {config_path} (audit requires file_rules.yaml)")

    rules, mappings, threshold, defaults, prefix_map = load_rules(config_path)
    raw_dir = (base_dir / "raw").resolve()

    if target_file:
        candidate = (base_dir / Path(target_file)).resolve()
        files = [candidate] if candidate.is_file() else []
    else:
        files = iter_raw_files_one_level(raw_dir)

    results = []
    for raw_path in files:
        if not raw_path.is_file():
            continue
        if target_file:
            try:
                raw_path.relative_to(raw_dir)
            except ValueError:
                logging.warning("Skipping %s (not under raw/)", raw_path)
                continue
        results.append(
            audit_file(
                raw_path,
                raw_dir,
                rules,
                mappings,
                prefix_map,
                threshold,
                defaults,
                max_data_rows=max_data_rows,
            )
        )

    out = default_audit_path(base_dir)
    write_audit_excel(results, out)
    return out


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Pre-clean data audit (raw files only)")
    p.add_argument("--base-dir", type=Path, default=Path.cwd())
    p.add_argument("--file", type=str, default=None, help="Single file relative to base-dir under raw/")
    p.add_argument(
        "--max-data-rows",
        type=int,
        default=None,
        help="Limit data rows after header for value checks (phantom/total use same slice; omit for full file)",
    )
    return p.parse_args()


def main() -> None:
    setup_logging()
    args = parse_args()
    try:
        path = run_audit(args.base_dir, args.file, args.max_data_rows)
    except FileNotFoundError as e:
        logging.error("%s", e)
        sys.exit(1)
    logging.info("Audit report written to %s", path)


if __name__ == "__main__":
    main()
