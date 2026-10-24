"""アップロード要求全体のキャンセル・終了契約。"""

import asyncio
import hashlib
import threading
from unittest.mock import Mock

import pytest
from backend.application.attachment_import.commands.import_documents import (
    AttachmentImportCommands,
)
from backend.application.attachment_import.interfaces.import_replay import (
    ImportReplay,
)
from backend.application.attachment_import.interfaces.upload_import_receipts import (
    UploadImportReceipts,
)
from backend.application.file_upload.commands.models import UploadedSource, UploadSpec
from backend.infrastructure.import_payloads import (
    AttachmentDecoder,
    AttachmentRegistrationPublisher,
)
from backend.infrastructure.persistence.import_workers import ImportWorkers
from backend.infrastructure.persistence.original_document_registration import (
    OriginalDocumentRegistration,
)
from backend.infrastructure.pmda_xml.decoder import PmdaXmlDecoder
from backend.tests.support.attachment_import_fixtures import encoded, xml_source


class UnusedStore:
    def create(self, spec: UploadSpec) -> str:
        raise AssertionError("unexpected create")

    def put(self, upload_id: str, index: int, content: bytes) -> None:
        raise AssertionError("unexpected put")

    def read(self, upload_id: str) -> UploadedSource:
        raise AssertionError("unexpected read")

    def complete(self, upload_id: str, document_id: str) -> None:
        raise AssertionError("unexpected complete")

    def discard(self, upload_id: str) -> None:
        raise AssertionError("unexpected discard")


@pytest.mark.asyncio
async def test_cancelled_upload_creation_discards_unreachable_session():
    entered, release = threading.Event(), threading.Event()
    sessions = set()

    class Store(UnusedStore):
        def create(self, spec):
            entered.set()
            assert release.wait(5)
            sessions.add("session")
            return "session"

        def discard(self, upload_id):
            sessions.remove(upload_id)

    service = make_service(upload_store=Store())
    task = asyncio.create_task(service.start_upload(spec()))
    try:
        assert await asyncio.to_thread(entered.wait, 5)
        task.cancel()
        await asyncio.sleep(0)
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert not sessions
    finally:
        release.set()
        await asyncio.gather(task, return_exceptions=True)
        await service.aclose()


def spec():
    return UploadSpec("テスト.xml", 1, hashlib.sha256(b"x").hexdigest())


def make_service(**kwargs):
    return AttachmentImportCommands(
        executor=ImportWorkers(),
        reader=Mock(spec=ImportReplay),
        upload_receipts=Mock(spec=UploadImportReceipts, find=Mock(return_value=None)),
        **kwargs,
        registration=OriginalDocumentRegistration(
            decoder=Mock(spec=AttachmentDecoder),
            publisher=Mock(spec=AttachmentRegistrationPublisher),
        ),
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("cancel_after_commit", [False, True])
async def test_shutdown_waits_for_publication_and_upload_completion(
    cancel_after_commit,
):
    entered, release = threading.Event(), threading.Event()
    completed = []

    class Store(UnusedStore):
        def read(self, upload_id):
            return UploadedSource(spec(), xml_source())

        def complete(self, upload_id: str, document_id: str) -> None:
            completed.append((upload_id, document_id))

    result = encoded(xml_source()).result

    class Publisher:
        def publish(self, *args, **kwargs):
            entered.set()
            assert release.wait(5)
            return result

    service = AttachmentImportCommands(
        executor=ImportWorkers(),
        reader=Mock(spec=ImportReplay),
        upload_store=Store(),
        upload_receipts=Mock(
            spec=UploadImportReceipts,
            find=Mock(return_value=None),
            record=Mock(
                side_effect=lambda upload_id, document_id: completed.append(
                    (upload_id, document_id)
                )
            ),
        ),
        registration=OriginalDocumentRegistration(
            decoder=PmdaXmlDecoder(), publisher=Publisher()
        ),
    )
    task = asyncio.create_task(service.finish_upload("session"))
    try:
        assert await asyncio.to_thread(entered.wait, 5)
        closing = asyncio.create_task(service.aclose())
        await asyncio.sleep(0)
        assert not closing.done()
        if cancel_after_commit:
            task.cancel()
            await asyncio.sleep(0)
        release.set()
        if cancel_after_commit:
            with pytest.raises(asyncio.CancelledError):
                await task
        else:
            assert await task is result
        await closing
        assert completed == [("session", result.document_id)]
    finally:
        release.set()
        await asyncio.gather(task, return_exceptions=True)
        await service.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "code, discarded", [("upload_incomplete", False), ("invalid_document", True)]
)
async def test_finish_failure_preserves_only_repairable_sessions(code, discarded):
    from backend.application.attachment_import.errors import ImportConflict

    calls = []

    class Store(UnusedStore):
        def read(self, upload_id):
            raise ImportConflict(code, "テスト失敗")

        def discard(self, upload_id):
            calls.append(upload_id)

    service = make_service(upload_store=Store())
    try:
        with pytest.raises(ImportConflict, match="テスト失敗"):
            await service.finish_upload("session")
        assert calls == (["session"] if discarded else [])
    finally:
        await service.aclose()


