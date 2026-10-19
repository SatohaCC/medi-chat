"""PG-023～027/051: real transaction/worker ownership and immutable results."""

import asyncio
import base64
import json
import os
import subprocess
import sys
import threading
import time

import pytest
from backend.application.medicine.product_models import ResolvedMedicine
from backend.domain.medicine.value_objects import MedicineMatch
from backend.domain.retrieval.primitives import DetectionSource, SearchSectionCode
from backend.domain.retrieval.value_objects import SearchCriteria
from backend.infrastructure.persistence import postgres_schema as s
from backend.infrastructure.persistence.postgres_runtime import PostgresRuntime
from backend.infrastructure.persistence.read_workers import ReadWorkers
from backend.tests.integration.test_postgres_registration import (
    pg_publisher as pg_publisher,
)
from backend.tests.integration.test_postgres_registration import publish
from backend.tests.support.paths import PROJECT_ROOT
from backend.tests.support.postgres_fixtures import pg_engines as pg_engines
from backend.tests.support.registration_oracles import source
from sqlalchemy import event, select, text
from sqlalchemy.exc import DBAPIError


def target(code="111111111111"):
    return (ResolvedMedicine(MedicineMatch("", (), (code,), ()), ("000001_test",)),)


def warning_criteria():
    return SearchCriteria(
        source=DetectionSource.LOGIC, section_codes=(SearchSectionCode("1"),)
    )


async def wait_event(event, task=None):
    for _ in range(1000):
        if event.is_set():
            return
        if task is not None and task.done():
            task.result()
        await asyncio.sleep(0.01)
    raise AssertionError("worker barrier was not reached")


def publish_in_process(schema, raw):
    environment = {
        **os.environ,
        "PYTHONUTF8": "1",
        "PG_WORKER_SCHEMA": schema,
        "PG_WORKER_SOURCE": base64.b64encode(raw).decode("ascii"),
    }
    result = subprocess.run(
        [sys.executable, "-m", "backend.tests.support.postgres_registration_worker"],
        cwd=PROJECT_ROOT,
        input="go\n",
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=20,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout.splitlines()[-1])


@pytest.mark.asyncio
async def test_pg023_scope_reads_old_rows_after_other_process_publication_and_delete(
    pg_engines, pg_publisher
):
    old = publish(pg_publisher, source("テスト旧根拠"))
    workers = ReadWorkers()
    runtime = PostgresRuntime(pg_engines[1], workers=workers)
    try:
        async with runtime.acquire() as snapshot:
            assert snapshot.generation_id.value == old.generation_id
            new = await asyncio.to_thread(
                publish_in_process,
                pg_engines[2],
                source("テスト新根拠", revised_at="2026-11"),
            )
            assert new["generation"] != old.generation_id
            with pg_engines[0].connect() as connection:
                assert not connection.execute(
                    select(s.versions.c.version_id).where(
                        s.versions.c.version_id
                        == f"{old.document_id}:{old.source_sha256}"
                    )
                ).first()
            medicines = await snapshot.medicine_reader.read_medicines()
            evidence = await snapshot.evidence_reader.search(
                warning_criteria(), target()
            )
            assert medicines[0].revision.to_dict()["year_month"] == "2026-10"
            assert len(evidence) == 1 and "テスト旧根拠" in evidence[0].excerpt
            assert evidence[0].document_revision.to_dict()["year_month"] == "2026-10"
        async with runtime.acquire() as current:
            assert current.generation_id.value == new["generation"]
            result = await current.evidence_reader.search(warning_criteria(), target())
            assert len(result) == 1 and "テスト新根拠" in result[0].excerpt
        assert pg_engines[1].pool.checkedout() == 0
    finally:
        await workers.aclose()


