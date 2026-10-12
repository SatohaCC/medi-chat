"""Test-owned historical restoration and read-only, WAL-aware observations."""

import hashlib
import json
import sqlite3
import sys
from argparse import Namespace
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


def restore(index):
    from alembic import command
    from alembic.config import Config

    from backend.infrastructure.persistence.legacy_content_validator import (
        validate_legacy_content,
    )
    from backend.migrations.legacy_copy_stamp import (
        STAMP_COPY_ATTRIBUTE,
        LegacyCopyStamp,
        validate_stamp_copy,
    )
    from backend.tests.startup_recovery_fixture import restore_manifest_v3_fixture

    fixture = ROOT / "backend/tests/fixtures/pre_registration_manifest_v3.sqlite3.gz"
    assert (
        hashlib.sha256(fixture.read_bytes()).hexdigest()
        == "dd571bd3c28ba13479240fb8422c4404df1c29f391f15e66ffddd5d3e02983a4"
    )
    restore_manifest_v3_fixture(index)
    validate_legacy_content(index)
    before = snapshot(index)
    config = Config(str(ROOT / "backend/alembic.ini"))
    config.cmd_opts = Namespace(x=[f"index_path={index.resolve()}"])
    approval = LegacyCopyStamp(index.resolve())
    validate_stamp_copy(approval, index)
    config.attributes[STAMP_COPY_ATTRIBUTE] = approval
    command.stamp(config, "0001_v3_schema")
    after = snapshot(index)
    assert after["tables"].pop("alembic_version")["rows"] == [["0001_v3_schema"]]
    after["schema"] = [row for row in after["schema"] if row[2] != "alembic_version"]
    # The digest includes the revision table; compare the remaining schema/rows directly.
    before.pop("logical_sha256")
    after.pop("logical_sha256")
    assert before == after
    return {
        "path": str(index),
        "gzip_sha256": hashlib.sha256(fixture.read_bytes()).hexdigest(),
    }


if __name__ == "__main__":
    mode, target = sys.argv[1:]
    index = Path(target)
    result = (
        restore(index)
        if mode == "restore"
        else snapshot(index, include_journal_mode=True)
    )
    print(json.dumps(result, ensure_ascii=False))
