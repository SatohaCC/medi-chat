"""HTTP等に公開する、取り込みと転送ユースケースの窓口。"""

from backend.application.attachment_import.commands.models import ImportResult
from backend.application.attachment_import.commands.services.import_document import (
    import_document,
)
from backend.application.attachment_import.commands.services.import_uploaded_document import (
    import_uploaded_document,
)
from backend.application.attachment_import.interfaces.import_execution import (
    ImportExecutor,
)
from backend.application.attachment_import.interfaces.import_replay import (
    ImportReplay,
)
from backend.application.attachment_import.interfaces.original_document_registration import (
    OriginalDocumentRegistration,
)
from backend.application.attachment_import.interfaces.upload_import_receipts import (
    UploadImportReceipts,
)
from backend.application.file_upload.commands.models import UploadSpec
from backend.application.file_upload.commands.services.start_upload import start_upload
from backend.application.file_upload.commands.services.upload_part import upload_part
from backend.application.file_upload.interfaces.temporary_file_store import (
    TemporaryFileStore,
)


class AttachmentImportCommands:
    def __init__(
        self,
        *,
        registration: OriginalDocumentRegistration,
        reader: ImportReplay,
        executor: ImportExecutor,
        upload_store: TemporaryFileStore | None = None,
        upload_receipts: UploadImportReceipts | None = None,
    ) -> None:
        self.registration = registration
        self.reader = reader
        self._executor = executor
        self.upload_store = upload_store
        self.upload_receipts = upload_receipts

    def _uploads(self) -> TemporaryFileStore:
        if self.upload_store is None:
            raise RuntimeError("Upload storage is not configured")
        return self.upload_store

    async def import_document(
        self, source: bytes, *, original_filename: str
    ) -> ImportResult:
        return await self._executor.run(
            lambda check: import_document(
                source,
                original_filename=original_filename,
                registration=self.registration,
                check_cancel=check,
            )
        )

    async def start_upload(self, spec: UploadSpec) -> str:
        store = self._uploads()
        return await self._executor.run(
            lambda check: start_upload(spec, store=store, check_cancel=check),
            on_cancel=store.discard,
        )

    async def upload_part(self, upload_id: str, index: int, content: bytes) -> None:
        await self._executor.run(
            lambda check: upload_part(upload_id, index, content, store=self._uploads())
        )

    async def finish_upload(self, upload_id: str) -> ImportResult:
        if self.upload_receipts is None:
            raise RuntimeError("Upload receipts are not configured")
        receipts = self.upload_receipts
        return await self._executor.run(
            lambda check: import_uploaded_document(
                upload_id,
                store=self._uploads(),
                receipts=receipts,
                registration=self.registration,
                reader=self.reader,
                check_cancel=check,
            )
        )

    async def aclose(self) -> None:
        await self._executor.aclose()