@pytest.mark.asyncio
async def test_pg024_snapshot_reads_only_needed_structure_and_never_original_bytes(
    pg_engines, pg_publisher, monkeypatch
):
    from backend.infrastructure.pmda_xml.decoder import PmdaXmlDecoder

    publish(pg_publisher, source("テスト構造から検索"))
    statements = []

    def observe(connection, cursor, statement, parameters, context, executemany):
        statements.append(statement.lower())
        assert "attachment_versions.source" not in statement.lower()
        assert "attachment_assets" not in statement.lower()

    def refuse_decode(*args, **kwargs):
        raise AssertionError("snapshot must not decode original XML")

    monkeypatch.setattr(PmdaXmlDecoder, "decode", refuse_decode)
    event.listen(pg_engines[1], "before_cursor_execute", observe)
    workers = ReadWorkers()
    try:
        async with PostgresRuntime(
            pg_engines[1], workers=workers
        ).acquire() as snapshot:
            assert snapshot.document_count == snapshot.unit_count == 1
            assert await snapshot.medicine_reader.read_medicines()
            assert not any(
                "attachment_versions.structure" in value for value in statements
            )
            assert await snapshot.evidence_reader.search(warning_criteria(), target())
            assert any("attachment_versions.structure" in value for value in statements)
    finally:
        event.remove(pg_engines[1], "before_cursor_execute", observe)
        await workers.aclose()


@pytest.mark.asyncio
async def test_pg024_scope_serializes_detector_queries_and_rejects_reuse(
    pg_engines, pg_publisher
):
    publish(pg_publisher, source("テスト並行根拠"))
    workers = ReadWorkers(max_workers=4)
    runtime = PostgresRuntime(pg_engines[1], workers=workers)
    pids = set()
    active_queries = 0
    maximum = 0
    mutex = threading.Lock()

    def trace(connection, cursor, statement, parameters, context, executemany):
        nonlocal active_queries, maximum
        pids.add(connection.connection.driver_connection.info.backend_pid)
        with mutex:
            active_queries += 1
            maximum = max(maximum, active_queries)
        time.sleep(0.002)

    def finished(*args):
        nonlocal active_queries
        with mutex:
            active_queries -= 1

    event.listen(pg_engines[1], "before_cursor_execute", trace)
    event.listen(pg_engines[1], "after_cursor_execute", finished)
    try:
        async with runtime.acquire() as snapshot:
            results = await asyncio.gather(
                *(
                    snapshot.evidence_reader.search(warning_criteria(), target())
                    for _ in range(4)
                )
            )
            assert results[0] and all(result == results[0] for result in results)
            reader = snapshot.evidence_reader
        assert len(pids) == 1 and maximum == 1
        with pytest.raises(RuntimeError, match="released"):
            await reader.search(warning_criteria(), target())
        assert pg_engines[1].pool.checkedout() == 0
    finally:
        event.remove(pg_engines[1], "before_cursor_execute", trace)
        event.remove(pg_engines[1], "after_cursor_execute", finished)
        await workers.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize("phase", ["opened", "pointer", "medicines", "search"])
async def test_pg025_cancel_waits_owned_worker_and_then_releases_connection(
    pg_engines, pg_publisher, phase
):
    publish(pg_publisher, source("テスト取消根拠"))
    entered, release = threading.Event(), threading.Event()

    def fault(actual):
        if actual == phase:
            entered.set()
            assert release.wait(10)

    workers = ReadWorkers()
    runtime = PostgresRuntime(pg_engines[1], workers=workers, fault=fault)

    async def request():
        async with runtime.acquire() as snapshot:
            await snapshot.medicine_reader.read_medicines()
            await snapshot.evidence_reader.search(warning_criteria(), target())

    task = asyncio.create_task(request())
    try:
        await wait_event(entered, task)
        task.cancel()
        started = time.monotonic()
        await asyncio.sleep(0.05)
        assert time.monotonic() - started < 1
        assert not task.done() and pg_engines[1].pool.checkedout() == 1
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert pg_engines[1].pool.checkedout() == 0
    finally:
        release.set()
        await asyncio.gather(task, return_exceptions=True)
        await workers.aclose()


