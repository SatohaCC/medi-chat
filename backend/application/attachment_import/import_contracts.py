from collections.abc import Callable
from typing import Protocol

from backend.application.indexing.search_models import SearchUnit

from ...domain.attachment.entities import AttachmentDocument
from .import_models import ArtifactBundle, DecodedAttachment, ImportPage, ImportResult


class AttachmentDecoder(Protocol):
    def decode(self, source: bytes, *, original_filename: str) -> DecodedAttachment: ...


class AttachmentArtifactEncoder(Protocol):
    def encode(
        self,
        document: AttachmentDocument,
        search_units: tuple[SearchUnit, ...],
        source_info: object,
    ) -> ArtifactBundle: ...


class AttachmentRegistrationPublisher(Protocol):
    def publish(
        self,
        decoded: DecodedAttachment,
        source: bytes,
        *,
        check_cancel: Callable[[], None],
    ) -> ImportResult: ...
    def read_result(self, document_id: str, digest: str) -> ImportResult: ...
    def replay_result(self, document_id: str, digest: str) -> ImportResult: ...
    def list_imports(self, *, limit: int, offset: int) -> ImportPage: ...
