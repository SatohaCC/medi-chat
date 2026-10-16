"""TC-016/027/029/032/033/039/044: owned worker orchestration."""

import asyncio
import hashlib
import json
import threading

import pytest
from backend.application.attachment_import.import_document import (
    AttachmentImportService,
)
from backend.application.attachment_import.import_errors import ImportNotFound
from backend.domain.attachment.identifiers import DocumentId
from backend.infrastructure.persistence.attachment_import_store import (
    FileAttachmentImportStore,
)
from backend.infrastructure.pmda_xml.artifact_mapping import PmdaArtifactEncoder
from backend.infrastructure.pmda_xml.decoder import PmdaXmlDecoder
from backend.tests.attachment_import_fixtures import encoded, xml_source
from backend.tests.test_attachment_import_store import hashes


@pytest.mark.asyncio
async def test_missing_figure_warning_and_caption_survive_store_restart(tmp_path):
    source = xml_source(
        '<Warnings><Graphic><GraphicBody gfname="../../outside.gif"/><GraphicCaption><Lang>図の説明 Ａ①</Lang></GraphicCaption></Graphic></Warnings>'
    )
    service = AttachmentImportService(
        decoder=PmdaXmlDecoder(),
        encoder=PmdaArtifactEncoder(),
        store=FileAttachmentImportStore(tmp_path),
    )
    try:
        result = await service.import_document(source, original_filename="figure.xml")
        assert result.validation_status == "warning"
        assert result.warnings[0].reference == "../../outside.gif"
        document = json.loads(next(tmp_path.rglob("document.json")).read_bytes())
        assert "図の説明 Ａ①" in json.dumps(document, ensure_ascii=False)
        assert next(tmp_path.rglob("source.xml")).read_bytes() == source
        assert (
            FileAttachmentImportStore(tmp_path).read(
                DocumentId(result.document_id), result.source_sha256
            )
            == result
        )
    finally:
        await service.aclose()


@pytest.mark.asyncio
async def test_resend_reuses_original_conversion_result_without_running_new_encoder(
    tmp_path, monkeypatch
):
    store = FileAttachmentImportStore(tmp_path)
    encoder = PmdaArtifactEncoder()
    service = AttachmentImportService(
        decoder=PmdaXmlDecoder(), encoder=encoder, store=store
    )
    source = xml_source()
    try:
        first = await service.import_document(source, original_filename="first.xml")
        before = hashes(tmp_path)
        encoder.transformer_version = "new-version"
        monkeypatch.setattr(
            encoder,
            "encode",
            lambda *args: pytest.fail("resend re-encoded committed version"),
        )
        second = await service.import_document(
            source, original_filename="../../renamed.xml"
        )
        assert not first.reused and second.reused
        assert first.source_sha256 == second.source_sha256
        assert first.transformer_version == second.transformer_version
        assert hashes(tmp_path) == before
    finally:
        await service.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize("phase", ["decode", "encode", "write", "publish"])
async def test_cancellation_waits_for_owned_worker_and_never_publishes_stage(
    tmp_path, monkeypatch, phase
):
    store = FileAttachmentImportStore(tmp_path)
    original_source = xml_source()
    original_bundle = encoded(original_source)
    store.commit(original_bundle, original_source)
    before = hashes(tmp_path)
    decoder = PmdaXmlDecoder()
    encoder = PmdaArtifactEncoder()
    entered = threading.Event()
    release = threading.Event()
    target, method = {
        "decode": (decoder, "decode"),
        "encode": (encoder, "encode"),
        "write": (store, "_write_file"),
        "publish": (store, "_publish"),
    }[phase]
    original = getattr(target, method)

    def stopped(*args, **kwargs):
        entered.set()
        assert release.wait(10)
        return original(*args, **kwargs)

    monkeypatch.setattr(target, method, stopped)
    service = AttachmentImportService(decoder=decoder, encoder=encoder, store=store)
    source = xml_source("<Warnings><Lang>取消版</Lang></Warnings>")
    bundle = encoded(source)
    task = asyncio.create_task(
        service.import_document(source, original_filename="cancel.xml")
    )
    try:
        await asyncio.sleep(0)
        if task.done():
            task.result()
        assert await asyncio.to_thread(entered.wait, 10)
        task.cancel()
        await asyncio.sleep(0)
        assert not task.done()
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert hashes(tmp_path) == before
        assert not list(tmp_path.glob(".stage-*"))
        with pytest.raises(ImportNotFound):
            store.read(bundle.document_id, bundle.source_sha256)
    finally:
        release.set()
        await service.aclose()


@pytest.mark.asyncio
async def test_heavy_worker_does_not_block_loop_and_shutdown_waits_for_it(
    tmp_path, monkeypatch
):
    decoder = PmdaXmlDecoder()
    entered = threading.Event()
    release = threading.Event()
    original = decoder.decode

    def decode(*args, **kwargs):
        entered.set()
        assert release.wait(10)
        return original(*args, **kwargs)

    monkeypatch.setattr(decoder, "decode", decode)
    service = AttachmentImportService(
        decoder=decoder,
        encoder=PmdaArtifactEncoder(),
        store=FileAttachmentImportStore(tmp_path),
    )
    task = asyncio.create_task(
        service.import_document(xml_source(), original_filename="source.xml")
    )
    try:
        await asyncio.sleep(0)
        if task.done():
            task.result()
        assert await asyncio.to_thread(entered.wait, 10)
        # This coroutine progresses while the real parser worker remains stopped.
        progress = asyncio.Event()

        async def lightweight():
            progress.set()

        await lightweight()
        assert progress.is_set()
        closing = asyncio.create_task(service.aclose())
        await asyncio.sleep(0)
        assert not closing.done()
        release.set()
        assert (await task).status == "stored"
        await closing
    finally:
        release.set()
        await service.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "encoding", ["utf-8-sig", "utf-16", "utf-16-le", "utf-16-be", "cp932"]
)
async def test_saved_original_is_exact_for_each_declared_encoding(tmp_path, encoding):
    declared = (
        "UTF-16"
        if encoding.startswith("utf-16")
        else "CP932"
        if encoding == "cp932"
        else "UTF-8"
    )
    source = xml_source(
        prefix=f'<?xml version="1.0" encoding="{declared}"?>', encoding=encoding
    )
    service = AttachmentImportService(
        decoder=PmdaXmlDecoder(),
        encoder=PmdaArtifactEncoder(),
        store=FileAttachmentImportStore(tmp_path),
    )
    try:
        result = await service.import_document(source, original_filename="encoding.xml")
        (source_path,) = tmp_path.rglob("source.xml")
        assert source_path.read_bytes() == source
        assert result.source_sha256 == hashlib.sha256(source).hexdigest()
    finally:
        await service.aclose()
