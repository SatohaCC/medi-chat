"""旧索引のread-only接続から整合したSQLite snapshotを複製する。"""

import sqlite3
from contextlib import closing
from pathlib import Path


def backup_legacy_index(source: Path, output: Path) -> None:
    with closing(
        sqlite3.connect(f"{source.resolve().as_uri()}?mode=ro", uri=True)
    ) as origin:
        # 排他的な作成で、接続直前に現れた既存出力も上書きしない。
        with output.open("xb"):
            pass
        with closing(sqlite3.connect(output)) as target:
            origin.backup(target)
