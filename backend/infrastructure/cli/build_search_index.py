"""添付文書の検索索引を構築するコマンド。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sqlalchemy.engine import URL

from ...config.database_settings import resolve_database_settings
from ...config.import_settings import resolve_import_directory
from ..composition.index_verifier import verify_schema_readiness
from ..persistence.attachment_import_store import FileAttachmentImportStore
from ..persistence.index_writer import SqlAlchemyIndexWriter
from ..persistence.registration_lock import registration_lock
from ..persistence.registration_publisher import SqliteRegistrationPublisher
from ..persistence.registration_reader import read_registered_snapshot
from ..persistence.sqlite_engine import create_sqlite_engine
from ..persistence.sqlite_recovery import recover_sqlite_journal


def main() -> int:
    parser = argparse.ArgumentParser(
        description="medi-chat package insert SQLite index builder and verifier"
    )
    parser.add_argument(
        "--structured-dir",
        type=Path,
        default=None,
        help="Path to structured directory",
    )
    parser.add_argument(
        "--index-path",
        type=Path,
        default=None,
        help="Path to output sqlite3 database",
    )
    parser.add_argument(
        "--database-url",
        default=None,
        help="Database connection URL",
    )
    args = parser.parse_args()
    settings = resolve_database_settings(
        structured_dir=args.structured_dir,
        index_path=args.index_path,
        database_url=args.database_url,
    )

    try:
        recover_sqlite_journal(settings.index_path)
        verify_schema_readiness(settings.index_path)
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(
        f"Building/verifying index from {settings.structured_dir} "
        f"to {settings.index_path}..."
    )
    engine = create_sqlite_engine(
        URL.create("sqlite", database=settings.index_path.as_posix()).render_as_string(
            hide_password=False
        )
    )
    try:
        with registration_lock(settings.index_path):
            if read_registered_snapshot(settings.index_path) is None:
                print(
                    "Error: initial_registration_required; run initialize_registrations after backup and migration",
                    file=sys.stderr,
                )
                return 1
        SqliteRegistrationPublisher(
            settings.index_path,
            FileAttachmentImportStore(resolve_import_directory()),
            allowed_roots=(
                settings.structured_dir,
                settings.structured_dir.parent / "originals",
            ),
        ).recover()
        with registration_lock(settings.index_path):
            snapshot = read_registered_snapshot(settings.index_path)
            if snapshot is None:
                print(
                    "Error: initial_registration_required; run initialize_registrations after backup and migration",
                    file=sys.stderr,
                )
                return 1
            result = SqlAlchemyIndexWriter(engine).replace(snapshot)
    finally:
        engine.dispose()

    print(
        f"Index ready: {{'document_count': {result.document_count}, 'unit_count': {result.unit_count}}} "
        f"({len(snapshot.medicines)} medicines loaded)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
