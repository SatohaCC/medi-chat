"""索引で識別される検索対象のEntity。"""

from dataclasses import dataclass

from ..attachment.identifiers import DocumentId, DocumentVersionId
from ..foundation.exceptions import DomainValidationError
from .identifiers import SearchUnitId
from .primitives import (
    EvidenceContextLabel,
    SearchUnitKind,
    SearchUnitProductCode,
    SearchUnitSectionCode,
    SearchUnitText,
    SearchUnitUrl,
)
from .value_objects import (
    DocumentRevision,
    SearchContentBlock,
    SearchDocumentVersion,
    VersionSearchIdentity,
)


@dataclass(frozen=True, slots=True, kw_only=True)
class SearchUnit:
    """検索対象となる添付文書内の本文単位Entity。"""

    unit_id: SearchUnitId
    document_id: DocumentId
    section_code: SearchUnitSectionCode
    kind: SearchUnitKind
    text: SearchUnitText
    product_codes: tuple[SearchUnitProductCode, ...] = ()
    source_url: SearchUnitUrl | None = None
    context_labels: tuple[EvidenceContextLabel, ...] = ()
    blocks: tuple[SearchContentBlock, ...] = ()
    revisions: tuple[DocumentRevision, ...] = ()
    section_title: SearchUnitText | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class VersionSearchSnapshot:
    document_id: DocumentId
    version_id: DocumentVersionId
    units: tuple[SearchUnit, ...]

    def __post_init__(self) -> None:
        SearchDocumentVersion(document_id=self.document_id, version_id=self.version_id)
        if not isinstance(self.units, tuple):
            raise DomainValidationError("version search units must be immutable")
        if len({unit.section_code for unit in self.units}) != len(self.units):
            raise DomainValidationError(
                "one search row per numbered section and source version"
            )
        for unit in self.units:
            identity = VersionSearchIdentity(
                document_id=self.document_id,
                version_id=self.version_id,
                section_code=unit.section_code,
            )
            if unit.document_id != self.document_id or unit.unit_id != identity.unit_id:
                raise DomainValidationError(
                    "search unit must retain its document and source-qualified identity"
                )
