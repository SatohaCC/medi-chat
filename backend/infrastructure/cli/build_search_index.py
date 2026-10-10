"""添付文書の検索索引を構築するコマンド。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sqlalchemy.engine import URL

from ...config.database_settings import resolve_database_settings
from ..composition.index_verifier import verify_schema_readiness
from ..persistence.index_writer import SqlAlchemyIndexWriter
from ..persistence.sqlite_engine import create_sqlite_engine
from ..sources.file_index_source import FileIndexSourceReader


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
        snapshot = FileIndexSourceReader(settings.structured_dir).read_snapshot()
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
