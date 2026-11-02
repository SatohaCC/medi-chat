from typing import Protocol

from backend.application.package_insert_import.commands.models import (
    UploadImportReceipt,
)


class UploadImportReceipts(Protocol):
    def find(self, upload_id: str) -> UploadImportReceipt | None: ...
    def record(self, upload_id: str, document_id: str) -> None: ...
