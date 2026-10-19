"""Real DB + HTTP: upload across application instances, retry and validation."""

import hashlib

import httpx
import pytest
from backend.tests.support.attachment_import_fixtures import xml_source
from backend.tests.support.postgres_fixtures import pg_api as pg_api
from backend.tests.support.postgres_fixtures import pg_engines as pg_engines


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
