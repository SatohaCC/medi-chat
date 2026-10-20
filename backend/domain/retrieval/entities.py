"""索引で識別される検索対象のEntity。"""

from dataclasses import dataclass

from ..attachment.identifiers import DocumentId
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