@pytest.mark.asyncio
async def test_shutdown_waits_cancelled_creation_cleanup_and_rejects_new_requests():
    created, release_create = threading.Event(), threading.Event()
    cleaning, release_cleanup = threading.Event(), threading.Event()
    calls = []

    class Store(UnusedStore):
        def create(self, spec):
            created.set()
            assert release_create.wait(5)
            return "session"

        def discard(self, upload_id):
            cleaning.set()
            assert release_cleanup.wait(5)
            calls.append(upload_id)

    service = make_service(upload_store=Store())
    task = asyncio.create_task(service.start_upload(spec()))
    try:
        assert await asyncio.to_thread(created.wait, 5)
        task.cancel()
        await asyncio.sleep(0)
        closing = asyncio.create_task(service.aclose())
        await asyncio.sleep(0)
        with pytest.raises(RuntimeError, match="closed"):
            await service.start_upload(spec())
        release_create.set()
        assert await asyncio.to_thread(cleaning.wait, 5)
        assert not closing.done()
        task.cancel()
        closing.cancel()
        await asyncio.sleep(0)
        assert not task.done() and not closing.done()
        release_cleanup.set()
        with pytest.raises(asyncio.CancelledError):
            await task
        with pytest.raises(asyncio.CancelledError):
            await closing
        assert calls == ["session"]
    finally:
        release_create.set()
        release_cleanup.set()
        await asyncio.gather(task, return_exceptions=True)
        await service.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize("concurrent_completion", [False, True])
async def test_completed_upload_replays_without_reimporting_original(
    concurrent_completion,
):
    from backend.application.attachment_import.commands.models import (
        UploadImportReceipt,
    )
    from backend.application.attachment_import.interfaces.original_document_registration import (
        OriginalDocumentRegistration as RegistrationPort,
    )
    from backend.application.file_upload.errors import UploadGone
    from backend.application.file_upload.interfaces.temporary_file_store import (
        TemporaryFileStore,
    )

    result = encoded(xml_source()).result
    receipt = UploadImportReceipt(result.document_id, result.source_sha256)
    receipts = Mock(spec=UploadImportReceipts)
    receipts.find.side_effect = [None, receipt] if concurrent_completion else [receipt]
    store = Mock(spec=TemporaryFileStore)
    store.read.side_effect = UploadGone("upload_source_released", "テスト原本解放済み")
    registration = Mock(spec=RegistrationPort)
    reader = Mock(spec=ImportReplay)
    reader.replay_result.return_value = result
    service = AttachmentImportCommands(
        registration=registration,
        reader=reader,
        executor=ImportWorkers(),
        upload_store=store,
        upload_receipts=receipts,
    )
    try:
        assert await service.finish_upload("session") is result
        registration.register.assert_not_called()
        receipts.record.assert_not_called()
        reader.replay_result.assert_called_once_with(
            result.document_id, result.source_sha256
        )
        assert store.read.call_count == int(concurrent_completion)
    finally:
        await service.aclose()
