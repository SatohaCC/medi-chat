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
    SearchFigure,
    SearchParagraph,
    SearchTableBlock,
    _require,
    _require_items,
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

    def __post_init__(self) -> None:
        _require(self.unit_id, SearchUnitId)
        _require(self.document_id, DocumentId)
        _require(self.section_code, SearchUnitSectionCode)
        _require(self.kind, SearchUnitKind)
        _require(self.text, SearchUnitText)
        _require_items(self.product_codes, SearchUnitProductCode)
        _require(self.source_url, SearchUnitUrl, optional=True)
        _require_items(self.context_labels, EvidenceContextLabel)
        _require_items(self.blocks, (SearchParagraph, SearchTableBlock, SearchFigure))
        _require_items(self.revisions, DocumentRevision)
        _require(self.section_title, SearchUnitText, optional=True)
