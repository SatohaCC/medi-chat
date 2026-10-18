"""実Alembicによる新規SQLite schemaを旧v3の物理契約と照合する。"""

from __future__ import annotations

import re
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import pytest
from alembic.config import CommandLine, Config
from alembic.script import ScriptDirectory
from backend.infrastructure.persistence.index_writer import SqlAlchemyIndexWriter
from backend.infrastructure.persistence.sqlite_engine import create_sqlite_engine
from backend.infrastructure.sources.file_index_source import FileIndexSourceReader
from backend.tests.support.paths import BACKEND_ROOT
from backend.tests.support.storage_fixtures import write_structured_document


def _build_current_index(source: Path, index_path: Path) -> None:
    engine = create_sqlite_engine(f"sqlite:///{index_path.as_posix()}")
    try:
        SqlAlchemyIndexWriter(engine).replace(
            FileIndexSourceReader(source).read_snapshot()
        )
    finally:
        engine.dispose()


def _migrate_database(
    index_path: Path,
    structured_dir: Path,
    *,
    operation: Literal["upgrade", "downgrade"] = "upgrade",
) -> None:
    ini_path = BACKEND_ROOT / "alembic.ini"
    CommandLine().main(
        argv=[
            "-c",
            str(ini_path),
            "-x",
            f"structured_dir={structured_dir}",
            "-x",
            f"index_path={index_path}",
            operation,
            "head" if operation == "upgrade" else "base",
        ]
    )


