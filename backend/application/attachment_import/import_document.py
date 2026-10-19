import asyncio
import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from contextlib import suppress
from dataclasses import replace
from typing import TypeVar

from .import_contracts import (
    AttachmentDecoder,
    AttachmentRegistrationPublisher,
)
from .import_errors import ImportCancelled
from .import_models import ImportPage, ImportResult
from .upload_contracts import UploadStore
from .upload_models import UploadSpec

T = TypeVar("T")


class AttachmentImportService:
    def __init__(
        self,
        *,
        decoder: AttachmentDecoder,
        publisher: AttachmentRegistrationPublisher,
        upload_store: UploadStore | None = None,
    ) -> None:
        self.decoder = decoder
        self.publisher = publisher
        self.upload_store = upload_store
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
            return self.publisher.publish(decoded, source, check_cancel=check_cancel)

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
        return await self._run(
            lambda: self.publisher.read_result(document_id, source_sha256),
            threading.Event(),
        )

    def _uploads(self) -> UploadStore:
        if self.upload_store is None:
            raise RuntimeError("Upload storage is not configured")
        return self.upload_store

    async def start_upload(self, spec: UploadSpec) -> str:
        return await self._run(lambda: self._uploads().create(spec), threading.Event())

    async def upload_part(self, upload_id: str, index: int, content: bytes) -> None:
        await self._run(
            lambda: self._uploads().put(upload_id, index, content), threading.Event()
        )

    async def finish_upload(self, upload_id: str) -> ImportResult:
        uploaded = await self._run(
            lambda: self._uploads().read(upload_id), threading.Event()
        )
        if uploaded.document_id is not None:
            result = await self.read_result(
                uploaded.document_id, uploaded.spec.source_sha256
            )
            return replace(result, reused=True)
        assert uploaded.source is not None
        result = await self.import_document(
            uploaded.source, original_filename=uploaded.spec.filename
        )
        await self._run(
            lambda: self._uploads().complete(upload_id, result.document_id),
            threading.Event(),
        )
        return result

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

    async def list_imports(self, *, limit: int, offset: int) -> ImportPage:
        if not 1 <= limit <= 100 or offset < 0:
            raise ValueError("Invalid import page")
        return await self._run(
            lambda: self.publisher.list_imports(limit=limit, offset=offset),
            threading.Event(),
        )
