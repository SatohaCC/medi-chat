"""未管理の既存索引を別ファイルへ移行するCLI入口。"""

import argparse
import sqlite3
from pathlib import Path

from ...migrations.legacy_copy_stamp import stamp_and_upgrade_legacy_copy
from ..persistence.legacy_content_validator import (
    validate_legacy_content,
)
from ..persistence.legacy_index_backup import backup_legacy_index
from ..persistence.legacy_migration_verifier import (
    read_legacy_migration_snapshot,
    verify_legacy_migration,
)
from ..persistence.legacy_schema_validator import validate_legacy_schema


def main() -> int:
    parser = argparse.ArgumentParser(description="Migrate a legacy v3 SQLite index")
    parser.add_argument("--source-index", type=Path, required=True)
    parser.add_argument("--output-index", type=Path, required=True)
    args = parser.parse_args()
    source = args.source_index.resolve()
    output = args.output_index.resolve()
    if source == output or (
        source.exists() and output.exists() and source.samefile(output)
    ):
        parser.error("Source and output indexes must not be the same file")
    if output.exists():
        parser.error(f"Output index already exists: {output}")
    try:
        backup_legacy_index(source, output)
        validate_legacy_schema(output)
        validate_legacy_content(output)
        before = read_legacy_migration_snapshot(output)
        expected_revision = stamp_and_upgrade_legacy_copy(output)
        revision = verify_legacy_migration(output, before, expected_revision)
    except sqlite3.DatabaseError:
        parser.error("SQLite integrity validation failed: corrupt index")
    except ValueError as error:
        parser.error(str(error))
    print(
        f"Verified migration from {source} to {output}, revision {revision}: "
        f"{len(before.rows['documents'])} documents, {len(before.rows['units'])} units"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
