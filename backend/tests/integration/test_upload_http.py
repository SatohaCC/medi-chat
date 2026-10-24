"""Real DB + HTTP: upload across application instances, retry and validation."""

import hashlib

import httpx
import pytest
from backend.application.attachment_import.errors import ImportStorageError
from backend.tests.support.attachment_import_fixtures import xml_source
from backend.tests.support.postgres_fixtures import pg_api as pg_api
from backend.tests.support.postgres_fixtures import pg_engines as pg_engines
from sqlalchemy import text


async def send_parts(client, raw, *, digest=None):
    started = await client.post(
        "/api/attachment-imports/uploads",
        json={
            "filename": "テスト.xml",
            "byte_size": len(raw),
            "source_sha256": digest or hashlib.sha256(raw).hexdigest(),
        },
    )
    assert started.status_code == 201
    session = started.json()
    path = f"/api/attachment-imports/uploads/{session['upload_id']}"
    for index, offset in enumerate(range(0, len(raw), session["chunk_bytes"])):
        assert (
            await client.post(
                f"{path}/parts/{index}",
                content=raw[offset : offset + session["chunk_bytes"]],
            )
        ).status_code == 204
    return path


@pytest.mark.asyncio
@pytest.mark.parametrize("cleanup_first", [True, False])
async def test_complete_retry_preserves_cleaned_receipt(pg_api, cleanup_first):
    app = pg_api()
    old = xml_source().replace(b"111111111111", b"222222222222")
    newer = old.replace(b"2026-10", b"2026-11")
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client,
    ):
        registered = await client.post(
            "/api/attachment-imports", files={"file": ("テスト.xml", old)}
        )
        assert registered.status_code == 201
        path = await send_parts(client, old)
        if cleanup_first:
            assert (
                await client.post(
                    "/api/attachment-imports", files={"file": ("テスト新版.xml", newer)}
                )
            ).status_code == 201
        first = await client.post(path + "/complete")
        assert first.status_code == 200
        if not cleanup_first:
            assert (
                await client.post(
                    "/api/attachment-imports", files={"file": ("テスト新版.xml", newer)}
                )
            ).status_code == 201
        assert (await client.get(registered.headers["location"])).status_code == 410
        retry = await client.post(path + "/complete")
        assert retry.status_code == 200
        assert retry.json()["reused"] is True
        assert retry.json()["artifacts_deleted"] is True
        assert retry.json()["active_yj_codes"] == []


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["xml", "digest"])
async def test_terminal_failure_releases_capacity(pg_api, pg_engines, failure):
    app = pg_api()
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client,
    ):
        for _ in range(17):
            path = await send_parts(
                client, b"<broken", digest="a" * 64 if failure == "digest" else None
            )
            assert (await client.post(path + "/complete")).status_code == 422
        with pg_engines[0].connect() as connection:
            for table in ("attachment_uploads", "attachment_upload_parts"):
                assert (
                    connection.execute(
                        text(f"SELECT count(*) FROM {table}")
                    ).scalar_one()
                    == 0
                )
        raw = xml_source().replace(b"111111111111", b"222222222222")
        path = await send_parts(client, raw)
        assert (await client.post(path + "/complete")).status_code == 201


@pytest.mark.asyncio
async def test_transient_failure_keeps_parts_for_retry(pg_api, monkeypatch):
    app = pg_api()
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client,
    ):
        raw = xml_source().replace(b"111111111111", b"222222222222")
        path = await send_parts(client, raw)
        publisher = app.state.attachment_import_service.registration.publisher
        publish = publisher.publish

        def fail(*args, **kwargs):
            raise ImportStorageError("test_unavailable", "テスト一時障害")

        monkeypatch.setattr(publisher, "publish", fail)
        assert (await client.post(path + "/complete")).status_code == 500
        monkeypatch.setattr(publisher, "publish", publish)
        assert (await client.post(path + "/complete")).status_code == 201


@pytest.mark.asyncio
async def test_segmented_http_publishes_exact_original_and_retry(pg_api, pg_engines):
    raw = (
        xml_source()
        .replace(b"111111111111", b"222222222222")
        .replace(
            b"</PackIns>",
            b"<!--"
            + b"x" * (10 * 1024 * 1024 - len(xml_source()) - 7)
            + b"--></PackIns>",
        )
    )
    assert len(raw) == 10 * 1024 * 1024
    digest = hashlib.sha256(raw).hexdigest()
    first, second = pg_api(), pg_api()
    async with (
        first.router.lifespan_context(first),
        second.router.lifespan_context(second),
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=first), base_url="http://test"
        ) as a,
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=second), base_url="http://test"
        ) as b,
    ):
        started = await a.post(
            "/api/attachment-imports/uploads",
            json={
                "filename": "テスト10MiB.xml",
                "byte_size": len(raw),
                "source_sha256": digest,
            },
        )
        assert started.status_code == 201
        upload = started.json()
        path = f"/api/attachment-imports/uploads/{upload['upload_id']}"
        assert (await b.post(path + "/complete")).status_code == 409
        for index, offset in enumerate(range(0, len(raw), upload["chunk_bytes"])):
            part = raw[offset : offset + upload["chunk_bytes"]]
            assert len(part) <= 3 * 1024 * 1024
            assert (
                await b.post(f"{path}/parts/{index}", content=part)
            ).status_code == 204
        result = await a.post(path + "/complete")
        assert result.status_code == 201
        assert result.json()["source_sha256"] == digest
        assert (await b.post(path + "/complete")).status_code == 200
    from sqlalchemy import text

    with pg_engines[0].connect() as connection:
        source = connection.execute(
            text(
                "SELECT source FROM attachment_versions WHERE version_id LIKE :suffix"
            ),
            {"suffix": "%:" + digest},
        ).scalar_one()
        assert source == raw
        assert (
            connection.execute(
                text("SELECT count(*) FROM attachment_upload_parts")
            ).scalar_one()
            == 0
        )


@pytest.mark.asyncio
async def test_upload_http_limits_and_missing_session(pg_api):
    app = pg_api()
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client,
    ):
        prefix = "/api/attachment-imports/uploads"
        assert (await client.post(prefix, content=b"x" * 4097)).status_code == 413
        assert (
            await client.post(
                prefix,
                json={
                    "filename": "test.xml",
                    "byte_size": 10485761,
                    "source_sha256": "a" * 64,
                },
            )
        ).status_code == 422
        assert (await client.post(prefix + "/unknown/complete")).status_code == 410
        assert (
            await client.post(
                prefix + "/unknown/parts/0", content=b"x" * (3 * 1024 * 1024 + 1)
            )
        ).status_code == 413
