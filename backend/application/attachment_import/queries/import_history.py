"""Import detail/history queries, independent of command handlers and results."""

from backend.application.attachment_import.interfaces.import_execution import (
    ImportExecutor,
)
from backend.application.attachment_import.interfaces.import_query_reader import (
    ImportQueryReader,
)
from backend.application.attachment_import.queries.dtos.import_views import (
    ImportDetail,
    ImportPage,
)


class ImportHistoryQueries:
    def __init__(self, *, reader: ImportQueryReader, executor: ImportExecutor):
        self.reader = reader
        self._executor = executor

    async def read_result(self, document_id: str, source_sha256: str) -> ImportDetail:
        return await self._executor.run(
            lambda check: self.reader.read_result(document_id, source_sha256)
        )

    async def list_imports(self, *, limit: int, offset: int) -> ImportPage:
        if not 1 <= limit <= 100 or offset < 0:
            raise ValueError("Invalid import page")
        return await self._executor.run(
            lambda check: self.reader.list_imports(limit=limit, offset=offset)
        )
