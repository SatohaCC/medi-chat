"""索引構築と読取の独立性、再構築、失敗時の既存データ維持を検証する。"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Iterator
from pathlib import Path

import pytest
from backend.application.indexing.index_errors import IndexSourceError
from backend.application.indexing.index_models import IndexBuildResult, SourceSnapshot
from backend.domain.attachment.value_objects import AttachmentProductMatch
from backend.domain.retrieval.primitives import (
    DetectionSource,
    SearchKeyword,
    SearchSectionCode,
)
from backend.domain.retrieval.value_objects import Evidence, SearchCriteria
from backend.infrastructure.persistence import schema
from backend.infrastructure.persistence.evidence_reader import SqlAlchemyEvidenceReader
from backend.infrastructure.persistence.index_reader import SqlAlchemyIndexReader
from backend.infrastructure.persistence.index_writer import SqlAlchemyIndexWriter
from backend.infrastructure.persistence.medicine_reader import SqlAlchemyMedicineReader
from backend.infrastructure.persistence.sqlite_engine import create_sqlite_engine
from backend.infrastructure.sources.file_index_source import FileIndexSourceReader
from backend.tests.storage_fixtures import write_structured_document
from backend.tests.test_alembic_migrations import (
    _migrate_database,
    _snapshot_existing_database,
    _snapshot_managed_index,
)
from backend.tests.test_persistence_boundaries import source_snapshot as source_snapshot
from sqlalchemy import func, insert, select, text
from sqlalchemy.engine import URL, Engine


@pytest.fixture
def migrated_index(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[tuple[Path, Engine]]:
    for key in (
        "MEDI_CHAT_STRUCTURED_DIR",
        "MEDI_CHAT_INDEX_PATH",
        "MEDI_CHAT_DATABASE_URL",
    ):
        monkeypatch.delenv(key, raising=False)
    structured = write_structured_document(tmp_path)
    index_path = tmp_path / "index.sqlite3"
    _migrate_database(index_path, structured)
    engine = create_sqlite_engine(
        URL.create("sqlite", database=index_path.as_posix()).render_as_string(
            hide_password=False
        )
    )
    try:
        yield structured, engine
    finally:
        engine.dispose()


def _revision(engine: Engine) -> tuple[str, ...]:
    with engine.connect() as connection:
        return tuple(
            connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalars()
        )


def _fingerprint(engine: Engine) -> str:
    with engine.connect() as connection:
        return connection.execute(
            select(schema.index_meta.c.value).where(
                schema.index_meta.c.key == "source_fingerprint"
            )
        ).scalar_one()


def _document(engine: Engine, key: str) -> object:
    with engine.connect() as connection:
        payload = connection.execute(
            select(schema.documents.c.payload_json).where(
                schema.documents.c.document_key == key
            )
        ).scalar_one_or_none()
    return json.loads(payload) if payload is not None else None


def _insert_sentinel(engine: Engine) -> None:
    with engine.begin() as connection:
        connection.execute(
            insert(schema.documents),
            {"document_key": "sentinel", "payload_json": '{"unchanged": true}'},
        )


@pytest.mark.parametrize("observation", ["statistics", "document"])
def test_構築済み索引は元データなしで検索できる(
    tmp_path: Path, migrated_index: tuple[Path, Engine], observation: str
) -> None:
    structured, engine = migrated_index
    snapshot = FileIndexSourceReader(structured).read_snapshot()
    assert SqlAlchemyIndexWriter(engine).replace(snapshot) == IndexBuildResult(1, 3)
    assert structured.resolve().is_relative_to(tmp_path.resolve())
    destination = (tmp_path / "unused-sources").resolve()
    assert destination.is_relative_to(tmp_path.resolve())
    structured.rename(destination)
    assert not structured.exists()
    indexed_medicines = asyncio.run(SqlAlchemyMedicineReader(engine).read_medicines())
    assert indexed_medicines[0].yj_code is not None
    assert indexed_medicines[0].yj_code.value == "1234567A0000"
    medicines = (
        AttachmentProductMatch(
            generic_name="テスト成分",
            brand_names=["テスト薬"],
            yj_codes=["1234567A0000"],
            document_ids=["test_001"],
        ),
    )
    evidence_reader = SqlAlchemyEvidenceReader(engine)
    units = asyncio.run(
        evidence_reader.search(
            SearchCriteria(
                source=DetectionSource("logic"),
                section_codes=(SearchSectionCode("11.1"),),
            ),
            medicines,
        )
    )
    assert [item.unit_id.value for item in units] == [
        "test_001:000",
        "test_001:001",
        "test_001:002",
    ]
    assert (
        len(
            asyncio.run(
                evidence_reader.search(
                    SearchCriteria(
                        source=DetectionSource("keyword"),
                        keywords=(SearchKeyword("頭痛"),),
                    ),
                    medicines,
                )
            )
        )
        == 3
    )
    index_reader = SqlAlchemyIndexReader(engine)
    if observation == "statistics":
        assert asyncio.run(index_reader.read_index_stats()) == {
            "document_count": 1,
            "unit_count": 3,
        }
    else:
        document = asyncio.run(index_reader.get_document("test_001"))
        assert document is not None
        assert document == snapshot.documents[0].payload


def test_ソースが変わったときだけ索引を再構築する(
    migrated_index: tuple[Path, Engine],
) -> None:
    structured, engine = migrated_index
    revision = _revision(engine)
    assert len(revision) == 1
    source_reader = FileIndexSourceReader(structured)
    writer = SqlAlchemyIndexWriter(engine)
    initial = source_reader.read_snapshot()
    assert type(initial) is SourceSnapshot
    assert writer.replace(initial) == IndexBuildResult(1, 3)
    assert _fingerprint(engine) == initial.fingerprint
    assert _revision(engine) == revision
    _insert_sentinel(engine)
    before_unchanged = _snapshot_managed_index(Path(engine.url.database or ""))
    unchanged = source_reader.read_snapshot()
    assert unchanged.fingerprint == initial.fingerprint
    assert writer.replace(unchanged) == IndexBuildResult(2, 3)
    assert _document(engine, "sentinel") == {"unchanged": True}
    assert _snapshot_managed_index(Path(engine.url.database or "")) == before_unchanged
    assert _fingerprint(engine) == initial.fingerprint
    assert _revision(engine) == revision
    units = structured / "test_001/search_units.jsonl"
    new_unit = {
        "unit_id": "added",
        "document_key": "test_001",
        "section": {"code": "11.1"},
        "text": "新しく追加された頭痛の記載",
    }
    with units.open("a", encoding="utf-8") as stream:
        stream.write("\n" + json.dumps(new_unit, ensure_ascii=False))
    changed = source_reader.read_snapshot()
    assert changed.fingerprint != initial.fingerprint
    assert writer.replace(changed) == IndexBuildResult(1, 4)
    assert _document(engine, "sentinel") is None
    with engine.connect() as connection:
        assert (
            connection.execute(
                select(func.count()).select_from(schema.units)
            ).scalar_one()
            == 4
        )
        assert (
            connection.execute(text("SELECT COUNT(*) FROM unit_fts")).scalar_one() == 4
        )
    evidence = asyncio.run(
        SqlAlchemyEvidenceReader(engine).search(
            SearchCriteria(
                source=DetectionSource("keyword"),
                keywords=(SearchKeyword("新しく追加"),),
            ),
            (
                AttachmentProductMatch(
                    generic_name="テスト成分",
                    brand_names=["テスト薬"],
                    yj_codes=["1234567A0000"],
                    document_ids=["test_001"],
                ),
            ),
        )
    )
    assert {item.unit_id.value for item in evidence} == {"added"}
    assert _fingerprint(engine) == changed.fingerprint
    assert _revision(engine) == revision


def test_同fingerprintのCore更新は既存索引を保持する(
    migrated_index: tuple[Path, Engine], source_snapshot: SourceSnapshot
) -> None:
    _, engine = migrated_index
    revision = _revision(engine)
    writer = SqlAlchemyIndexWriter(engine)
    assert writer.replace(source_snapshot) == IndexBuildResult(1, 1)
    _insert_sentinel(engine)
    before_unchanged = _snapshot_managed_index(Path(engine.url.database or ""))
    # 実snapshotを直接渡し、File readerの失敗と独立してwriterの更新判断を観測する。
    result = writer.replace(source_snapshot)
    assert _document(engine, "sentinel") == {"unchanged": True}
    assert _snapshot_managed_index(Path(engine.url.database or "")) == before_unchanged
    assert result == IndexBuildResult(2, 1)
    assert _fingerprint(engine) == source_snapshot.fingerprint
    assert _revision(engine) == revision


@pytest.mark.parametrize(
    "failure", ["empty", "missing_units", "invalid_document", "invalid_jsonl"]
)
def test_構築に失敗しても既存索引が失われない(
    tmp_path: Path, migrated_index: tuple[Path, Engine], failure: str
) -> None:
    structured, engine = migrated_index
    writer = SqlAlchemyIndexWriter(engine)
    initial = FileIndexSourceReader(structured).read_snapshot()
    assert writer.replace(initial) == IndexBuildResult(1, 3)
    index_path = Path(engine.url.database or "")
    expected = _snapshot_existing_database(index_path)
    assert len(expected.rows["documents"]) == 1
    assert len(expected.rows["medicines"]) == 1
    assert len(expected.rows["units"]) == len(expected.rows["unit_fts"]) == 3
    assert expected.revision is not None and len(expected.revision) == 1
    expected_fingerprint = _fingerprint(engine)
    medicines = (
        AttachmentProductMatch(
            generic_name="テスト成分",
            brand_names=["テスト薬"],
            yj_codes=["1234567A0000"],
            document_ids=["test_001"],
        ),
    )
    criteria = (
        SearchCriteria(
            source=DetectionSource("logic"), section_codes=(SearchSectionCode("11.1"),)
        ),
        SearchCriteria(
            source=DetectionSource("keyword"), keywords=(SearchKeyword("頭痛"),)
        ),
        SearchCriteria(
            source=DetectionSource("keyword"), keywords=(SearchKeyword("注意して"),)
        ),
    )

    def read_results(reader_engine: Engine) -> tuple[tuple[Evidence, ...], ...]:
        reader = SqlAlchemyEvidenceReader(reader_engine)
        return tuple(
            asyncio.run(reader.search(condition, medicines)) for condition in criteria
        )

    before_search = read_results(engine)
    assert all(
        [item.unit_id.value for item in result]
        == ["test_001:000", "test_001:001", "test_001:002"]
        for result in before_search
    )
    if failure == "empty":
        structured = tmp_path / "empty"
        structured.mkdir()
    elif failure == "missing_units":
        target = (structured / "test_001/search_units.jsonl").resolve()
        assert target.is_relative_to(tmp_path.resolve())
        target.unlink()
    elif failure == "invalid_document":
        (structured / "test_001/document.json").write_text("not json", encoding="utf-8")
    else:
        (structured / "test_001/search_units.jsonl").write_text(
            "not jsonl", encoding="utf-8"
        )
    error: Exception | None = None
    try:
        writer.replace(FileIndexSourceReader(structured).read_snapshot())
    except ImportError, NotImplementedError:
        raise
    except Exception as caught:
        # この入力に対する生のfile/JSON例外はエラー変換不足としてassertで判別する。
        error = caught
    actual = _snapshot_existing_database(index_path)  # 独立した実SQLite接続
    separate_engine = create_sqlite_engine(
        engine.url.render_as_string(hide_password=False)
    )
    try:
        after_search = read_results(separate_engine)
    finally:
        separate_engine.dispose()
    assert isinstance(error, IndexSourceError), f"意味例外が必要: {error!r}"
    reason = str(error).lower()
    assert reason.strip(), "索引元の不足・破損理由が必要"
    if failure == "empty":
        assert any(
            word in reason
            for word in ("empty", "no structured", "no document", "no source", "空")
        )
    elif failure == "missing_units":
        assert "search_units.jsonl" in reason
        assert any(
            word in reason
            for word in ("missing", "not found", "no such", "欠落", "存在")
        )
    else:
        filename = (
            "document.json" if failure == "invalid_document" else "search_units.jsonl"
        )
        assert filename in reason
        assert any(word in reason for word in ("invalid", "json", "不正", "破損"))
    assert actual == expected
    assert after_search == before_search
    assert _fingerprint(engine) == expected_fingerprint
    assert _revision(engine) == expected.revision
