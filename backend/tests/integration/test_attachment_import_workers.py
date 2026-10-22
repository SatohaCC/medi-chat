"""Owned import-worker contracts on the real PostgreSQL publication boundary."""

import asyncio
import hashlib
import json
import threading

import pytest
from backend.application.attachment_import.import_document import (
    AttachmentImportService,
)
from backend.application.attachment_import.import_errors import ImportNotFound
from backend.infrastructure.persistence import postgres_schema as schema
from backend.infrastructure.pmda_xml.decoder import PmdaXmlDecoder
from backend.tests.integration.test_postgres_registration import (
    pg_publisher as pg_publisher,
)
from backend.tests.integration.test_postgres_registration import publish
from backend.tests.support.attachment_import_fixtures import xml_source
from backend.tests.support.postgres_fixtures import pg_engines as pg_engines
from backend.tests.support.registration_oracles import source as revision_source
from sqlalchemy import select


def service(publisher, decoder=None):
    return AttachmentImportService(
        decoder=decoder or PmdaXmlDecoder(),
        publisher=publisher,
        reader=publisher.results,
    )


@pytest.mark.asyncio
async def test_missing_figure_warning_and_caption_survive_store_restart(
    pg_engines, pg_publisher
):
    raw = xml_source(
        '<Warnings><Graphic><GraphicBody gfname="../../outside.gif"/><GraphicCaption><Lang>図の説明 Ａ①</Lang></GraphicCaption></Graphic></Warnings>'
    )
    first = service(pg_publisher)
    try:
        result = await first.import_document(raw, original_filename="figure.xml")
        assert result.validation_status == "warning"
        assert result.warnings[0].reference == "../../outside.gif"
        with pg_engines[0].connect() as connection:
            stored = connection.execute(
                select(schema.versions.c.source, schema.versions.c.structure)
            ).one()
        assert bytes(stored.source) == raw
        assert "図の説明 Ａ①" in json.dumps(stored.structure, ensure_ascii=False)
    finally:
        await first.aclose()
    restarted = service(pg_publisher)
    try:
        assert (
            await restarted.read_result(result.document_id, result.source_sha256)
            == result
        )
    finally:
        await restarted.aclose()


@pytest.mark.asyncio
async def test_resend_reuses_original_conversion_result_without_running_new_encoder(
    pg_engines, pg_publisher, monkeypatch
):
    importer = service(pg_publisher)
    raw = xml_source()
    try:
        first = await importer.import_document(raw, original_filename="first.xml")

        def refuse(*args, **kwargs):
            raise AssertionError("resend re-encoded committed version")

        monkeypatch.setattr(pg_publisher.preparer.encoder, "encode", refuse)
        second = await importer.import_document(
            raw, original_filename="../../renamed.xml"
        )
        assert not first.reused and second.reused
        assert first.source_sha256 == second.source_sha256
        assert first.transformer_version == second.transformer_version
        assert first.registration_sequence == second.registration_sequence
        with pg_engines[0].connect() as connection:
            assert (
                bytes(connection.execute(select(schema.versions.c.source)).scalar_one())
                == raw
            )
    finally:
        await importer.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize("phase", ["decode", "encode", "write", "publish"])
async def test_cancellation_waits_for_owned_worker_and_never_publishes_stage(
    pg_engines, pg_publisher, monkeypatch, phase
):
    old = publish(pg_publisher, xml_source())
    decoder = PmdaXmlDecoder()
    entered, release = threading.Event(), threading.Event()
    if phase in {"decode", "encode"}:
        target = decoder if phase == "decode" else pg_publisher.preparer.encoder
        method = phase
        original = getattr(target, method)

        def stopped(*args, **kwargs):
            entered.set()
            assert release.wait(10)
            return original(*args, **kwargs)

        monkeypatch.setattr(target, method, stopped)
    else:

        def fault(point):
            if point == ("source" if phase == "write" else "before_commit"):
                entered.set()
                assert release.wait(10)

        pg_publisher.fault = fault
    importer = service(pg_publisher, decoder)
    raw = revision_source("テスト取消版", revised_at="2026-11")
    task = asyncio.create_task(
        importer.import_document(raw, original_filename="cancel.xml")
    )
    try:
        assert await asyncio.to_thread(entered.wait, 10)
        task.cancel()
        await asyncio.sleep(0)
        assert not task.done()
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await task
        with pg_engines[0].connect() as connection:
            assert connection.execute(
                select(schema.receipts.c.source_sha256)
            ).scalars().all() == [old.source_sha256]
            assert connection.execute(
                select(schema.versions.c.version_id)
            ).scalars().all() == [f"{old.document_id}:{old.source_sha256}"]
        with pytest.raises(ImportNotFound):
            await importer.read_result(old.document_id, hashlib.sha256(raw).hexdigest())
    finally:
        release.set()
        await asyncio.gather(task, return_exceptions=True)
        await importer.aclose()


@pytest.mark.asyncio
async def test_heavy_worker_does_not_block_loop_and_shutdown_waits_for_it(
    pg_publisher, monkeypatch
):
    decoder = PmdaXmlDecoder()
    entered, release = threading.Event(), threading.Event()
    original = decoder.decode

    def decode(*args, **kwargs):
        entered.set()
        assert release.wait(10)
        return original(*args, **kwargs)

    monkeypatch.setattr(decoder, "decode", decode)
    importer = service(pg_publisher, decoder)
    task = asyncio.create_task(
        importer.import_document(xml_source(), original_filename="source.xml")
    )
    try:
        assert await asyncio.to_thread(entered.wait, 10)
        progress = asyncio.Event()

        async def lightweight():
            progress.set()

        await lightweight()
        assert progress.is_set()
        closing = asyncio.create_task(importer.aclose())
        await asyncio.sleep(0)
        assert not closing.done()
        release.set()
        assert (await task).status == "registered"
        await closing
    finally:
        release.set()
        await importer.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "encoding", ["utf-8-sig", "utf-16", "utf-16-le", "utf-16-be", "cp932"]
)
async def test_saved_original_is_exact_for_each_declared_encoding(
    pg_engines, pg_publisher, encoding
):
    declared = (
        "UTF-16"
        if encoding.startswith("utf-16")
        else "CP932"
        if encoding == "cp932"
        else "UTF-8"
    )
    raw = xml_source(
        prefix=f'<?xml version="1.0" encoding="{declared}"?>', encoding=encoding
    )
    importer = service(pg_publisher)
    try:
        result = await importer.import_document(raw, original_filename="encoding.xml")
        with pg_engines[0].connect() as connection:
            assert (
                bytes(connection.execute(select(schema.versions.c.source)).scalar_one())
                == raw
            )
        assert result.source_sha256 == hashlib.sha256(raw).hexdigest()
    finally:
        await importer.aclose()
