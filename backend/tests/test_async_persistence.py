"""実DB検索停止中の同一event loop応答を検証する。"""

from __future__ import annotations

import asyncio
import json
import threading
from dataclasses import fields, is_dataclass
from pathlib import Path

import httpx
import pytest
from backend.application.indexing.index_models import IndexBuildResult
from backend.domain.attachment.value_objects import AttachmentProductMatch
from backend.domain.foundation.primitives.primitives import (
    BaseFiniteFloat,
    BaseString,
)
from backend.domain.retrieval.primitives import (
    DetectionSource,
    SearchKeyword,
    SearchSectionCode,
)
from backend.domain.retrieval.value_objects import SearchCriteria
from backend.infrastructure.composition.persistence_lifespan import (
    create_persistence_lifespan,
)
from backend.infrastructure.persistence.evidence_reader import SqlAlchemyEvidenceReader
from backend.infrastructure.persistence.index_reader import SqlAlchemyIndexReader
from backend.infrastructure.persistence.index_writer import SqlAlchemyIndexWriter
from backend.infrastructure.persistence.medicine_reader import SqlAlchemyMedicineReader
from backend.infrastructure.persistence.read_workers import ReadWorkers
from backend.infrastructure.sources.file_index_source import FileIndexSourceReader
from backend.presentation import chat_websocket_routes, health_routes
from backend.tests.test_package_insert_index import migrated_index as migrated_index
from fastapi import FastAPI
from sqlalchemy import event
from sqlalchemy.engine import Connection, Engine
from starlette.types import Message, Scope


