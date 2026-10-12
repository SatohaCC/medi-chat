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
