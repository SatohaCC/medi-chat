"""取り込みユースケースの入出力。保存表現はopaqueな外部port情報。"""

from dataclasses import dataclass

from ...domain.attachment.entities import AttachmentDocument
from ...domain.attachment.identifiers import DocumentId


@dataclass(frozen=True, slots=True)
class DecodedAttachment:
    document: AttachmentDocument
    source_info: object


@dataclass(frozen=True, slots=True)
class ImportWarning:
    code: str
    reference: str


@dataclass(frozen=True, slots=True)
class ImportedProduct:
    yj_code: str | None
    brand_name: str | None


@dataclass(frozen=True, slots=True)
class ImportedRevision:
    source_label: str | None
    year_month: str | None
    version: str | None


@dataclass(frozen=True, slots=True)
class ImportResult:
    document_id: str
    source_sha256: str
    validation_status: str
    section_count: int
    search_unit_count: int
    products: tuple[ImportedProduct, ...]
    revisions: tuple[ImportedRevision, ...]
    warnings: tuple[ImportWarning, ...]
    transformer_version: str
    reused: bool = False
    status: str = "stored"
    search_index_updated: bool = False
    generation_id: str | None = None
    registration_sequence: int | None = None
    active_yj_codes: tuple[str, ...] = ()
    replaced_yj_codes: tuple[str, ...] = ()
    deleted_version_ids: tuple[str, ...] = ()
    cleanup_pending: tuple[tuple[str, str], ...] = ()
    artifacts_deleted: bool = False


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
