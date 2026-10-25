"""Segmented uploads persist across instances and publish only verified originals."""

import hashlib
from concurrent.futures import ThreadPoolExecutor

import pytest
from backend.application.file_upload.commands.models import MAX_SOURCE_BYTES, UploadSpec
from backend.application.file_upload.errors import (
    InvalidUpload,
    UploadConflict,
    UploadGone,
    UploadLimitExceeded,
)
from backend.config.upload_settings import CHUNK_BYTES
from backend.infrastructure.persistence.stores.postgres_upload_store import (
    PostgresUploadImportReceipts,
    PostgresUploadStore,
)
from backend.tests.support.postgres_fixtures import pg_engines as pg_engines
from sqlalchemy import text


def spec(raw):
    return UploadSpec("テスト.xml", len(raw), hashlib.sha256(raw).hexdigest())


def test_parts_survive_instance_change_and_cannot_be_replaced(pg_engines):
    a, b = (PostgresUploadStore(engine) for engine in pg_engines[:2])
    raw = b"a" * CHUNK_BYTES + b"tail"
    upload_id = a.create(spec(raw))
    a.put(upload_id, 0, raw[:CHUNK_BYTES])
    with pytest.raises(UploadConflict):
        b.read(upload_id)
    b.put(upload_id, 1, raw[CHUNK_BYTES:])
    a.put(upload_id, 0, raw[:CHUNK_BYTES])
    with pytest.raises(UploadConflict):
        b.put(upload_id, 0, b"b" * CHUNK_BYTES)
    assert b.read(upload_id).source == raw
    receipts = PostgresUploadImportReceipts(pg_engines[1])
    receipts.record(upload_id, "test-document")
    done = receipts.find(upload_id)
    assert done is not None and done.document_id == "test-document"
    with pytest.raises(UploadGone):
        b.read(upload_id)
    with pg_engines[0].connect() as connection:
        assert (
            connection.execute(
                text("SELECT count(*) FROM attachment_upload_parts")
            ).scalar_one()
            == 0
        )


def test_size_digest_and_expiration(pg_engines):
    store = PostgresUploadStore(pg_engines[1])
    upload_id = store.create(spec(b"abcd"))
    with pytest.raises(InvalidUpload):
        store.put(upload_id, 0, b"abc")
    store.put(upload_id, 0, b"wxyz")
    with pytest.raises(InvalidUpload):
        store.read(upload_id)
    with pg_engines[0].begin() as connection:
        connection.execute(
            text("UPDATE attachment_uploads SET expires_at=now()-interval '1 second'")
        )
    with pytest.raises(UploadGone):
        store.read(upload_id)
    store.create(spec(b"new"))
    with pg_engines[0].connect() as connection:
        assert (
            connection.execute(
                text("SELECT count(*) FROM attachment_upload_parts")
            ).scalar_one()
            == 0
        )


def test_concurrent_same_part_and_maximum_original(pg_engines):
    store = PostgresUploadStore(pg_engines[1])
    raw = b"x" * MAX_SOURCE_BYTES
    upload_id = store.create(spec(raw))
    with ThreadPoolExecutor(2) as pool:
        list(pool.map(lambda _: store.put(upload_id, 0, raw[:CHUNK_BYTES]), range(2)))
    for index, offset in enumerate(range(CHUNK_BYTES, len(raw), CHUNK_BYTES), start=1):
        store.put(upload_id, index, raw[offset : offset + CHUNK_BYTES])
    assert store.read(upload_id).source == raw


@pytest.mark.parametrize(
    "size,digest", [(0, "a" * 64), (MAX_SOURCE_BYTES + 1, "a" * 64), (1, "bad")]
)
def test_invalid_upload_spec(size, digest):
    with pytest.raises(ValueError):
        UploadSpec("テスト.xml", size, digest)


def test_session_capacity_and_completed_sessions_release_admission(pg_engines):
    from backend.infrastructure.persistence.stores.postgres_upload_store import (
        MAX_UPLOADS,
    )

    store = PostgresUploadStore(pg_engines[1])
    ids = [store.create(spec(b"test")) for _ in range(MAX_UPLOADS)]
    with pytest.raises(UploadLimitExceeded):
        store.create(spec(b"test"))
    store.put(ids[0], 0, b"test")
    assert store.read(ids[0]).source == b"test"
    PostgresUploadImportReceipts(pg_engines[1]).record(ids[0], "test-document")
    assert store.create(spec(b"next"))
