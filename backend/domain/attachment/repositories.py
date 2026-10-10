"""添付文書ドメインが必要とするRepository Interface。"""

from typing import Protocol

from .entities import AttachmentDocument, AttachmentProductRecord
from .identifiers import DocumentId


class AttachmentRepository(Protocol):
    """添付文書の取得を抽象化する読み取りポート。"""

    async def find_document(
        self, document_id: DocumentId
    ) -> AttachmentDocument | None: ...


class AttachmentProductRepository(Protocol):
    """添付文書に掲載された製品スナップショットを取得する。"""

    async def read_medicines(self) -> tuple[AttachmentProductRecord, ...]: ...
