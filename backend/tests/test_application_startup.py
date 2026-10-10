"""明示migration/build済み索引だけを読取りで起動する契約。"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import httpx
import pytest
from backend.infrastructure.persistence.index_writer import SqlAlchemyIndexWriter
from backend.infrastructure.sources.file_index_source import FileIndexSourceReader
from backend.main import create_app
from backend.tests.test_alembic_migrations import _snapshot_existing_database
from backend.tests.test_package_insert_index import migrated_index as migrated_index
from sqlalchemy.engine import Engine


@pytest.mark.asyncio
async def test_prepared_index_starts_without_mutation(
    migrated_index: tuple[Path, Engine],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source, engine = migrated_index
    SqlAlchemyIndexWriter(engine).replace(FileIndexSourceReader(source).read_snapshot())
    assert engine.url.database is not None
    index_path = Path(engine.url.database)
    before = _snapshot_existing_database(index_path)
    statements: list[str] = []
    original = sqlite3.connect

    def trace_connect(*args, **kwargs):
        connection = original(*args, **kwargs)
        connection.set_trace_callback(statements.append)
        return connection

    monkeypatch.setattr(sqlite3, "connect", trace_connect)
    dbapi2 = getattr(sqlite3, "dbapi2", None)
    if dbapi2 is not None:
        monkeypatch.setattr(dbapi2, "connect", trace_connect)
    app = create_app(source, index_path)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api")
        assert response.status_code == 200 and response.json() == {"status": "ok"}
    assert _snapshot_existing_database(index_path) == before
    mutation = [
        statement
        for statement in statements
        if statement.lstrip().split()[0].upper()
        in {
            "CREATE",
            "DROP",
            "ALTER",
            "INSERT",
            "UPDATE",
            "DELETE",
            "REPLACE",
        }
    ]
    assert mutation == [], f"startup executed mutating SQL: {mutation}"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("condition", "setup_mode"),
    [
        ("missing_db", "missing_db"),
        ("unmanaged", "unmanaged"),
        ("old_revision", "old_revision"),
        ("missing_table", "missing_table"),
        ("unbuilt_empty", "unbuilt_empty"),
    ],
)
async def test_unprepared_index_is_rejected(
    condition: str,
    setup_mode: str,
    tmp_path: Path,
    migrated_index: tuple[Path, Engine],
) -> None:
    source, engine = migrated_index
    index_path = tmp_path / f"{condition}.sqlite3"

    expected_msg_parts: list[str] = []
    if setup_mode == "missing_db":
        assert not index_path.exists()
        expected_msg_parts = ["alembic upgrade head", "build_search_index"]
    elif setup_mode == "unmanaged":
        with sqlite3.connect(index_path) as conn:
            conn.execute("CREATE TABLE legacy_sample (id INTEGER PRIMARY KEY)")
        expected_msg_parts = ["unmanaged", "alembic upgrade head"]
    elif setup_mode == "old_revision":
        with sqlite3.connect(index_path) as conn:
            conn.execute(
                "CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)"
            )
            conn.execute("INSERT INTO alembic_version VALUES ('0000_old_revision')")
        expected_msg_parts = ["revision", "alembic upgrade head"]
    elif setup_mode == "missing_table":
        with sqlite3.connect(index_path) as conn:
            conn.execute(
                "CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)"
            )
            conn.execute("INSERT INTO alembic_version VALUES ('0001_v3_schema')")
            conn.execute(
                "CREATE TABLE documents (document_key TEXT PRIMARY KEY, payload_json TEXT)"
            )
        expected_msg_parts = ["missing required tables", "alembic upgrade head"]
    elif setup_mode == "unbuilt_empty":
        assert engine.url.database is not None
        index_path = Path(engine.url.database)
        expected_msg_parts = ["unbuilt", "build_search_index"]
    else:
        pytest.fail(f"Unknown setup_mode: {setup_mode}")

    before_exists = index_path.exists()
    before_snapshot = _snapshot_existing_database(index_path) if before_exists else None

    app = create_app(source, index_path)
    with pytest.raises(RuntimeError) as exc_info:
        async with app.router.lifespan_context(app):
            pass

    for part in expected_msg_parts:
        assert part in str(exc_info.value), (
            f"Expected {part!r} in error message: {exc_info.value}"
        )

    if before_exists:
        assert _snapshot_existing_database(index_path) == before_snapshot
    else:
        assert not index_path.exists()


@pytest.mark.asyncio
async def test_stale_index_requires_explicit_rebuild(
    migrated_index: tuple[Path, Engine],
) -> None:
    source, engine = migrated_index
    writer = SqlAlchemyIndexWriter(engine)
    writer.replace(FileIndexSourceReader(source).read_snapshot())
    assert engine.url.database is not None
    index_path = Path(engine.url.database)
    before_snapshot = _snapshot_existing_database(index_path)

    # Modify source by adding a new structured document
    second_doc = source / "test_doc_002"
    second_doc.mkdir()
    (second_doc / "document.json").write_text(
        json.dumps(
            {
                "document": {
                    "company_identifier": "test2",
                    "package_insert_no": "002",
                    "generic_name": "テスト成分2",
                    "products": [
                        {"yj_code": "9876543A0000", "brand_name": "テスト薬2"}
                    ],
                },
                "source": {"pmda_url": "https://example.test/package-insert-2"},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (second_doc / "search_units.jsonl").write_text(
        json.dumps(
            {
                "unit_id": "test_002:000",
                "document_key": "test2_002",
                "section_code": "1",
                "kind": "heading",
                "query_text": "テスト薬2",
                "drug_name": "テスト薬2",
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    # Attempt to start with stale index -> must be rejected without mutating DB
    app = create_app(source, index_path)
    with pytest.raises(RuntimeError) as exc_info:
        async with app.router.lifespan_context(app):
            pass

    assert (
        "stale" in str(exc_info.value).lower()
        or "fingerprint" in str(exc_info.value).lower()
    )
    assert "build_search_index" in str(exc_info.value)
    assert _snapshot_existing_database(index_path) == before_snapshot

    # Explicitly rebuild index in stopped state
    build_result = writer.replace(FileIndexSourceReader(source).read_snapshot())
    assert build_result.document_count == 2

    # Now startup succeeds
    restarted_app = create_app(source, index_path)
    async with restarted_app.router.lifespan_context(restarted_app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=restarted_app),
            base_url="http://test",
        ) as client:
            response = await client.get("/api")
        assert response.status_code == 200 and response.json() == {"status": "ok"}
