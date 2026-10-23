"""PG-021/035/048: healthy or cleanup-pending startup is strictly read-only."""

import httpx
import pytest
from backend.application.attachment_import.import_errors import ImportCancelled
from backend.infrastructure.persistence import postgres_schema as schema
from backend.infrastructure.pmda_xml.decoder import PmdaXmlDecoder
from backend.tests.integration.test_postgres_registration import (
    pg_publisher as pg_publisher,
)
from backend.tests.integration.test_postgres_registration import publish
from backend.tests.support.postgres_fixtures import pg_api as pg_api
from backend.tests.support.postgres_fixtures import pg_engines as pg_engines
from backend.tests.support.postgres_observations import digest
from backend.tests.support.registration_oracles import source
from sqlalchemy import event, select
from sqlalchemy.engine import Engine


@pytest.mark.asyncio
async def test_tc118_healthy_os_health_does_not_write_database_or_registered_files(
    pg_api, pg_engines
):
    app = pg_api()
    before = digest(pg_engines[0])
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client,
    ):
        for _ in range(3):
            assert (await client.get("/health")).status_code == 200
    assert digest(pg_engines[0]) == before


@pytest.mark.asyncio
async def test_pg021_pending_startup_has_no_cleanup_writes_then_explicit_maintenance_converges(
    pg_api, pg_engines, pg_publisher
):
    publish(pg_publisher, source("テスト旧payload"))
    cancelled = False

    def observe(point):
        nonlocal cancelled
        if point == "after_commit":
            cancelled = True

    def check():
        if cancelled:
            raise ImportCancelled()

    pg_publisher.fault = observe
    raw = source("テスト保留中の新版", revised_at="2026-11")
    result = pg_publisher.publish(PmdaXmlDecoder().decode(raw), raw, check_cancel=check)
    assert result.status == "registered_cleanup_pending"
    before = digest(pg_engines[0])
    statements = []

    def trace(connection, cursor, statement, parameters, context, executemany):
        statements.append(statement.lstrip().lower())

    event.listen(Engine, "before_cursor_execute", trace)
    try:
        app = pg_api()
        async with (
            app.router.lifespan_context(app),
            httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as client,
        ):
            assert (await client.get("/health")).status_code == 200
            saved = await client.get(
                f"/api/attachment-imports/{result.document_id}/{result.source_sha256}"
            )
            assert saved.json()["status"] == "registered_cleanup_pending"
    finally:
        event.remove(Engine, "before_cursor_execute", trace)
    assert not any(
        value.startswith(("insert", "update", "delete", "create", "drop", "alter"))
        for value in statements
    )
    assert digest(pg_engines[0]) == before
    pg_publisher.fault = lambda _: None
    pg_publisher.maintenance.cleanup()
    after = pg_publisher.results.read_result(result.document_id, result.source_sha256)
    assert after.status == "registered"
    assert after.registration_sequence == result.registration_sequence
    assert after.generation_id == result.generation_id
    with pg_engines[0].connect() as connection:
        assert len(connection.execute(select(schema.versions.c.version_id)).all()) == 2
