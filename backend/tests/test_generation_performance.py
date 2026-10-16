"""Connection ownership, projection reuse, and unchanged generation semantics."""

import asyncio
import sqlite3
import sqlite3.dbapi2 as sqlite_dbapi
import threading
import time

import pytest
from backend.application.medicine.product_models import ResolvedMedicine
from backend.domain.medicine.value_objects import MedicineMatch as DomainMedicineMatch
from backend.domain.retrieval.primitives import (
    DetectionSource,
    SearchKeyword,
    SearchSectionCode,
)
from backend.domain.retrieval.value_objects import SearchCriteria
from backend.infrastructure.persistence.generation_runtime import (
    GenerationRuntime,
    _SnapshotReader,
)
from backend.infrastructure.persistence.read_workers import ReadWorkers
from backend.infrastructure.persistence.registration_publisher import (
    SqliteRegistrationPublisher,
)
from backend.infrastructure.persistence.sqlite_engine import create_sqlite_engine
from backend.tests.test_registration_publisher import publish, source
from backend.tests.test_registration_publisher import publisher as publisher
from sqlalchemy import event


def target(code="111111111111"):
    return (
        ResolvedMedicine(
            medicine=DomainMedicineMatch("", (), (code,), ()),
            document_ids=("000001_test",),
        ),
    )


@pytest.mark.asyncio
async def test_warmup_is_readonly_and_refreshes_after_publication(
    publisher, monkeypatch
):
    first = publish(publisher, source("旧世代本文"))
    workers = ReadWorkers()
    runtime = GenerationRuntime(publisher, workers=workers)
    statements = []
    original = sqlite3.connect

    def traced_connect(*args, **kwargs):
        connection = original(*args, **kwargs)
        connection.set_trace_callback(statements.append)
        return connection

    monkeypatch.setattr(sqlite3, "connect", traced_connect)
    monkeypatch.setattr(sqlite_dbapi, "connect", traced_connect)
    try:
        await runtime.warmup()
        cached = runtime.cached_generation_id
        assert cached is not None and cached.value == first.generation_id
        assert not any(
            sql.lstrip().split()[0].upper()
            in {"INSERT", "UPDATE", "DELETE", "CREATE", "DROP", "ALTER", "REPLACE"}
            for sql in statements
        )
        updated = await workers.run(
            lambda: publish(publisher, source("新世代本文", revised_at="2026-11"))
        )
        await runtime.warmup()
        cached = runtime.cached_generation_id
        assert cached is not None and cached.value == updated.generation_id
        async with runtime.acquire() as snapshot:
            evidence = await snapshot.evidence_reader.search(
                SearchCriteria(
                    source=DetectionSource.LOGIC,
                    section_codes=(SearchSectionCode("1"),),
                ),
                target(),
            )
            assert len(evidence) == 1 and "新世代本文" in evidence[0].excerpt
    finally:
        await workers.aclose()


@pytest.mark.asyncio
async def test_cancellation_waits_for_search_close_without_blocking_loop(
    publisher, monkeypatch
):
    publish(publisher, source("検索中の本文"))
    workers = ReadWorkers(max_workers=2)
    runtime = GenerationRuntime(publisher, workers=workers)
    started = threading.Event()
    finish = threading.Event()
    original = _SnapshotReader._build_fts

    def blocked_build(connection, rows):
        started.set()
        assert finish.wait(5)
        original(connection, rows)

    monkeypatch.setattr(_SnapshotReader, "_build_fts", staticmethod(blocked_build))

    async def request():
        async with runtime.acquire() as snapshot:
            await snapshot.evidence_reader.search(
                SearchCriteria(
                    source=DetectionSource.KEYWORD, keywords=(SearchKeyword("検索中"),)
                ),
                target(),
            )

    task = asyncio.create_task(request())
    timer = threading.Timer(3, finish.set)
    timer.start()
    try:
        assert await asyncio.to_thread(started.wait, 2)
        before = time.monotonic()
        task.cancel()
        await asyncio.sleep(0.05)
        assert time.monotonic() - before < 1
        assert not task.done()
        finish.set()
        with pytest.raises(asyncio.CancelledError):
            await task
        with sqlite3.connect(publisher.index_path) as connection:
            assert connection.execute(
                "SELECT COUNT(*) FROM generation_leases"
            ).fetchone() == (0,)
    finally:
        finish.set()
        timer.cancel()
        await workers.aclose()