@pytest.mark.asyncio
async def test_api_and_ws_respond_while_search_is_blocked(
    migrated_index: tuple[Path, Engine],
) -> None:
    source, engine = migrated_index
    assert SqlAlchemyIndexWriter(engine).replace(
        FileIndexSourceReader(source).read_snapshot()
    ) == IndexBuildResult(1, 3)
    app = FastAPI()
    app.include_router(health_routes.router)
    app.include_router(chat_websocket_routes.router)
    loop = asyncio.get_running_loop()
    sql_started = threading.Event()
    loop_started = asyncio.Event()
    probes_completed = threading.Event()
    release = threading.Event()
    watchdog_released = threading.Event()

    def stop_search(
        connection: Connection,
        cursor: object,
        statement: str,
        parameters: object,
        context: object,
        executemany: bool,
    ) -> None:
        if "FROM units" in statement and not sql_started.is_set():
            sql_started.set()
            loop.call_soon_threadsafe(loop_started.set)
            if not release.wait(20):
                raise AssertionError("DB search release guard expired")

    def watchdog() -> None:
        # timeoutは同期実装のdeadlockから解放するguard。応答SLAの期待値ではない。
        if sql_started.wait(20) and not probes_completed.wait(5):
            watchdog_released.set()
        release.set()

    event.listen(engine, "before_cursor_execute", stop_search)
    watcher = threading.Thread(target=watchdog, name="tc40-release-watchdog")
    watcher.start()
    incoming: asyncio.Queue[Message] = asyncio.Queue()
    outgoing: asyncio.Queue[Message] = asyncio.Queue()

    async def receive() -> Message:
        return await incoming.get()

    async def send(message: Message) -> None:
        await outgoing.put(message)

    scope: Scope = {
        "type": "websocket",
        "asgi": {"version": "3.0"},
        "scheme": "ws",
        "path": "/ws/chat",
        "raw_path": b"/ws/chat",
        "root_path": "",
        "query_string": b"",
        "headers": [],
        "client": ("test", 123),
        "server": ("test", 80),
        "subprotocols": [],
    }
    websocket_task: asyncio.Task[None] | None = None
    search_task = asyncio.create_task(
        SqlAlchemyEvidenceReader(engine).search(
            SearchCriteria(
                source=DetectionSource("logic"),
                section_codes=(SearchSectionCode("11.1"),),
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
    try:
        await asyncio.wait_for(loop_started.wait(), timeout=25)
        assert sql_started.is_set()
        websocket_task = asyncio.create_task(app(scope, receive, send))
        await incoming.put({"type": "websocket.connect"})
        assert (await asyncio.wait_for(outgoing.get(), timeout=10))[
            "type"
        ] == "websocket.accept"
        await incoming.put(
            {"type": "websocket.receive", "text": json.dumps({"type": "ping"})}
        )
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api")
        pong = await asyncio.wait_for(outgoing.get(), timeout=10)
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
        assert pong["type"] == "websocket.send"
        assert json.loads(pong["text"]) == {"type": "pong"}
        # 同一loopの両応答がDB解放より前に完了した順序だけを判定する。
        assert not release.is_set(), "health/pong completed only after DB was released"
        assert not search_task.done()
        assert not watchdog_released.is_set()
        probes_completed.set()
        release.set()
        result = await asyncio.wait_for(search_task, timeout=10)
        assert [item.unit_id.value for item in result] == [
            "test_001:000",
            "test_001:001",
            "test_001:002",
        ]
    finally:
        release.set()
        probes_completed.set()
        if websocket_task is not None:
            await incoming.put({"type": "websocket.disconnect", "code": 1000})
            await asyncio.wait_for(websocket_task, timeout=10)
        await asyncio.wait_for(search_task, timeout=10)
        await asyncio.to_thread(watcher.join, 25)
        assert not watcher.is_alive()
        event.remove(engine, "before_cursor_execute", stop_search)


def _build_index(source: Path, engine: Engine) -> None:
    assert SqlAlchemyIndexWriter(engine).replace(
        FileIndexSourceReader(source).read_snapshot()
    ) == IndexBuildResult(1, 3)


def _assert_plain(value: object) -> None:
    if is_dataclass(value) and not isinstance(value, type):
        assert type(value).__module__.startswith("backend.domain.")
        for field in fields(value):
            _assert_plain(getattr(value, field.name))
    elif isinstance(value, dict):
        assert type(value) is dict
        for key, item in value.items():
            assert type(key) is str
            _assert_plain(item)
    elif isinstance(value, (tuple, list, frozenset)):
        assert type(value) in (tuple, list, frozenset)
        for item in value:
            _assert_plain(item)
    else:
        if isinstance(
            value,
            (
                BaseFiniteFloat,
                BaseString,
                DetectionSource,
            ),
        ):
            return
        assert type(value) in (str, int, float, bool, type(None))


@pytest.mark.parametrize(
    "reader_kind", ["evidence", "medicine", "document", "statistics"]
)
@pytest.mark.asyncio
async def test_workers_own_connections_and_return_plain_values(
    migrated_index: tuple[Path, Engine],
    monkeypatch: pytest.MonkeyPatch,
    reader_kind: str,
) -> None:
    from backend.infrastructure.persistence import (
        evidence_reader,
        index_reader,
        medicine_reader,
    )

    source, engine = migrated_index
    _build_index(source, engine)
    loop_thread = threading.get_ident()
    barrier = threading.Barrier(2, timeout=10)
    acquired: dict[int, int] = {}
    sql_threads: list[int] = []
    conversion_threads: list[int] = []
    returned: dict[int, int] = {}
    original_parse = evidence_reader.parse_json_object

    def checkout(dbapi: object, record: object, proxy: object) -> None:
        acquired[id(dbapi)] = threading.get_ident()

    def checkin(dbapi: object, record: object) -> None:
        returned[id(dbapi)] = threading.get_ident()

    def stop(
        connection: Connection,
        cursor: object,
        statement: str,
        parameters: object,
        context: object,
        executemany: bool,
    ) -> None:
        assert threading.get_ident() != loop_thread, (
            "SQL must execute inside its worker"
        )
        sql_threads.append(threading.get_ident())
        if reader_kind != "statistics" or "FROM documents" in statement:
            barrier.wait()

    def parse(payload: str) -> dict:
        conversion_threads.append(threading.get_ident())
        return original_parse(payload)

    monkeypatch.setattr(evidence_reader, "parse_json_object", parse)
    monkeypatch.setattr(medicine_reader, "parse_json_object", parse)
    monkeypatch.setattr(index_reader, "parse_json_object", parse)
    listeners = [
        ("checkout", checkout),
        ("checkin", checkin),
        ("before_cursor_execute", stop),
    ]
    for name, listener in listeners:
        event.listen(engine, name, listener)
    try:
        if reader_kind == "evidence":
            reader = SqlAlchemyEvidenceReader(engine)
            matches, empty = await asyncio.gather(
                reader.search(
                    SearchCriteria(
                        source=DetectionSource("logic"),
                        keywords=(SearchKeyword("頭痛"),),
                    ),
                    (),
                ),
                reader.search(
                    SearchCriteria(
                        source=DetectionSource("keyword"),
                        keywords=(SearchKeyword("腹痛"),),
                    ),
                    (),
                ),
            )
            assert [item.unit_id.value for item in matches] == [
                "test_001:000",
                "test_001:001",
                "test_001:002",
            ]
            assert all(item.retrieved_by == frozenset({"logic"}) for item in matches)
            assert empty == ()
            results = (matches, empty)
        elif reader_kind == "medicine":
            results = await asyncio.gather(
                *[SqlAlchemyMedicineReader(engine).read_medicines() for _ in range(2)]
            )
            assert results[0] == results[1]
            assert results[0][0].yj_code is not None
            assert results[0][0].yj_code.value == "1234567A0000"
        elif reader_kind == "document":
            results = await asyncio.gather(
                SqlAlchemyIndexReader(engine).get_document("test_001"),
                SqlAlchemyIndexReader(engine).get_document("absent"),
            )
            assert results[0] is not None and results[1] is None
        else:
            results = await asyncio.gather(
                *[SqlAlchemyIndexReader(engine).read_index_stats() for _ in range(2)]
            )
            assert results == [
                {"document_count": 1, "unit_count": 3},
            ]
        _assert_plain(results)
        assert len(acquired) == 2
        assert acquired == returned
        assert len(set(acquired.values())) == 2
        assert loop_thread not in acquired.values()
        assert set(sql_threads) == set(acquired.values())
        if reader_kind != "statistics":
            assert conversion_threads and set(conversion_threads) <= set(
                acquired.values()
            )
    finally:
        barrier.abort()
        for name, listener in listeners:
            event.remove(engine, name, listener)


@pytest.mark.asyncio
async def test_concurrent_reads_preserve_cached_document_content(
    migrated_index: tuple[Path, Engine],
) -> None:
    source, engine = migrated_index
    _build_index(source, engine)
    barrier = threading.Barrier(3, timeout=10)

    def overlap(
        connection: Connection,
        cursor: object,
        statement: str,
        parameters: object,
        context: object,
        executemany: bool,
    ) -> None:
        barrier.wait()

    event.listen(engine, "before_cursor_execute", overlap)
    try:
        documents = await asyncio.gather(
            *[SqlAlchemyIndexReader(engine).get_document("test_001") for _ in range(3)]
        )
        evidence = await asyncio.gather(
            *[
                SqlAlchemyEvidenceReader(engine).search(
                    SearchCriteria(
                        source=DetectionSource(label), keywords=(SearchKeyword("頭痛"),)
                    ),
                    (),
                )
                for label in ("logic", "jev", "keyword")
            ]
        )
    finally:
        barrier.abort()
        event.remove(engine, "before_cursor_execute", overlap)
    expected = FileIndexSourceReader(source).read_snapshot().documents[0].payload
    assert documents == [expected, expected, expected]
    assert all(
        [item.unit_id.value for item in batch]
        == ["test_001:000", "test_001:001", "test_001:002"]
        for batch in evidence
    )
    for batch, label in zip(evidence, ("logic", "jev", "keyword"), strict=True):
        assert all(item.retrieved_by == frozenset({label}) for item in batch)
    first = documents[0]
    assert first is not None
    metadata = first["document"]
    assert isinstance(metadata, dict)
    metadata["generic_name"] = "request-local change"
    public_evidence = evidence[0][0].to_dict()
    public_section = public_evidence["section"]
    assert isinstance(public_section, dict)
    public_section["title"] = "request-local title"
    assert documents[1:] == [expected, expected]
    assert evidence[1][0].section["title"] == "重大な副作用"
    assert evidence[2][0].section["title"] == "重大な副作用"
    # 返却後に再読取しても他の利用者による変更が保存内容へ漏れない。
    assert await SqlAlchemyIndexReader(engine).get_document("test_001") == expected
    _assert_plain((documents, evidence))


@pytest.mark.asyncio
async def test_pending_requests_respect_resource_limits(
    migrated_index: tuple[Path, Engine],
) -> None:
    source, engine = migrated_index
    _build_index(source, engine)
    workers = ReadWorkers(max_workers=2)
    loop = asyncio.get_running_loop()
    at_limit = asyncio.Event()
    permits = threading.Semaphore(0)
    lock = threading.Lock()
    active: set[int] = set()
    worker_threads: set[int] = set()
    peak = 0
    started = 0
    returned = 0
    submitted = 0
    all_submitted = asyncio.Event()

    def checkout(dbapi: object, record: object, proxy: object) -> None:
        nonlocal peak
        with lock:
            active.add(id(dbapi))
            peak = max(peak, len(active))

    def checkin(dbapi: object, record: object) -> None:
        nonlocal returned
        with lock:
            active.remove(id(dbapi))
            returned += 1

    def stop(
        connection: Connection,
        cursor: object,
        statement: str,
        parameters: object,
        context: object,
        executemany: bool,
    ) -> None:
        nonlocal started
        with lock:
            started += 1
            worker_threads.add(threading.get_ident())
            if started == workers.max_workers:
                loop.call_soon_threadsafe(at_limit.set)
        assert permits.acquire(timeout=15), "worker release guard expired"

    async def request(index: int) -> tuple:
        nonlocal submitted
        submitted += 1
        if submitted == 5:
            all_submitted.set()
        return await SqlAlchemyEvidenceReader(engine, workers=workers).search(
            SearchCriteria(
                source=DetectionSource("logic"),
                keywords=(SearchKeyword("頭痛" if index % 2 == 0 else "腹痛"),),
            ),
            (),
        )

    listeners = [
        ("checkout", checkout),
        ("checkin", checkin),
        ("before_cursor_execute", stop),
    ]
    for name, listener in listeners:
        event.listen(engine, name, listener)
    tasks = [asyncio.create_task(request(index)) for index in range(5)]
    try:
        await all_submitted.wait()
        # 未実装APIなら正しいNotImplementedErrorを直ちに観測する。
        if all(task.done() for task in tasks):
            await asyncio.gather(*tasks)
        await asyncio.wait_for(at_limit.wait(), 20)
        with lock:
            assert len(active) == workers.max_workers
            assert started == workers.max_workers
        assert not any(task.done() for task in tasks)
        permits.release(5)
        results = await asyncio.wait_for(asyncio.gather(*tasks), 20)
        assert [[item.unit_id.value for item in batch] for batch in results] == [
            ["test_001:000", "test_001:001", "test_001:002"],
            [],
            ["test_001:000", "test_001:001", "test_001:002"],
            [],
            ["test_001:000", "test_001:001", "test_001:002"],
        ]
        assert peak == workers.max_workers
        assert len(worker_threads) == workers.max_workers
        assert started == returned == 5
        assert not active
        _assert_plain(results)
    finally:
        permits.release(5)
        await asyncio.gather(*tasks, return_exceptions=True)
        await workers.aclose()
        for name, listener in listeners:
            event.remove(engine, name, listener)


@pytest.mark.asyncio
async def test_shutdown_waits_for_cancelled_worker_cleanup(
    migrated_index: tuple[Path, Engine],
) -> None:
    source, engine = migrated_index
    _build_index(source, engine)
    app = FastAPI(lifespan=create_persistence_lifespan(engine, max_workers=2))
    lifespan = app.router.lifespan_context(app)
    await lifespan.__aenter__()
    workers = app.state.read_workers
    assert isinstance(workers, ReadWorkers)
    loop = asyncio.get_running_loop()
    started = asyncio.Event()
    release = threading.Event()
    transitions: list[str] = []
    checked_out: set[int] = set()
    errors: list[dict] = []
    old_handler = loop.get_exception_handler()
    loop.set_exception_handler(lambda current_loop, context: errors.append(context))

    def checkout(dbapi: object, record: object, proxy: object) -> None:
        checked_out.add(id(dbapi))
        transitions.append("checkout")

    def checkin(dbapi: object, record: object) -> None:
        checked_out.remove(id(dbapi))
        transitions.append("checkin")

    def rollback(connection: Connection) -> None:
        transitions.append("rollback")

    def dispose(disposed_engine: Engine) -> None:
        transitions.append("dispose")

    def stop(
        connection: Connection,
        cursor: object,
        statement: str,
        parameters: object,
        context: object,
        executemany: bool,
    ) -> None:
        transitions.append("sql_started")
        loop.call_soon_threadsafe(started.set)
        assert release.wait(15), "cancelled worker release guard expired"
        transitions.append("sql_finished")
        raise RuntimeError("worker cleanup observation")

    listeners = [
        ("checkout", checkout),
        ("checkin", checkin),
        ("rollback", rollback),
        ("engine_disposed", dispose),
        ("before_cursor_execute", stop),
    ]
    for name, listener in listeners:
        event.listen(engine, name, listener)
    task = asyncio.create_task(
        SqlAlchemyEvidenceReader(engine, workers=workers).search(
            SearchCriteria(
                source=DetectionSource("logic"), keywords=(SearchKeyword("頭痛"),)
            ),
            (),
        )
    )
    shutdown: asyncio.Task | None = None
    exit_started = asyncio.Event()

    async def exit_lifespan() -> None:
        exit_started.set()
        await lifespan.__aexit__(None, None, None)

    try:
        await asyncio.wait_for(started.wait(), 20)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert checked_out
        assert transitions == ["checkout", "sql_started"]
        shutdown = asyncio.create_task(exit_lifespan())
        await exit_started.wait()
        assert not shutdown.done(), "lifespan exited before started worker cleanup"
        assert "dispose" not in transitions
        release.set()
        await asyncio.wait_for(shutdown, 20)
        assert transitions == [
            "checkout",
            "sql_started",
            "sql_finished",
            "rollback",
            "checkin",
            "dispose",
        ]
        assert not checked_out
        assert not errors
    finally:
        release.set()
        await asyncio.gather(task, return_exceptions=True)
        if shutdown is not None:
            await asyncio.gather(shutdown, return_exceptions=True)
        else:
            await lifespan.__aexit__(None, None, None)
        await workers.aclose()
        for name, listener in listeners:
            event.remove(engine, name, listener)
        loop.set_exception_handler(old_handler)


@pytest.mark.asyncio
async def test_read_workers_returns_result_and_propagates_failure() -> None:
    workers = ReadWorkers(max_workers=1)

    def fail() -> None:
        raise RuntimeError("read failed")

    try:
        assert await workers.run(lambda: 42) == 42
        with pytest.raises(RuntimeError, match="read failed"):
            await workers.run(fail)
    finally:
        await workers.aclose()
