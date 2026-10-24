from __future__ import annotations

from dataclasses import dataclass, field

from backend.application.indexing.values import (
    EvidenceContextLabel,
    SearchCellSpan,
    SearchColumnIndex,
    SearchUnitId,
    SearchUnitKind,
    SearchUnitProductCode,
    SearchUnitSectionCode,
    SearchUnitText,
    SearchUnitUrl,
)
from backend.domain.attachment.identifiers import DocumentId
from backend.domain.foundation.json_types import JsonValue
from backend.domain.foundation.value_objects import ImmutableMapping


@dataclass(frozen=True, slots=True, eq=False)
class SearchReferenceMetadata(ImmutableMapping[JsonValue]):
    """索引に保持する原文参照のmetadata。"""


@dataclass(frozen=True, slots=True, kw_only=True)
class SearchContentContext:
    product_codes: tuple[SearchUnitProductCode, ...] = ()
    labels: tuple[SearchUnitText, ...] = ()
    section_code: SearchUnitSectionCode | None = None
    section_title: SearchUnitText | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class SearchContentReference:
    label: SearchUnitText
    target_id: SearchUnitText | None = None
    metadata: SearchReferenceMetadata = field(default_factory=SearchReferenceMetadata)


@dataclass(frozen=True, slots=True, kw_only=True)
class SearchTableCell:
    text: SearchUnitText
    column: SearchColumnIndex
    rowspan: SearchCellSpan
    colspan: SearchCellSpan
    references: tuple[SearchContentReference, ...] = ()
    context: SearchContentContext = field(default_factory=SearchContentContext)


@dataclass(frozen=True, slots=True, kw_only=True)
class SearchTable:
    columns: tuple[SearchUnitText, ...]
    rows: tuple[tuple[SearchTableCell, ...], ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class SearchParagraph:
    text: SearchUnitText
    is_heading: bool = False
    context: SearchContentContext
    references: tuple[SearchContentReference, ...] = ()


@dataclass(frozen=True, slots=True, kw_only=True)
class SearchTableBlock:
    table: SearchTable
    context: SearchContentContext
    references: tuple[SearchContentReference, ...] = ()


@dataclass(frozen=True, slots=True, kw_only=True)
class SearchFigure:
    reference: SearchUnitText
    description: SearchUnitText
    context: SearchContentContext
    references: tuple[SearchContentReference, ...] = ()


@dataclass(frozen=True, slots=True, eq=False)
class DocumentRevision(ImmutableMapping[JsonValue]):
    """根拠に含める原本の改訂情報。未知metadataも保持する。"""


@dataclass(frozen=True, slots=True, kw_only=True)
class SearchUnit:
    """添付文書から投影した、ID付きの検索本文単位。"""

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


type SearchContentBlock = SearchParagraph | SearchTableBlock | SearchFigure


@dataclass(frozen=True)
class IndexDocument:
    document_id: str
    payload: dict[str, JsonValue]


@dataclass(frozen=True)
class IndexUnit:
    unit_id: str
    document_id: str
    section_code: str
    kind: str
    payload: dict[str, JsonValue]
    query_text: str
    drug_name: str
