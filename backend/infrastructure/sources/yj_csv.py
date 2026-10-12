"""CP932 YJ master CSV boundary."""

import csv
from pathlib import Path

from ...application.medicine.autocomplete import project_yj_row


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