@pytest.mark.asyncio
async def test_pg026_real_connection_loss_aborts_scope_without_snapshot_resume(
    pg_engines, pg_publisher
):
    publish(pg_publisher, source("テスト接続切断"))
    workers = ReadWorkers()
    runtime = PostgresRuntime(pg_engines[1], workers=workers)
    drivers = []

    def capture(connection, *args):
        driver = connection.connection.driver_connection
        if driver not in drivers:
            drivers.append(driver)

    event.listen(pg_engines[1], "after_cursor_execute", capture)
    try:
        with pytest.raises(DBAPIError):
            async with runtime.acquire() as snapshot:
                drivers[-1].close()
                await snapshot.medicine_reader.read_medicines()
        assert pg_engines[1].pool.checkedout() == 0
        async with runtime.acquire() as independent:
            assert await independent.medicine_reader.read_medicines()
    finally:
        event.remove(pg_engines[1], "after_cursor_execute", capture)
        await workers.aclose()


@pytest.mark.asyncio
async def test_pg024_connection_is_readonly_repeatable_read(pg_engines, pg_publisher):
    publish(pg_publisher, source("テスト読取専用"))
    workers = ReadWorkers()
    runtime = PostgresRuntime(pg_engines[1], workers=workers)
    connections = []

    def capture(connection, *args):
        connections.append(connection)

    event.listen(pg_engines[1], "after_cursor_execute", capture)
    try:
        with pytest.raises(DBAPIError):
            async with runtime.acquire():
                connection = connections[-1]
                assert (
                    await workers.run(
                        lambda: connection.exec_driver_sql(
                            "SHOW transaction_read_only"
                        ).scalar_one()
                    )
                    == "on"
                )
                assert (
                    await workers.run(
                        lambda: connection.exec_driver_sql(
                            "SHOW transaction_isolation"
                        ).scalar_one()
                    )
                    == "repeatable read"
                )
                await workers.run(
                    lambda: connection.exec_driver_sql(
                        "UPDATE registration_state SET sequence=sequence"
                    )
                )
        assert pg_engines[1].pool.checkedout() == 0
    finally:
        event.remove(pg_engines[1], "after_cursor_execute", capture)
        await workers.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize("phase", ["opened", "pointer", "medicines", "search"])
async def test_pg025_exception_at_each_read_phase_releases_pool(
    pg_engines, pg_publisher, phase
):
    publish(pg_publisher, source("テスト取得例外"))

    def fault(actual):
        if actual == phase:
            raise RuntimeError("test snapshot failure")

    workers = ReadWorkers()
    runtime = PostgresRuntime(pg_engines[1], workers=workers, fault=fault)
    try:
        with pytest.raises(RuntimeError, match="test snapshot failure"):
            async with runtime.acquire() as snapshot:
                await snapshot.medicine_reader.read_medicines()
                await snapshot.evidence_reader.search(warning_criteria(), target())
        assert pg_engines[1].pool.checkedout() == 0
        runtime.fault = lambda phase: None
        async with runtime.acquire() as independent:
            assert await independent.medicine_reader.read_medicines()
        assert pg_engines[1].pool.checkedout() == 0
    finally:
        await workers.aclose()


@pytest.mark.asyncio
async def test_pg025_cancellation_during_real_pool_checkout_waits_worker(
    pg_engines, pg_publisher
):
    publish(pg_publisher, source("テストpool待機"))
    held = [pg_engines[1].connect() for _ in range(5)]
    entered = threading.Event()

    class ObservedWorkers(ReadWorkers):
        async def run(self, operation):
            def observed():
                entered.set()
                return operation()

            return await super().run(observed)

    workers = ObservedWorkers()
    runtime = PostgresRuntime(pg_engines[1], workers=workers)

    async def request():
        async with runtime.acquire():
            raise AssertionError("Canceled request cannot enter the scope")

    task = asyncio.create_task(request())
    try:
        await wait_event(entered, task)
        await asyncio.sleep(0.05)
        assert not task.done() and pg_engines[1].pool.checkedout() == 5
        task.cancel()
        await asyncio.sleep(0.05)
        assert not task.done()
        held.pop().close()
        with pytest.raises(asyncio.CancelledError):
            await asyncio.wait_for(task, timeout=5)
        assert pg_engines[1].pool.checkedout() == 4
    finally:
        for connection in held:
            connection.close()
        await asyncio.gather(task, return_exceptions=True)
        await workers.aclose()
    assert pg_engines[1].pool.checkedout() == 0