def test_upgrade_creates_v3_compatible_schema(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "structured"
    source.mkdir()
    index_path = tmp_path / "new.sqlite3"
    index_path.touch()
    assert index_path.stat().st_size == 0
    for key in (
        "MEDI_CHAT_STRUCTURED_DIR",
        "MEDI_CHAT_INDEX_PATH",
        "MEDI_CHAT_DATABASE_URL",
    ):
        monkeypatch.delenv(key, raising=False)
    ini_path = BACKEND_ROOT / "alembic.ini"
    _migrate_database(index_path, source)

    scripts = ScriptDirectory.from_config(Config(str(ini_path)))
    heads = scripts.get_heads()
    assert len(heads) == 1
    registration_revision = scripts.get_revision(heads[0])
    assert registration_revision is not None
    assert registration_revision.revision == "0002_registration_generations"
    assert registration_revision.down_revision == "0001_v3_schema"
    initial_revision = scripts.get_revision("0001_v3_schema")
    assert initial_revision is not None
    assert initial_revision.down_revision is None

    # 期待値は承認計画7章と旧PackageInsertIndexBuilderのv3 DDLから固定する。
    # 新metadataやmigration実装から生成しない。tupleは列名・型・NOT NULL・PK順序。
    expected_columns = {
        "documents": [
            ("document_key", "TEXT", 0, 1),
            ("payload_json", "TEXT", 1, 0),
        ],
        "medicines": [
            ("document_key", "TEXT", 1, 0),
            ("yj_code", "TEXT", 0, 0),
            ("brand_name", "TEXT", 1, 0),
            ("generic_name", "TEXT", 1, 0),
            ("english_name", "TEXT", 1, 0),
            ("hiragana_name", "TEXT", 1, 0),
            ("pmda_url", "TEXT", 1, 0),
            ("revision_json", "TEXT", 1, 0),
        ],
        "units": [
            ("unit_id", "TEXT", 0, 1),
            ("document_key", "TEXT", 1, 0),
            ("section_code", "TEXT", 1, 0),
            ("kind", "TEXT", 1, 0),
            ("payload_json", "TEXT", 1, 0),
        ],
        "index_meta": [("key", "TEXT", 0, 1), ("value", "TEXT", 1, 0)],
    }
    connection = sqlite3.connect(index_path)
    try:
        assert connection.execute(
            "SELECT version_num FROM alembic_version"
        ).fetchall() == [(heads[0],)]
        for table_name, expected in expected_columns.items():
            columns = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
            assert [
                (row[1], row[2].upper(), row[3], row[5]) for row in columns
            ] == expected
            assert connection.execute(
                f"SELECT COUNT(*) FROM {table_name}"
            ).fetchone() == (0,)

        expected_indexes = {
            "idx_medicines_yj": ("medicines", ("yj_code",)),
            "idx_medicines_doc": ("medicines", ("document_key",)),
            "units_by_document_section": (
                "units",
                ("document_key", "section_code", "kind"),
            ),
        }
        ordinary_indexes = dict(
            connection.execute(
                "SELECT name, tbl_name FROM sqlite_master "
                "WHERE type='index' AND sql IS NOT NULL "
                "AND tbl_name IN ('documents', 'medicines', 'units', 'index_meta')"
            ).fetchall()
        )
        assert ordinary_indexes == {
            name: table for name, (table, _) in expected_indexes.items()
        }
        for name, (table, expected) in expected_indexes.items():
            assert (
                tuple(
                    row[2] for row in connection.execute(f"PRAGMA index_info({name})")
                )
                == expected
            )
            index = next(
                row
                for row in connection.execute(f"PRAGMA index_list({table})")
                if row[1] == name
            )
            assert index[2] == 0  # 既存の通常索引はUNIQUEではない。

        fts_row = connection.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='unit_fts'"
        ).fetchone()
        assert fts_row is not None
        fts_definition = re.search(
            r"\busing\s+fts5\s*\((.*)\)\s*;?\s*$", fts_row[0], re.I | re.S
        )
        assert fts_definition is not None
        arguments = [
            " ".join(argument.replace("'", "").replace('"', "").strip().lower().split())
            for argument in fts_definition.group(1).split(",")
        ]
        assert arguments[:6] == [
            "unit_id unindexed",
            "document_key unindexed",
            "section_code unindexed",
            "kind unindexed",
            "query_text",
            "drug_name",
        ]
        assert [argument.replace(" ", "") for argument in arguments[6:]] == [
            "tokenize=trigram"
        ]
        assert [
            row[1] for row in connection.execute("PRAGMA table_info(unit_fts)")
        ] == [
            "unit_id",
            "document_key",
            "section_code",
            "kind",
            "query_text",
            "drug_name",
        ]

        connection.execute(
            "INSERT INTO unit_fts(unit_id, document_key, section_code, kind, query_text, drug_name) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                "unitmarker",
                "documentmarker",
                "sectionmarker",
                "kindmarker",
                "アスピリンの頭痛",
                "テスト薬",
            ),
        )
        for query in ("query_text:スピリ", "drug_name:テスト"):
            assert connection.execute(
                "SELECT unit_id FROM unit_fts WHERE unit_fts MATCH ?", (query,)
            ).fetchall() == [("unitmarker",)]
        for query in (
            "unit_id:unitmarker",
            "document_key:documentmarker",
            "section_code:sectionmarker",
            "kind:kindmarker",
        ):
            assert (
                connection.execute(
                    "SELECT unit_id FROM unit_fts WHERE unit_fts MATCH ?", (query,)
                ).fetchall()
                == []
            )
    finally:
        connection.close()


@dataclass(frozen=True)
class ManagedIndexSnapshot:
    rows: dict[str, tuple[tuple[object, ...], ...]]
    counts: dict[str, int]
    fingerprint: str
    fts_results: tuple[tuple[str], ...]


def _snapshot_managed_index(index_path: Path) -> ManagedIndexSnapshot:
    tables = (
        "alembic_version",
        "documents",
        "medicines",
        "units",
        "index_meta",
        "unit_fts",
    )
    with closing(sqlite3.connect(index_path)) as connection:
        rows = {
            table: tuple(
                connection.execute(
                    f"SELECT {'rowid, *' if table == 'unit_fts' else '*'} FROM {table} ORDER BY rowid"
                ).fetchall()
            )
            for table in tables
        }
        counts = {
            table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in tables
        }
        fingerprint_row = connection.execute(
            "SELECT value FROM index_meta WHERE key='source_fingerprint'"
        ).fetchone()
        assert fingerprint_row is not None
        assert isinstance(fingerprint_row[0], str) and fingerprint_row[0].strip()
        results = tuple(
            connection.execute(
                "SELECT unit_id FROM unit_fts WHERE unit_fts MATCH ? ORDER BY unit_id",
                ("注意して",),
            ).fetchall()
        )
    return ManagedIndexSnapshot(rows, counts, fingerprint_row[0], results)