@pytest.mark.asyncio
async def test_injected_pool_survives_reads_publication_and_recovery(publisher):
    publish(publisher, source("初回本文"))
    engine = create_sqlite_engine("sqlite:///" + publisher.index_path.as_posix())
    connections = []
    disposed = []
    event.listen(
        engine, "connect", lambda connection, _: connections.append(connection)
    )
    event.listen(engine, "engine_disposed", lambda _: disposed.append(True))
    shared = SqliteRegistrationPublisher(
        publisher.index_path, publisher.store, engine=engine
    )
    workers = ReadWorkers()
    runtime = GenerationRuntime(shared, workers=workers)
    try:
        await runtime.warmup()
        for _ in range(2):
            async with runtime.acquire() as snapshot:
                assert await snapshot.medicine_reader.read_medicines()
        updated = await workers.run(
            lambda: publish(shared, source("更新本文", revised_at="2026-11"))
        )
        await workers.run(
            lambda: shared.read_result(updated.document_id, updated.source_sha256)
        )
        await workers.run(shared.recover)
        assert len(connections) == 1
        assert disposed == []
        with engine.connect() as connection:
            assert (
                connection.exec_driver_sql(
                    "SELECT COUNT(*) FROM generation_leases"
                ).scalar()
                == 0
            )
    finally:
        await workers.aclose()
        engine.dispose()
    assert disposed == [True]


@pytest.mark.asyncio
async def test_keyword_index_reused_and_closed_with_snapshot(publisher, monkeypatch):
    publish(publisher, source("共通本文を検索", ("111111111111", "222222222222")))
    workers = ReadWorkers()
    runtime = GenerationRuntime(publisher, workers=workers)
    connections = []
    statements = []
    original = sqlite3.connect

    def traced_connect(database, *args, **kwargs):
        connection = original(database, *args, **kwargs)
        if database == ":memory:":
            connections.append(connection)
            connection.set_trace_callback(statements.append)
        return connection

    monkeypatch.setattr(sqlite3, "connect", traced_connect)
    criteria = SearchCriteria(
        source=DetectionSource.KEYWORD, keywords=(SearchKeyword("共通本文"),)
    )
    try:
        async with runtime.acquire() as snapshot:
            section = await snapshot.evidence_reader.search(
                SearchCriteria(
                    source=DetectionSource.LOGIC,
                    section_codes=(SearchSectionCode("1"),),
                ),
                target(),
            )
            assert section and connections == []
            results = await asyncio.gather(
                *(snapshot.evidence_reader.search(criteria, target()) for _ in range(3))
            )
            assert all(result == results[0] for result in results)
            assert results[0] and results[0][0].retrieved_by == frozenset(
                {DetectionSource.KEYWORD}
            )
            assert len(connections) == 1
            assert (
                sum(sql.startswith("CREATE VIRTUAL TABLE") for sql in statements) == 1
            )
            other = await snapshot.evidence_reader.search(
                criteria, target("222222222222")
            )
            assert other[0].product_yj_codes[0].value == "222222222222"
            assert len(connections) == 2
            shorter = await snapshot.evidence_reader.search(
                SearchCriteria(
                    source=DetectionSource.JEV, keywords=(SearchKeyword("共通"),)
                ),
                target(),
            )
            assert shorter and shorter[0].retrieved_by == frozenset(
                {DetectionSource.JEV}
            )
        for connection in connections:
            with pytest.raises(sqlite3.ProgrammingError, match="closed"):
                connection.execute("SELECT 1")
        with pytest.raises(RuntimeError, match="released"):
            await snapshot.evidence_reader.search(criteria, target())
    finally:
        await workers.aclose()
