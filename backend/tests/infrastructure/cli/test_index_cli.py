"""索引構築CLI入口の検証。"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from backend.infrastructure.persistence.index_reader import SqlAlchemyIndexReader
from backend.infrastructure.persistence.sqlite_engine import create_sqlite_engine
from backend.tests.infrastructure.persistence.test_alembic_migrations import (
    _migrate_database,
)
from backend.tests.support.paths import PROJECT_ROOT
from backend.tests.support.registration_runtime_fixtures import (
    register_synthetic_prepared_index,
)
from backend.tests.support.storage_fixtures import write_structured_document
from sqlalchemy.engine import URL


def test_existing_build_entrypoint_requires_migrated_database(tmp_path: Path) -> None:
    structured = write_structured_document(tmp_path)
    index_path = tmp_path / "index.sqlite3"

    # 1. 未マイグレーション（ファイルなし）の場合、終了コード非0で拒否されること
    res_unmigrated = subprocess.run(
        [
            sys.executable,
            "-m",
            "backend.infrastructure.cli.build_search_index",
            "--structured-dir",
            str(structured),
            "--index-path",
            str(index_path),
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )
    assert res_unmigrated.returncode != 0
    assert "upgrade head" in res_unmigrated.stderr

    # 2. マイグレーション実行後、正常にビルドが成功すること
    _migrate_database(index_path, structured)
    unregistered = subprocess.run(
        [
            sys.executable,
            "-m",
            "backend.infrastructure.cli.build_search_index",
            "--structured-dir",
            str(structured),
            "--index-path",
            str(index_path),
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )
    assert unregistered.returncode != 0
    assert "initialize_registrations" in unregistered.stderr
    register_synthetic_prepared_index(structured, index_path)

    res_build = subprocess.run(
        [
            sys.executable,
            "-m",
            "backend.infrastructure.cli.build_search_index",
            "--structured-dir",
            str(structured),
            "--index-path",
            str(index_path),
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )
    assert res_build.returncode == 0
    assert "Index ready" in res_build.stdout

    # 3. 構築された索引から正常にデータが検索・読取できること
    engine = create_sqlite_engine(
        URL.create("sqlite", database=index_path.as_posix()).render_as_string(
            hide_password=False
        )
    )
    try:
        reader = SqlAlchemyIndexReader(engine)
        stats = reader._read_index_stats()
        assert stats["document_count"] == 1
        assert stats["unit_count"] == 1

        doc = reader._get_document("test_001")
        assert doc is not None
        document_obj = doc["document"]
        assert isinstance(document_obj, dict)
        assert document_obj["generic_name"] == "テスト成分"
    finally:
        engine.dispose()
