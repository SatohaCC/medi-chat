"""Build autocomplete dictionary from MHLW YJ master CSV.

Extracts active medicines with names, readings (kana/hiragana),
YJ codes, generic names, and dosage categories.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from backend.infrastructure.sources.yj_csv_reader import parse_yj_csv
from backend.project_paths import PROJECT_ROOT, resolve_project_path

logger = logging.getLogger(__name__)


def find_default_csv_path() -> Path | None:
    """Look for y_ALL*.csv in common locations."""
    candidates = [
        PROJECT_ROOT / "yj",
        PROJECT_ROOT / "data/pmda/yj",
    ]
    for directory in candidates:
        if directory.exists():
            for p in directory.glob("y_ALL*.csv"):
                return p
    return None


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    parser = argparse.ArgumentParser(
        description="Build autocomplete dictionary from YJ master CSV."
    )
    parser.add_argument(
        "--csv-path",
        type=Path,
        default=None,
        help="Path to y_ALL*.csv file. Defaults to auto-detect in yj/ directory.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        action="append",
        default=[],
        help="Output JSON file paths. Can be specified multiple times.",
    )

    args = parser.parse_args()

    csv_path = (
        resolve_project_path(args.csv_path)
        if args.csv_path is not None
        else find_default_csv_path()
    )
    if not csv_path:
        logger.error("Could not find y_ALL*.csv. Please specify with --csv-path.")
        sys.exit(1)

    logger.info(f"Parsing YJ CSV from: {csv_path}")
    items = parse_yj_csv(csv_path)
    logger.info(f"Extracted {len(items)} active medicine entries.")

    outputs: list[Path] = [resolve_project_path(path) for path in args.output]
    if not outputs:
        # Default output paths
        default_frontend = PROJECT_ROOT / "frontend/public/data/medicines.json"
        default_backend = (
            PROJECT_ROOT / "data/pmda/structured/medicines_autocomplete.json"
        )
        outputs = [default_frontend, default_backend]

    json_str = json.dumps(items, ensure_ascii=False, separators=(",", ":"))

    for out in outputs:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json_str, encoding="utf-8")
        size_kb = len(json_str.encode("utf-8")) / 1024
        logger.info(f"Wrote {len(items)} items to {out} ({size_kb:.1f} KB)")


if __name__ == "__main__":
    main()
