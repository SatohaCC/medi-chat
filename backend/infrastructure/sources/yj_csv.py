"""CP932 YJ master CSV boundary."""

import csv
import unicodedata
from pathlib import Path

from ...application.medicine.autocomplete import katakana_to_hiragana

CATEGORY_MAP: dict[str, str] = {
    "1": "内用",
    "2": "内用",
    "3": "歯科",
    "4": "注射",
    "6": "外用",
    "8": "他",
}


def project_yj_row(row: list[str]) -> dict[str, str] | None:
    if len(row) < 38:
        return None
    # Check validity: Col 30 is expiration date; 99999999 means active
    end_date = row[30].strip()
    if end_date != "99999999":
        return None

    name = row[4].strip()
    if not name:
        return None

    yj_code = row[31].strip()

    # Col 6 is half-width katakana reading
    raw_reading = unicodedata.normalize("NFKC", row[6].strip())
    hiragana_reading = katakana_to_hiragana(raw_reading).lower()

    generic_name = row[37].replace("【般】", "").strip()
    category_code = row[27].strip()
    category = CATEGORY_MAP.get(category_code, "他")

    return {
        "n": name,
        "k": raw_reading,
        "h": hiragana_reading,
        "y": yj_code,
        "g": generic_name,
        "c": category,
    }


def parse_yj_csv(csv_path: Path) -> list[dict[str, str]]:
    if not csv_path.exists():
        raise FileNotFoundError(f"YJ CSV not found at {csv_path}")
    items = []
    seen = set()
    with csv_path.open(encoding="cp932", errors="replace") as stream:
        for row in csv.reader(stream):
            item = project_yj_row(row)
            if item is None:
                continue
            key = item["n"], item["y"]
            if key not in seen:
                items.append(item)
                seen.add(key)
    return items
