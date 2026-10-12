"""実SQLiteの接続設定とCore readerの検索互換性を検証する。"""

from __future__ import annotations

import asyncio
import json
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest
from backend.domain.attachment.value_objects import AttachmentProductMatch
from backend.domain.retrieval.primitives import DetectionSource, SearchKeyword
from backend.domain.retrieval.value_objects import Evidence, SearchCriteria
from backend.infrastructure.persistence.evidence_reader import SqlAlchemyEvidenceReader
from backend.infrastructure.persistence.sqlite_engine import create_sqlite_engine
from backend.tests.storage_fixtures import (
    build_document_store,
    write_structured_document,
)
from backend.tests.test_alembic_migrations import _migrate_database
from sqlalchemy import event
from sqlalchemy.engine import URL, Connection, Engine, ExecutionContext


def _driver_connection(connection: Connection) -> sqlite3.Connection:
    driver = connection.connection.driver_connection
    assert isinstance(driver, sqlite3.Connection), "実SQLiteのDBAPI接続が必要"
    return driver


def _assert_connection_settings(driver: sqlite3.Connection) -> None:
    # SQLAlchemyのbegin状態を変えず、実DBAPI cursorで接続ごとの設定を読む。
    with closing(driver.cursor()) as cursor:
        collations = {row[1] for row in cursor.execute("PRAGMA collation_list")}
        pragmas = {
            name: cursor.execute(f"PRAGMA {name}").fetchone()[0]
            for name in ("busy_timeout", "journal_mode", "synchronous", "cache_size")
        }
        # 未登録collationをSQLへ渡してOperationalErrorを起こす前にassertする。
        assert "section_code_order" in collations, (
            f"章順collationが未登録: {collations}; PRAGMA={pragmas}"
        )
        assert pragmas == {
            "busy_timeout": 30000,
            "journal_mode": "wal",
            "synchronous": 1,  # SQLite NORMAL
            "cache_size": -64000,
        }
        assert cursor.execute(
            "WITH codes(code) AS (VALUES ('10'), ('2'), ('1'), ('11.10'), ('11.2')) "
            "SELECT code FROM codes ORDER BY code COLLATE section_code_order"
        ).fetchall() == [("1",), ("2",), ("10",), ("11.2",), ("11.10",)]