@pytest.mark.asyncio
async def test_pg051_injected_pool_is_reused_and_only_owner_disposes(
    pg_engines, pg_publisher
):
    publish(pg_publisher, source("テストpool所有"))
    disposed = []

    def observe(engine):
        disposed.append(True)

    event.listen(pg_engines[1], "engine_disposed", observe)
    workers = ReadWorkers()
    runtime = PostgresRuntime(pg_engines[1], workers=workers)
    try:
        for _ in range(3):
            async with runtime.acquire() as snapshot:
                assert await snapshot.medicine_reader.read_medicines()
                assert await snapshot.evidence_reader.search(
                    warning_criteria(), target()
                )
            assert pg_engines[1].pool.checkedout() == 0
        await workers.aclose()
        assert disposed == []
        with pg_engines[1].connect() as connection:
            assert connection.execute(text("SELECT 1")).scalar_one() == 1
        pg_engines[1].dispose()
        assert disposed == [True]
    finally:
        event.remove(pg_engines[1], "engine_disposed", observe)
        await workers.aclose()


@pytest.mark.asyncio
async def test_pg027_detectors_pin_old_scope_then_llm_has_no_connection(
    pg_engines, pg_publisher
):
    from backend.application.retrieval.intent_contracts import IntentResult
    from backend.infrastructure.package_insert_definitions.loader import (
        get_package_insert_definitions,
    )
    from backend.presentation.chat_models import ChatMessage
    from backend.presentation.chat_service import AppChatService

    old = publish(pg_publisher, source("テストLLM前の原文"))
    workers = ReadWorkers()
    runtime = PostgresRuntime(pg_engines[1], workers=workers)

    class UnusedReaders:
        async def read_medicines(self):
            raise AssertionError("All product resolution must use the snapshot")

        async def search(self, criteria, medicines):
            raise AssertionError("All detectors must use the snapshot")

    class Detector:
        async def classify(self, request):
            assert pg_engines[1].pool.checkedout() == 1
            await workers.run(
                lambda: publish(
                    pg_publisher, source("テスト検出中更新", revised_at="2026-11")
                )
            )
            return IntentResult(is_available=False)

    class Keywords:
        def extract_keywords(self, text: str) -> tuple[str, ...]:
            return ()

    class Provider:
        async def stream_response(self, messages, model=None):
            assert pg_engines[1].pool.checkedout() == 0
            await workers.run(
                lambda: publish(
                    pg_publisher, source("テストLLM中更新", revised_at="2026-12")
                )
            )
            assert pg_engines[1].pool.checkedout() == 0
            assert any("テストLLM前の原文" in item["content"] for item in messages)
            yield "テスト固定回答"

    definitions = get_package_insert_definitions()
    service = AppChatService(
        medicine_reader=UnusedReaders(),
        evidence_reader=UnusedReaders(),
        intent_classifier=Detector(),
        keyword_extractor=Keywords(),
        intent_policy=definitions.intent_policy,
        answer_prompt_policy=definitions.answer_prompt_policy,
        provider_factory=lambda _: Provider(),
        snapshot_provider=runtime,
    )
    try:
        reply = await service.answer_question(
            [ChatMessage(role="user", content="警告")], ["111111111111"]
        )
        assert reply.answer == "テスト固定回答"
        assert reply.sources and all(
            "テストLLM前の原文" in item.excerpt for item in reply.sources
        )
        assert reply.sources[0].unit_id == f"{old.document_id}:{old.source_sha256}:1"
        assert pg_engines[1].pool.checkedout() == 0
    finally:
        await workers.aclose()
