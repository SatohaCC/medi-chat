"""アプリ起動時の索引準備状態と指紋整合性を検証する境界。"""

from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

from ...application.indexing.index_errors import IndexSourceError
from ..persistence.owned_sqlite import OwnedSqliteConnection

REQUIRED_TABLES = frozenset(
    {
        "documents",
        "medicines",
        "units",
        "index_meta",
        "unit_fts",
        "registration_receipts",
        "active_registrations",
        "registration_generations",
        "registration_state",
        "generation_leases",
        "registration_owned_files",
        "registration_version_artifacts",
    }
)
EXPECTED_REVISION = "0002_registration_generations"


def verify_schema_readiness(index_path: Path) -> None:
    """Alembic migrationが完了し必須テーブルが存在することを検証する。"""
    if not index_path.is_file():
        raise RuntimeError(
            f"Database file does not exist at {index_path}. "
            "Please run 'alembic upgrade head' and 'build_search_index'."
        )

    uri = f"{index_path.resolve().as_uri()}?mode=ro"
    try:
        connection = sqlite3.connect(uri, uri=True, factory=OwnedSqliteConnection)
    except (sqlite3.DatabaseError, OSError) as exc:
        raise RuntimeError(
            f"Database at {index_path} cannot be opened in read-only mode: {exc}. "
            "Please run 'alembic upgrade head'."
        ) from exc

    with closing(connection):
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        if "alembic_version" not in tables:
            raise RuntimeError(
                f"Database at {index_path} is unmanaged (missing alembic_version table). "
                "Please run 'alembic upgrade head'."
            )

        rev_rows = connection.execute(
            "SELECT version_num FROM alembic_version"
        ).fetchall()
        if not rev_rows or rev_rows[0][0] != EXPECTED_REVISION:
            current_rev = rev_rows[0][0] if rev_rows else None
            raise RuntimeError(
                f"Database at {index_path} has revision {current_rev}, "
                f"expected '{EXPECTED_REVISION}'. Please run 'alembic upgrade head'."
            )

        missing_tables = sorted(REQUIRED_TABLES - tables)
        if missing_tables:
            raise RuntimeError(
                f"Database at {index_path} is missing required tables: {missing_tables}. "
                "Please run 'alembic upgrade head'."
            )


def verify_index_readiness(structured_dir: Path, index_path: Path) -> None:
    """起動前にAlembic migrationと索引構築が完了していることを検証する。

    DDL・自動build・自動stampで補完せず、不足時は理由と必要コマンドを示す。
    """
    verify_schema_readiness(index_path)

    uri = f"{index_path.resolve().as_uri()}?mode=ro"
    connection = sqlite3.connect(uri, uri=True, factory=OwnedSqliteConnection)
    with closing(connection):
        doc_count = connection.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
        if doc_count == 0:
            raise RuntimeError(
                f"Database at {index_path} is unbuilt (0 indexed documents). "
                "Please run 'python -m backend.infrastructure.cli.build_search_index'."
            )

        fp_row = connection.execute(
            "SELECT value FROM index_meta WHERE key='source_fingerprint'"
        ).fetchone()
        if not fp_row or not fp_row[0]:
            raise RuntimeError(
                f"Database at {index_path} has no source fingerprint. "
                "Please run 'python -m backend.infrastructure.cli.build_search_index'."
            )
        stored_fingerprint = str(fp_row[0])

    if not structured_dir.is_dir():
        raise RuntimeError(
            f"Structured data directory does not exist: {structured_dir}. "
            "Please verify data and run 'python -m backend.infrastructure.cli.build_search_index'."
        )

    try:
        from ..sources.registration_source import read_registered_snapshot

        registered = read_registered_snapshot(index_path)
        if registered is None:
            raise RuntimeError(
                "initial_registration_required: after backup and explicit migration, "
                "run python -m backend.infrastructure.cli.initialize_registrations"
            )
        if registered.fingerprint != stored_fingerprint:
            raise IndexSourceError(
                "Published generation fingerprint differs from index"
            )
    except (IndexSourceError, OSError) as exc:
        raise RuntimeError(
            f"Structured data at {structured_dir} is invalid: {exc}. "
            "Please verify data and run 'python -m backend.infrastructure.cli.build_search_index'."
        ) from exc
