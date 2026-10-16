"""添付文書ドメインが必要とするRepository Interface。"""

from typing import Protocol

from .entities import (
    AttachmentDocument,
)
from .identifiers import DocumentId


class AttachmentRepository(Protocol):
    """添付文書の取得を抽象化する読み取りポート。"""

    async def find_document(
        self, document_id: DocumentId
    ) -> AttachmentDocument | None: ...
