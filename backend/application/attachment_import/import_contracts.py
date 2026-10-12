from collections.abc import Callable
from typing import Protocol

from ...domain.attachment.entities import AttachmentDocument
from ...domain.attachment.identifiers import DocumentId
from ...domain.retrieval.entities import SearchUnit
from .import_models import ArtifactBundle, DecodedAttachment, ImportResult


class AttachmentDecoder(Protocol):
    def decode(self, source: bytes, *, original_filename: str) -> DecodedAttachment: ...


class AttachmentArtifactEncoder(Protocol):
    def encode(
        self,
        document: AttachmentDocument,
        search_units: tuple[SearchUnit, ...],
        source_info: object,
    ) -> ArtifactBundle: ...


class AttachmentImportStore(Protocol):
    def read(self, document_id: DocumentId, source_sha256: str) -> ImportResult: ...
    def commit(
        self, bundle: ArtifactBundle, source: bytes, *, check_cancel: Callable[[], None]
    ) -> ImportResult: ...


class AttachmentRegistrationPublisher(Protocol):
    def publish(
        self,
        decoded: DecodedAttachment,
        source: bytes,
        *,
        check_cancel: Callable[[], None],
    ) -> ImportResult: ...
    def read_result(self, document_id: str, digest: str) -> ImportResult: ...
