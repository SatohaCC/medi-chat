import asyncio
import hashlib
import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from contextlib import suppress
from dataclasses import replace
from typing import TypeVar

from ...domain.attachment.identifiers import DocumentId
from ..indexing.attachment_projection import project_attachment
from .import_contracts import (
    AttachmentArtifactEncoder,
    AttachmentDecoder,
    AttachmentImportStore,
    AttachmentRegistrationPublisher,
)
from .import_errors import ImportCancelled, ImportNotFound
from .import_models import ImportResult

T = TypeVar("T")


class AttachmentImportService:
    def __init__(
        self,
        *,
        decoder: AttachmentDecoder,
        encoder: AttachmentArtifactEncoder,
        store: AttachmentImportStore,
        publisher: AttachmentRegistrationPublisher | None = None,
    ) -> None:
        self.decoder = decoder
        self.encoder = encoder
        self.store = store
        self.publisher = publisher
        self._executor = ThreadPoolExecutor(
            max_workers=2, thread_name_prefix="attachment-import"
        )
        self._closed = False
        self._lock = threading.Lock()

    async def import_document(
        self, source: bytes, *, original_filename: str
    ) -> ImportResult:
        cancelled = threading.Event()

        def check_cancel() -> None:
            if cancelled.is_set():
                raise ImportCancelled

        def operation() -> ImportResult:
            check_cancel()
            decoded = self.decoder.decode(source, original_filename=original_filename)
            if self.publisher is not None:
                return self.publisher.publish(
                    decoded, source, check_cancel=check_cancel
                )
            check_cancel()
            digest = hashlib.sha256(source).hexdigest()
            try:
                existing = self.store.read(decoded.document.document_id, digest)
            except ImportNotFound:
                pass
            else:
                return replace(existing, reused=True)
            check_cancel()
            bundle = self.encoder.encode(
                decoded.document,
                project_attachment(decoded.document),
                decoded.source_info,
            )
            check_cancel()
            return self.store.commit(bundle, source, check_cancel=check_cancel)

        return await self._run(operation, cancelled)

    async def _run(self, operation: Callable[[], T], cancelled: threading.Event) -> T:
        with self._lock:
            if self._closed:
                raise RuntimeError("Import service is closed")
            native = self._executor.submit(operation)
        result = asyncio.wrap_future(native)
        cancellation_seen = False
        while not result.done():
            try:
                await asyncio.shield(result)
            except asyncio.CancelledError:
                cancellation_seen = True
                cancelled.set()
            except Exception:
                if cancellation_seen:
                    break
                raise
        if cancellation_seen:
            # Retrieving the native result/exception completes the owned worker cleanup.
            with suppress(Exception):
                result.result()
            raise asyncio.CancelledError
        return result.result()

    async def read_result(self, document_id: str, source_sha256: str) -> ImportResult:
        if self.publisher is not None:
            publisher = self.publisher
            return await self._run(
                lambda: publisher.read_result(document_id, source_sha256),
                threading.Event(),
            )
        return await self._run(
            lambda: self.store.read(DocumentId(document_id), source_sha256),
            threading.Event(),
        )

    async def aclose(self) -> None:
        with self._lock:
            self._closed = True
        cleanup = asyncio.create_task(
            asyncio.to_thread(self._executor.shutdown, wait=True)
        )
        cancelled = False
        while not cleanup.done():
            try:
                await asyncio.shield(cleanup)
            except asyncio.CancelledError:
                cancelled = True
        cleanup.result()
        if cancelled:
            raise asyncio.CancelledError