def test_repeated_upgrade_preserves_index(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    for key in (
        "MEDI_CHAT_STRUCTURED_DIR",
        "MEDI_CHAT_INDEX_PATH",
        "MEDI_CHAT_DATABASE_URL",
    ):
        monkeypatch.delenv(key, raising=False)
    source = write_structured_document(tmp_path, unit_count=3)
    index_path = tmp_path / "managed.sqlite3"
    _migrate_database(index_path, source)
    # 現在の明示builderで準備する。後続のCore writer/use caseを先行要求しない。
    _build_current_index(source, index_path)
    before = _snapshot_managed_index(index_path)
    assert before.counts["alembic_version"] == 1
    assert {
        table: before.counts[table]
        for table in ("documents", "medicines", "units", "unit_fts")
    } == {
        "documents": 1,
        "medicines": 1,
        "units": 3,
        "unit_fts": 3,
    }
    assert before.fts_results == (
        ("test_001:000",),
        ("test_001:001",),
        ("test_001:002",),
    )

    _migrate_database(index_path, source)
    after = _snapshot_managed_index(index_path)
    assert after.rows["alembic_version"] == before.rows["alembic_version"]
    assert after.rows == before.rows
    assert after.counts == before.counts
    assert after.fingerprint == before.fingerprint
    assert after.fts_results == before.fts_results


def test_downgrade_and_reupgrade_recreate_managed_schema(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """downgradeはデータを削除する。復旧は明示upgrade＋buildで行う。"""
    for key in (
        "MEDI_CHAT_STRUCTURED_DIR",
        "MEDI_CHAT_INDEX_PATH",
        "MEDI_CHAT_DATABASE_URL",
    ):
        monkeypatch.delenv(key, raising=False)
    source = write_structured_document(tmp_path, unit_count=3)
    index_path = tmp_path / "downgrade-deletes-data.sqlite3"
    _migrate_database(index_path, source)
    _build_current_index(source, index_path)
    before = _snapshot_managed_index(index_path)
    assert before.counts["documents"] == 1
    assert before.counts["units"] == 3
    assert before.fts_results == (
        ("test_001:000",),
        ("test_001:001",),
        ("test_001:002",),
    )

    _migrate_database(index_path, source, operation="downgrade")
    with closing(sqlite3.connect(index_path)) as connection:
        remaining_objects = {
            row[0] for row in connection.execute("SELECT name FROM sqlite_master")
        }
        assert remaining_objects.isdisjoint(
            {
                "documents",
                "medicines",
                "units",
                "index_meta",
                "unit_fts",
                "idx_medicines_yj",
                "idx_medicines_doc",
                "units_by_document_section",
            }
        )
        assert not any(name.startswith("unit_fts_") for name in remaining_objects)
        if "alembic_version" in remaining_objects:
            assert (
                connection.execute("SELECT version_num FROM alembic_version").fetchall()
                == []
            )

    _migrate_database(index_path, source)
    with closing(sqlite3.connect(index_path)) as connection:
        # 再upgradeだけでは削除済みデータは戻らない。
        for table in ("documents", "medicines", "units", "unit_fts"):
            assert connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone() == (
                0,
            )
        assert (
            connection.execute(
                "SELECT value FROM index_meta WHERE key='source_fingerprint'"
            ).fetchall()
            == []
        )
        assert connection.execute(
            "SELECT version_num FROM alembic_version"
        ).fetchall() == list(before.rows["alembic_version"])

    _build_current_index(source, index_path)
    rebuilt = _snapshot_managed_index(index_path)
    assert rebuilt == before


@dataclass(frozen=True)
class ExistingDatabaseSnapshot:
    schema: tuple[tuple[object, ...], ...]
    rows: dict[str, tuple[tuple[object, ...], ...]]
    revision: tuple[str, ...] | None


def _snapshot_existing_database(index_path: Path) -> ExistingDatabaseSnapshot:
    """未知tableやFTS shadowを含め、実DB全体を意味のある値で保存する。"""
    with closing(sqlite3.connect(index_path)) as connection:
        schema = tuple(
            connection.execute(
                "SELECT type, name, tbl_name, sql FROM sqlite_master ORDER BY type, name"
            ).fetchall()
        )
        tables = [
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        ]
        rows = {}
        for table in tables:
            identifier = '"' + table.replace('"', '""') + '"'
            # FTSのWITHOUT ROWID shadowも含むためrowidを前提にしない。
            rows[table] = tuple(
                sorted(
                    connection.execute(f"SELECT * FROM {identifier}").fetchall(),
                    key=repr,
                )
            )
        revision = (
            tuple(row[0] for row in rows["alembic_version"])
            if "alembic_version" in rows
            else None
        )
    return ExistingDatabaseSnapshot(schema, rows, revision)


@pytest.mark.parametrize(
    "variant", ["unmanaged_v3", "unmanaged_unknown_table", "unknown_revision"]
)
def test_upgrade_rejects_unmanaged_or_unknown_database(
    tmp_path: Path,
    variant: str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    caplog: pytest.LogCaptureFixture,
) -> None:
    for key in (
        "MEDI_CHAT_STRUCTURED_DIR",
        "MEDI_CHAT_INDEX_PATH",
        "MEDI_CHAT_DATABASE_URL",
    ):
        monkeypatch.delenv(key, raising=False)
    source = write_structured_document(tmp_path, unit_count=3)
    index_path = tmp_path / f"{variant}.sqlite3"
    unknown_revision = "unknown_revision_for_tc24"
    if variant == "unmanaged_unknown_table":
        with closing(sqlite3.connect(index_path)) as connection:
            connection.execute(
                "CREATE TABLE mystery_table (id TEXT PRIMARY KEY, payload TEXT NOT NULL)"
            )
            connection.execute(
                "INSERT INTO mystery_table VALUES (?, ?)",
                ("sentinel", "変更してはいけない値"),
            )
            connection.commit()
    else:
        _migrate_database(index_path, source)
        _build_current_index(source, index_path)
        if variant == "unmanaged_v3":
            with sqlite3.connect(index_path) as connection:
                connection.execute("DROP TABLE alembic_version")
        if variant == "unknown_revision":
            with closing(sqlite3.connect(index_path)) as connection:
                connection.execute(
                    "UPDATE alembic_version SET version_num=?", (unknown_revision,)
                )
                connection.commit()

    before = _snapshot_existing_database(index_path)
    if variant == "unknown_revision":
        assert before.revision == (unknown_revision,)
    else:
        assert before.revision is None
    if variant == "unmanaged_v3":
        assert any(row[0] == "source_fingerprint" for row in before.rows["index_meta"])
        assert len(before.rows["units"]) == 3
    elif variant == "unmanaged_unknown_table":
        assert before.rows["mystery_table"] == (("sentinel", "変更してはいけない値"),)
    capsys.readouterr()
    caplog.clear()

    error: Exception | SystemExit | None = None
    try:
        _migrate_database(index_path, source)
    except (ImportError, TypeError, NotImplementedError):
        raise
    except (Exception, SystemExit) as caught:
        error = caught
    captured = capsys.readouterr()
    after = _snapshot_existing_database(index_path)
    assert after.schema == before.schema, (
        "拒否時に既存schemaまたはversion tableを変更した"
    )
    assert after.rows == before.rows, "拒否時に既存データを変更した"
    assert after.revision == before.revision, "拒否時にrevisionを変更・自動stampした"
    assert error is not None, "未管理・未知revision DBを通常upgradeで受理した"
    if isinstance(error, SystemExit):
        assert error.code not in (None, 0)
    reason = (str(error) + captured.out + captured.err + caplog.text).lower()
    if variant == "unknown_revision":
        assert unknown_revision in reason
        assert "revision" in reason or "リビジョン" in reason
    else:
        assert "unmanaged" in reason or "未管理" in reason
        assert any(
            word in reason for word in ("table", "schema", "テーブル", "スキーマ")
        )
