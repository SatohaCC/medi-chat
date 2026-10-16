"""Let SQLite recover its own WAL under the publication lock, without DDL/DML."""

import os
import sqlite3
import time
from contextlib import closing
from pathlib import Path

from .owned_sqlite import OwnedSqliteConnection
from .registration_lock import registration_lock


def recover_sqlite_journal(index_path: Path, *, locked: bool = False) -> None:
    if not index_path.is_file():
        raise RuntimeError(
            f"Database file does not exist at {index_path}. "
            "Please run 'alembic upgrade head' and "
            "'python -m backend.infrastructure.cli.initialize_registrations' "
            "after backup and explicit migration."
        )

    def read_schema() -> None:
        with closing(
            sqlite3.connect(
                index_path.resolve().as_uri() + "?mode=rw",
                uri=True,
                factory=OwnedSqliteConnection,
            )
        ) as connection:
            connection.execute("SELECT name FROM sqlite_master").fetchall()

    def recover() -> None:
        deadline = time.monotonic() + 3
        while True:
            try:
                read_schema()
                return
            except sqlite3.OperationalError as exc:
                if (
                    os.name != "nt"
                    or exc.sqlite_errorcode != sqlite3.SQLITE_IOERR_TRUNCATE
                    or time.monotonic() >= deadline
                ):
                    raise
                time.sleep(0.05)

    if locked:
        recover()
    else:
        with registration_lock(index_path):
            recover()


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
