"""XML変換・成果物生成・DB登録の間で使うInfrastructure内部契約。"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

from backend.application.attachment_import.commands.models import ImportResult
from backend.application.indexing.queries.models import SearchUnit
from backend.domain.attachment.entities import AttachmentDocument
from backend.domain.attachment.identifiers import DocumentId


@dataclass(frozen=True, slots=True)
class AttachmentSourceInformation:
    """原本のメタデータ・構造化行・検証結果・変換イベントを渡す境界情報。"""

    document: dict[str, Any]
    rows: list[dict[str, Any]]
    validation: dict[str, Any]
    events: list[dict[str, object]]


@dataclass(frozen=True, slots=True)
class DecodedAttachment:
    document: AttachmentDocument
    source_info: AttachmentSourceInformation


@dataclass(frozen=True, slots=True)
class ArtifactFile:
    name: str
    content: bytes


@dataclass(frozen=True, slots=True)
class ArtifactBundle:
    document_id: DocumentId
    source_sha256: str
    files: tuple[ArtifactFile, ...]
    result: ImportResult


class AttachmentDecoder(Protocol):
    def decode(self, source: bytes, *, original_filename: str) -> DecodedAttachment: ...


class AttachmentArtifactEncoder(Protocol):
    def encode(
        self,
        document: AttachmentDocument,
        search_units: tuple[SearchUnit, ...],
        source_info: AttachmentSourceInformation,
    ) -> ArtifactBundle: ...


class AttachmentRegistrationPublisher(Protocol):
    def publish(
        self,
        decoded: DecodedAttachment,
        source: bytes,
        *,
        check_cancel: Callable[[], None],
    ) -> ImportResult: ...
