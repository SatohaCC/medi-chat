"""添付文書ドメインが必要とするRepository Interface。"""

from typing import Protocol

from .entities import (
    AttachmentDocument,
    AttachmentProductRecord,
    AttachmentRegistration,
)
from .identifiers import DocumentId, DocumentVersionId
from .value_objects import RegistrationProposal, RegistrationReceipt


class AttachmentRepository(Protocol):
    """添付文書の取得を抽象化する読み取りポート。"""

    async def find_document(
        self, document_id: DocumentId
    ) -> AttachmentDocument | None: ...


class AttachmentProductRepository(Protocol):
    """添付文書に掲載された製品スナップショットを取得する。"""

    async def read_medicines(self) -> tuple[AttachmentProductRecord, ...]: ...


class AttachmentRegistrationRepository(Protocol):
    """登録状態の読書き。公開transaction/lockの調整はApplicationの責務。"""

    async def read_registration(self) -> AttachmentRegistration: ...

    async def find_receipt(
        self, version_id: DocumentVersionId
    ) -> RegistrationReceipt | None: ...

    async def save_registration(self, proposal: RegistrationProposal) -> None: ...
