"""一時原本の登録と、登録済み要求の再送を調整する。"""

from collections.abc import Callable

from backend.application.attachment_import.commands.models import ImportResult
from backend.application.attachment_import.errors import (
    ImportConflict,
    ImportLimitExceeded,
    InvalidAttachment,
    UnsupportedAttachment,
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
from backend.application.file_upload.errors import (
    InvalidUpload,
    UploadConflict,
    UploadGone,
    UploadLimitExceeded,
)
from backend.application.file_upload.interfaces.temporary_file_store import (
    TemporaryFileStore,
)


def import_uploaded_document(
    upload_id: str,
    *,
    store: TemporaryFileStore,
    receipts: UploadImportReceipts,
    registration: OriginalDocumentRegistration,
    reader: ImportReplay,
    check_cancel: Callable[[], None],
) -> ImportResult:
    check_cancel()
    try:
        receipt = receipts.find(upload_id)
        if receipt is not None:
            return reader.replay_result(receipt.document_id, receipt.source_sha256)
        try:
            uploaded = store.read(upload_id)
        except UploadGone:
            # A concurrent completion may have released the original after find().
            receipt = receipts.find(upload_id)
            if receipt is None:
                raise
            return reader.replay_result(receipt.document_id, receipt.source_sha256)
        check_cancel()
        result = registration.register(
            uploaded.source,
            original_filename=uploaded.spec.filename,
            check_cancel=check_cancel,
        )
        # After publication, finish its receipt even if cancellation arrives.
        receipts.record(upload_id, result.document_id)
        return result
    except (
        InvalidAttachment,
        UnsupportedAttachment,
        ImportLimitExceeded,
        ImportConflict,
        InvalidUpload,
        UploadLimitExceeded,
        UploadConflict,
    ) as exc:
        if exc.code != "upload_incomplete":
            store.discard(upload_id)
        raise
