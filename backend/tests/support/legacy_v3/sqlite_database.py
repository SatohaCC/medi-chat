"""添付文書索引の SQLite 接続とトランザクション。"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from backend.domain.retrieval.services import section_code_sort_key


def _compare_section_codes(str1: str, str2: str) -> int:
    k1, k2 = section_code_sort_key(str1), section_code_sort_key(str2)
    return (k1 > k2) - (k1 < k2)


class SQLiteDatabase:
    def __init__(self, index_path: Path) -> None:
        self.index_path = index_path.resolve()

    def _open_connection(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.index_path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.create_collation("section_code_order", _compare_section_codes)
        connection.execute("PRAGMA busy_timeout=30000")
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=NORMAL")
        connection.execute("PRAGMA cache_size=-64000")
        return connection

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        connection = self._open_connection()
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
