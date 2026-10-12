"""状態を変更するPRAGMAを使わないSQLite読取接続。"""

import sqlite3
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.pool import NullPool

from .owned_sqlite import OwnedSqliteConnection
from .sqlite_engine import _compare_section_codes


def create_readonly_engine(index_path: Path) -> Engine:
    uri = f"{index_path.resolve().as_uri()}?mode=ro"

    def connect() -> sqlite3.Connection:
        connection = sqlite3.connect(uri, uri=True, factory=OwnedSqliteConnection)
        connection.create_collation("section_code_order", _compare_section_codes)
        return connection

    # 接続を実行threadに残さず、各読取のwith終了時に同じthreadでcloseする。
    return create_engine("sqlite://", creator=connect, poolclass=NullPool)
