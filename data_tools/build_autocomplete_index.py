"""Build autocomplete dictionary from MHLW YJ master CSV.

Extracts active medicines with names, readings (kana/hiragana),
YJ codes, generic names, and dosage categories.
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import sys
import unicodedata
from pathlib import Path

logger = logging.getLogger(__name__)

# Map MHLW administration category code to human-readable label
CATEGORY_MAP: dict[str, str] = {
    "1": "内用",
    "2": "内用",
    "3": "歯科",
    "4": "注射",
    "6": "外用",
    "8": "他",
}


def katakana_to_hiragana(text: str) -> str:
    """Convert Katakana characters to Hiragana."""
    return "".join(
        chr(ord(c) - 0x60) if 0x30A1 <= ord(c) <= 0x30F6 else c for c in text
    )


def find_default_csv_path() -> Path | None:
    """Look for y_ALL*.csv in common locations."""
    candidates = [
        Path("yj"),
        Path("../yj"),
        Path("../../yj"),
        Path("data_tools/yj"),
        Path("../data_tools/yj"),
    ]
    for directory in candidates:
        if directory.exists():
            for p in directory.glob("y_ALL*.csv"):
                return p
    return None


def parse_yj_csv(csv_path: Path) -> list[dict[str, str]]:
    """Parse MHLW YJ CSV file and return compact medicine objects."""
    if not csv_path.exists():
        raise FileNotFoundError(f"YJ CSV not found at {csv_path}")

    items: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()

    with open(csv_path, encoding="cp932", errors="replace") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) < 38:
                continue

            # Check validity: Col 30 is expiration date; 99999999 means active
            end_date = row[30].strip()
            if end_date != "99999999":
                continue

            name = row[4].strip()
            if not name:
                continue

            yj_code = row[31].strip()
            key = (name, yj_code)
            if key in seen:
                continue
            seen.add(key)

            # Col 6 is half-width katakana reading
            raw_reading = unicodedata.normalize("NFKC", row[6].strip())
            hiragana_reading = katakana_to_hiragana(raw_reading).lower()

            generic_name = row[37].replace("【般】", "").strip()
            category_code = row[27].strip()
            category = CATEGORY_MAP.get(category_code, "他")

            items.append(
                {
                    "n": name,
                    "k": raw_reading,
                    "h": hiragana_reading,
                    "y": yj_code,
                    "g": generic_name,
                    "c": category,
                }
            )

    return items


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

    csv_path = args.csv_path or find_default_csv_path()
    if not csv_path:
        logger.error("Could not find y_ALL*.csv. Please specify with --csv-path.")
        sys.exit(1)

    logger.info(f"Parsing YJ CSV from: {csv_path}")
    items = parse_yj_csv(csv_path)
    logger.info(f"Extracted {len(items)} active medicine entries.")

    outputs: list[Path] = args.output
    if not outputs:
        # Default output paths
        default_frontend = Path("frontend/public/data/medicines.json")
        default_backend = Path("data_tools/structured/medicines_autocomplete.json")
        outputs = [default_frontend, default_backend]

    json_str = json.dumps(items, ensure_ascii=False, separators=(",", ":"))

    for out in outputs:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json_str, encoding="utf-8")
        size_kb = len(json_str.encode("utf-8")) / 1024
        logger.info(f"Wrote {len(items)} items to {out} ({size_kb:.1f} KB)")


if __name__ == "__main__":
    main()