@pytest.mark.parametrize("connection_path", ["pool_and_reconnect", "alembic"])
def test_connection_settings_apply_to_every_connection(
    tmp_path: Path,
    connection_path: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for key in (
        "MEDI_CHAT_STRUCTURED_DIR",
        "MEDI_CHAT_INDEX_PATH",
        "MEDI_CHAT_DATABASE_URL",
    ):
        monkeypatch.delenv(key, raising=False)
    index_path = tmp_path / f"{connection_path}.sqlite3"
    if connection_path == "pool_and_reconnect":
        database_url = URL.create(
            "sqlite", database=index_path.as_posix()
        ).render_as_string(hide_password=False)
        engine = create_sqlite_engine(database_url)
        try:
            # 同時に保持することで、異なるpool checkoutだけでなく物理接続の違いを証明する。
            with engine.connect() as first, engine.connect() as second:
                first_driver = _driver_connection(first)
                second_driver = _driver_connection(second)
                assert first_driver is not second_driver
                _assert_connection_settings(first_driver)
                _assert_connection_settings(second_driver)
            engine.dispose()
            with engine.connect() as reconnected:
                reconnected_driver = _driver_connection(reconnected)
                assert reconnected_driver is not first_driver
                assert reconnected_driver is not second_driver
                _assert_connection_settings(reconnected_driver)
        finally:
            engine.dispose()
    else:
        source = tmp_path / "structured"
        source.mkdir()
        captured: list[sqlite3.Connection] = []

        def observe_migration_connection(
            connection: Connection,
            cursor: object,
            statement: str,
            parameters: object,
            context: ExecutionContext,
            executemany: bool,
        ) -> None:
            if Path(connection.engine.url.database or "").resolve() != index_path:
                return
            driver = _driver_connection(connection)
            if not any(previous is driver for previous in captured):
                captured.append(driver)
                _assert_connection_settings(driver)

        event.listen(Engine, "before_cursor_execute", observe_migration_connection)
        try:
            # actual env.py/runnerの最初のSQLに使う物理接続を観測する。
            _migrate_database(index_path, source)
        finally:
            event.remove(Engine, "before_cursor_execute", observe_migration_connection)
        assert captured, "実Alembicが対象DBで使った接続を観測できない"


@pytest.mark.parametrize(
    ("keyword", "expected_ids"),
    [
        ("頭痛", ("test_001:000", "test_001:001", "test_001:002")),
        ("腹痛", ()),
    ],
    ids=["two_character_match", "two_character_no_match"],
)
def test_two_character_search_matches_legacy_instr(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    keyword: str,
    expected_ids: tuple[str, ...],
) -> None:
    for key in (
        "MEDI_CHAT_STRUCTURED_DIR",
        "MEDI_CHAT_INDEX_PATH",
        "MEDI_CHAT_DATABASE_URL",
    ):
        monkeypatch.delenv(key, raising=False)
    source = write_structured_document(tmp_path)
    index_path = tmp_path / "two_character.sqlite3"
    _migrate_database(index_path, source)
    build_document_store(source, index_path)
    # 2文字の旧instr経路を独立した比較基準にする。旧SQLにはORDER BYがない。
    # 固定期待も残し、最終章順sortを候補readerへ要求しない。
    legacy_units = baseline_query_units(index_path, keyword)
    legacy_ids = tuple(unit["unit_id"] for unit in legacy_units)
    assert legacy_ids == expected_ids
    medicines = (
        AttachmentProductMatch(
            generic_name="テスト成分",
            brand_names=("テスト薬",),
            yj_codes=("1234567A0000",),
            document_ids=("test_001",),
        ),
    )
    criteria = SearchCriteria(
        source=DetectionSource("keyword"), keywords=(SearchKeyword(keyword),)
    )
    database_url = URL.create(
        "sqlite", database=index_path.as_posix()
    ).render_as_string(hide_password=False)
    engine = create_sqlite_engine(database_url)
    try:
        evidence = asyncio.run(
            SqlAlchemyEvidenceReader(engine).search(criteria, medicines)
        )
        assert isinstance(evidence, tuple)
        assert all(type(item) is Evidence for item in evidence)
        actual_ids = tuple(item.unit_id.value for item in evidence)
        assert set(actual_ids) == set(expected_ids)
        assert actual_ids == legacy_ids
    finally:
        engine.dispose()


@pytest.mark.parametrize(
    ("keyword", "expected_ids"),
    [
        (
            "注意",
            (
                "test_001:z_tie",
                "test_001:best",
                "test_001:a_tie",
                "test_001:long",
                "test_001:metadata_only",
            ),
        ),
        (
            "注意事",
            ("test_001:best", "test_001:z_tie", "test_001:a_tie", "test_001:long"),
        ),
        (
            "注意事項",
            ("test_001:best", "test_001:z_tie", "test_001:a_tie", "test_001:long"),
        ),
    ],
    ids=["two_character_boundary", "three_character_fts", "longer_fts"],
)
def test_trigram_search_and_tie_break_match_baseline(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    keyword: str,
    expected_ids: tuple[str, ...],
) -> None:
    for key in (
        "MEDI_CHAT_STRUCTURED_DIR",
        "MEDI_CHAT_INDEX_PATH",
        "MEDI_CHAT_DATABASE_URL",
    ):
        monkeypatch.delenv(key, raising=False)
    source = write_structured_document(tmp_path)
    # 同順位のIDは辞書順と逆に配置する。metadata_onlyはpayload中だけの語で、
    # instrからquery_textのFTSへの2→3文字境界を結果集合でも区別できる。
    units = [
        {
            "unit_id": f"test_001:{suffix}",
            "document_key": "test_001",
            "product_yj_codes": ["1234567A0000"],
            "section": {"code": "11.1", "title": "副作用"},
            "kind": "text",
            "text": text,
            "raw_metadata": {"note": "注意事項"},
        }
        for suffix, text in (
            ("z_tie", "注意事項"),
            ("best", "注意事項注意事項注意事項"),
            ("a_tie", "注意事項"),
            ("long", "注意事項。" + "関係のない長い説明です。" * 10),
            ("metadata_only", "別の記載"),
        )
    ]
    (source / "test_001" / "search_units.jsonl").write_text(
        "\n".join(json.dumps(unit, ensure_ascii=False) for unit in units),
        encoding="utf-8",
    )
    index_path = tmp_path / "trigram.sqlite3"
    _migrate_database(index_path, source)
    build_document_store(source, index_path)
    legacy_ids = tuple(
        unit["unit_id"] for unit in baseline_query_units(index_path, keyword)
    )
    assert legacy_ids == expected_ids
    if len(keyword) >= 3:
        with closing(sqlite3.connect(index_path)) as connection:
            ddl = connection.execute(
                "SELECT sql FROM sqlite_master WHERE name='unit_fts'"
            ).fetchone()[0]
            assert "trigram" in ddl.lower()
            ranks = connection.execute(
                "SELECT unit_id, bm25(unit_fts) FROM unit_fts "
                "WHERE unit_fts MATCH ? AND document_key=? ORDER BY bm25(unit_fts)",
                (f'query_text : "{keyword}"', "test_001"),
            ).fetchall()
        assert tuple(unit_id for unit_id, _ in ranks) == expected_ids
        assert ranks[0][1] < ranks[1][1] == ranks[2][1] < ranks[3][1]
        # 旧実行のID順と実bm25値をrunnerのcaptured stdoutへ保存する。
        print(
            json.dumps({"keyword": keyword, "legacy_ranks": ranks}, ensure_ascii=False)
        )
    medicines = (
        AttachmentProductMatch(
            generic_name="テスト成分",
            brand_names=("テスト薬",),
            yj_codes=("1234567A0000",),
            document_ids=("test_001",),
        ),
    )
    engine = create_sqlite_engine(
        URL.create("sqlite", database=index_path.as_posix()).render_as_string(
            hide_password=False
        )
    )
    try:
        evidence = asyncio.run(
            SqlAlchemyEvidenceReader(engine).search(
                SearchCriteria(
                    source=DetectionSource("keyword"),
                    keywords=(SearchKeyword(keyword),),
                ),
                medicines,
            )
        )
        assert isinstance(evidence, tuple)
        assert all(type(item) is Evidence for item in evidence)
        assert (
            tuple(item.unit_id.value for item in evidence) == expected_ids == legacy_ids
        )
    finally:
        engine.dispose()


def baseline_query_units(index_path: Path, keyword: str):
    """固定された旧2文字instr/3文字trigram SQLを独立比較する。"""
    with closing(sqlite3.connect(index_path)) as connection:
        if len(keyword) < 3:
            rows = connection.execute(
                "SELECT payload_json FROM units WHERE instr(payload_json, ?) > 0 AND document_key=?",
                (keyword, "test_001"),
            ).fetchall()
        else:
            rows = connection.execute(
                "SELECT units.payload_json FROM unit_fts JOIN units USING(unit_id) WHERE unit_fts MATCH ? AND unit_fts.document_key=? ORDER BY bm25(unit_fts)",
                (f'query_text : "{keyword}"', "test_001"),
            ).fetchall()
    return [json.loads(row[0]) for row in rows]
