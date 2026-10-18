"""Read-only, WAL-aware observations of test-owned databases."""

import hashlib
import json
import sqlite3
import sys
from contextlib import closing
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")


def snapshot(index, *, include_journal_mode=False):
    with (
        closing(
            sqlite3.connect(index.resolve().as_uri() + "?mode=ro", uri=True)
        ) as source,
        closing(sqlite3.connect(":memory:")) as copy,
    ):
        source.backup(copy)
        schema = copy.execute(
            "SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY type,name"
        ).fetchall()
        tables = {}
        for kind, name, _, _ in schema:
            if kind != "table":
                continue
            quoted = '"' + name.replace('"', '""') + '"'
            columns = [row[1] for row in copy.execute(f"PRAGMA table_info({quoted})")]
            rows = copy.execute(f"SELECT * FROM {quoted}").fetchall()
            rows.sort(key=repr)
            rows = [
                [
                    {"blob_hex": value.hex()} if isinstance(value, bytes) else value
                    for value in row
                ]
                for row in rows
            ]
            tables[name] = {"columns": columns, "rows": rows}
        result = {
            "schema": schema,
            "tables": tables,
            "integrity": copy.execute("PRAGMA integrity_check").fetchone()[0],
        }
        if include_journal_mode:
            result["journal_mode"] = source.execute("PRAGMA journal_mode").fetchone()[0]
        result["logical_sha256"] = hashlib.sha256(
            json.dumps([schema, tables], ensure_ascii=False, sort_keys=True).encode(
                "utf-8"
            )
        ).hexdigest()
        return result


if __name__ == "__main__":
    mode, target = sys.argv[1:]
    index = Path(target)
    if mode != "snapshot":
        raise ValueError("Only snapshot mode is supported")
    result = snapshot(index, include_journal_mode=True)
    print(json.dumps(result, ensure_ascii=False))
