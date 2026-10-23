from typing import Protocol

from backend.application.attachment_import.queries.dtos.import_views import (
    ImportDetail,
    ImportPage,
)


class ImportQueryReader(Protocol):
    def read_result(self, document_id: str, digest: str) -> ImportDetail: ...
    def list_imports(self, *, limit: int, offset: int) -> ImportPage: ...
