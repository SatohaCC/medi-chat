"""Real PostgreSQL worker boundaries and same-loop API/WS responsiveness."""

import asyncio
import json
import threading
from dataclasses import fields, is_dataclass

import httpx
import pytest
from backend.application.indexing.values import SearchSectionCode
from backend.application.medicine.queries.models import (
    RegisteredMedicine,
    ResolvedMedicine,
)
from backend.application.retrieval.queries.models import SearchCriteria
from backend.application.retrieval.values import DetectionSource
from backend.domain.foundation.primitives.primitives import BaseFiniteFloat, BaseString
from backend.domain.medicine.identifiers import YjCode
from backend.domain.medicine.primitives import BrandName, GenericName, MatchedAlias
from backend.domain.medicine.value_objects import MedicineMatch as DomainMedicineMatch
from backend.infrastructure.persistence.read_workers import ReadWorkers
from backend.tests.support.postgres_fixtures import pg_api as pg_api
from backend.tests.support.postgres_fixtures import pg_engines as pg_engines
from sqlalchemy import event
from sqlalchemy.engine import Connection
from starlette.types import Message, Scope


@pytest.mark.asyncio
async def test_api_and_ws_respond_while_search_is_blocked(
    pg_api,
) -> None:
    app = pg_api()
    manager = app.router.lifespan_context(app)
    await manager.__aenter__()
    engine = app.state.database_engine
    runtime = app.state.generation_runtime
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
        if "FROM attachment_versions" in statement and not sql_started.is_set():
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

    async def search():
        async with runtime.acquire() as snapshot:
            return await snapshot.evidence_reader.search(
                SearchCriteria(
                    source=DetectionSource.LOGIC,
                    section_codes=(SearchSectionCode("11"),),
                ),
                (
                    ResolvedMedicine(
                        medicine=DomainMedicineMatch(
                            generic_name=GenericName("テスト成分"),
                            brand_names=tuple(
                                BrandName(value) for value in ("テスト薬",)
                            ),
                            yj_codes=tuple(
                                YjCode(value) for value in ("1234567A0000",)
                            ),
                            matched_aliases=tuple(MatchedAlias(value) for value in ()),
                        ),
                        document_ids=("test_001",),
                    ),
                ),
            )

    search_task = asyncio.create_task(search())
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
        assert [item.section["code"] for item in result] == ["11"]
        assert all(f"記載{index}" in result[0].excerpt.value for index in range(3))
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
        await manager.__aexit__(None, None, None)


def _assert_plain(value: object) -> None:
    if is_dataclass(value) and not isinstance(value, type):
        assert (
            type(value) is RegisteredMedicine
            or type(value).__module__.startswith("backend.domain.")
            or type(value).__module__
            in {
                "backend.application.indexing.queries.models",
                "backend.application.indexing.values",
                "backend.application.retrieval.queries.models",
                "backend.application.retrieval.values",
            }
        )
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


@pytest.mark.asyncio
@pytest.mark.parametrize("operation", ["medicine", "evidence", "statistics"])
async def test_pg027_workers_own_connections_and_return_plain_values(pg_api, operation):
    app = pg_api()
    async with app.router.lifespan_context(app):
        engine = app.state.database_engine
        runtime = app.state.generation_runtime
        loop_thread = threading.get_ident()
        acquired = []
        returned = []
        executions = []

        def checkout(dbapi, record, proxy):
            acquired.append((id(dbapi), threading.get_ident()))

        def checkin(dbapi, record):
            returned.append((id(dbapi), threading.get_ident()))

        def observe(connection, cursor, statement, parameters, context, executemany):
            executions.append(threading.get_ident())

        listeners = (
            ("checkout", checkout),
            ("checkin", checkin),
            ("before_cursor_execute", observe),
        )
        for name, callback in listeners:
            event.listen(engine, name, callback)
        try:
            if operation == "statistics":
                result = await runtime.statistics()
            else:
                async with runtime.acquire() as snapshot:
                    if operation == "medicine":
                        result = await snapshot.medicine_reader.read_medicines()
                    else:
                        result = await snapshot.evidence_reader.search(
                            SearchCriteria(
                                source=DetectionSource.LOGIC,
                                section_codes=(SearchSectionCode("11"),),
                            ),
                            (
                                ResolvedMedicine(
                                    medicine=DomainMedicineMatch(
                                        generic_name=GenericName("テスト成分"),
                                        brand_names=tuple(
                                            BrandName(value) for value in ("テスト薬",)
                                        ),
                                        yj_codes=tuple(
                                            YjCode(value) for value in ("1234567A0000",)
                                        ),
                                        matched_aliases=tuple(
                                            MatchedAlias(value) for value in ()
                                        ),
                                    ),
                                    document_ids=("test_001",),
                                ),
                            ),
                        )
            assert result
            _assert_plain(result)
            assert len(acquired) == len(returned) == 1
            assert acquired[0][0] == returned[0][0]
            assert executions
            assert loop_thread not in executions
            assert acquired[0][1] != loop_thread and returned[0][1] != loop_thread
            assert engine.pool.checkedout() == 0
        finally:
            for name, callback in listeners:
                event.remove(engine, name, callback)
