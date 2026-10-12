"""SQLite接続設定を共有するEngine生成の境界。"""

import sqlite3
from contextlib import closing

from package_inserts.text_formatting import section_code_sort_key
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.pool import ConnectionPoolEntry

from .owned_sqlite import OwnedSqliteConnection


def _compare_section_codes(left: str, right: str) -> int:
    left_key = section_code_sort_key(left)
    right_key = section_code_sort_key(right)
    return (left_key > right_key) - (left_key < right_key)


def _configure_connection(
    connection: sqlite3.Connection, connection_record: ConnectionPoolEntry
) -> None:
    connection.create_collation("section_code_order", _compare_section_codes)
    with closing(connection.cursor()) as cursor:
        cursor.execute("PRAGMA busy_timeout=30000")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA cache_size=-64000")


def create_sqlite_engine(database_url: str) -> Engine:
    engine = create_engine(
        database_url, connect_args={"factory": OwnedSqliteConnection}
    )
    event.listen(engine, "connect", _configure_connection)
    return engine
