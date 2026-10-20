"""添付文書ドメインの不変Value Object。

AttachmentRevision / Source / Product / Section は添付文書自体の構造を表す。
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from ..foundation.json_types import JsonValue
from ..foundation.value_objects import ImmutableMapping
from ..medicine.identifiers import YjCode
from .exceptions import (
    AttachmentDomainError,
    MissingOrInvalidYjError,
    MissingRevisionError,
)
from .identifiers import DocumentId
from .primitives import (
    AttachmentBrandName,
    AttachmentCellSpan,
    AttachmentColumnIndex,
    AttachmentEnglishName,
    AttachmentProductCode,
    AttachmentSectionTitle,
    AttachmentSha256,
    AttachmentSourceOrder,
    AttachmentText,
    AttachmentUrl,
    DefinitionTitle,
    DocumentVersionId,
    InteractionColumnId,
    NumberedSectionCode,
    PmdaUrl,
    RevisionSourceLabel,
    RevisionVersion,
    RevisionYearMonth,
)


@dataclass(frozen=True, slots=True, kw_only=True)
class SectionDefinition:
    code: NumberedSectionCode
    title: DefinitionTitle

    def __post_init__(self) -> None:
        _require(self.code, NumberedSectionCode)
        _require(self.title, DefinitionTitle)


@dataclass(frozen=True, slots=True, kw_only=True)
class SectionTaxonomy:
    sections: tuple[SectionDefinition, ...]

    def __post_init__(self) -> None:
        _require_items(self.sections, SectionDefinition)
        codes = tuple(section.code for section in self.sections)
        if len(codes) != len(set(codes)):
            raise AttachmentDomainError("duplicate section definition")
        for code in codes:
            if code.parent_code is not None and code.parent_code not in codes:
                raise AttachmentDomainError("unknown parent section definition")


@dataclass(frozen=True, slots=True, kw_only=True)
class InteractionColumnDefinition:
    id: InteractionColumnId
    title: DefinitionTitle

    def __post_init__(self) -> None:
        _require(self.id, InteractionColumnId)
        _require(self.title, DefinitionTitle)


@dataclass(frozen=True, slots=True, kw_only=True)
class RegistrationVersion:
    document_id: DocumentId
    source_sha256: AttachmentSha256
    yj_codes: frozenset[YjCode]
    revised_at: RevisionYearMonth

    def __post_init__(self) -> None:
        if not isinstance(self.document_id, DocumentId) or not isinstance(
            self.source_sha256, AttachmentSha256
        ):
            raise AttachmentDomainError(
                "registration version requires typed document identity and source SHA256"
            )
        if (
            not isinstance(self.yj_codes, frozenset)
            or not self.yj_codes
            or any(not isinstance(code, YjCode) for code in self.yj_codes)
        ):
            raise MissingOrInvalidYjError("missing_or_invalid_yj")
        if not isinstance(self.revised_at, RevisionYearMonth):
            raise MissingRevisionError("registration requires a revision month")

    @property
    def version_id(self) -> DocumentVersionId:
        return DocumentVersionId(f"{self.document_id}:{self.source_sha256}")


def _require(
    value: object, expected: type | tuple[type, ...], *, optional: bool = False
) -> None:
    if optional and value is None:
        return
    if not isinstance(value, expected):
        raise AttachmentDomainError(
            f"invalid attachment field type: expected {expected}"
        )


def _require_items(values: object, item_type: type | tuple[type, ...]) -> None:
    if not isinstance(values, tuple):
        raise AttachmentDomainError("content collections must be tuples")
    for value in values:
        _require(value, item_type)


@dataclass(frozen=True, slots=True, kw_only=True)
class AttachmentReferenceTarget:
    """原文内で参照可能な要素。タグや保存形式には依存しない。"""

    reference_id: AttachmentText
    text: AttachmentText
    context: AttachmentContext = field(default_factory=lambda: AttachmentContext())

    def __post_init__(self) -> None:
        _require(self.reference_id, AttachmentText)
        _require(self.text, AttachmentText)
        _require(self.context, AttachmentContext)


@dataclass(frozen=True, slots=True, eq=False)
class AttachmentMetadata(ImmutableMapping[JsonValue]):
    """原本の未知metadataも失わない独立した値。"""

    def __post_init__(self) -> None:
        _require(self._data, Mapping)
        super().__post_init__()


@dataclass(frozen=True, slots=True, kw_only=True)
class AttachmentContext:
    """原文の適用対象と文脈の順序。"""

    product_codes: tuple[AttachmentProductCode, ...] = ()
    labels: tuple[AttachmentText, ...] = ()
    # 文書全体での出現順。同じ文脈の隣接表行の結合判定には含めない。
    source_order: AttachmentSourceOrder | None = field(default=None, compare=False)

    def __post_init__(self) -> None:
        _require_items(self.product_codes, AttachmentProductCode)
        _require_items(self.labels, AttachmentText)
        _require(self.source_order, AttachmentSourceOrder, optional=True)


@dataclass(frozen=True, slots=True, kw_only=True)
class AttachmentReference:
    """本文中の参照表示と原文内の参照先。"""

    label: AttachmentText
    target_id: AttachmentText | None = None
    metadata: AttachmentMetadata = field(default_factory=AttachmentMetadata)

    def __post_init__(self) -> None:
        _require(self.label, AttachmentText)
        _require(self.target_id, AttachmentText, optional=True)
        _require(self.metadata, AttachmentMetadata)


@dataclass(frozen=True, slots=True, kw_only=True)
class AttachmentTableCell:
    """原文セルと結合情報。列番号は0から始める。"""

    text: AttachmentText
    column: AttachmentColumnIndex
    rowspan: AttachmentCellSpan = field(default_factory=lambda: AttachmentCellSpan(1))
    colspan: AttachmentCellSpan = field(default_factory=lambda: AttachmentCellSpan(1))
    references: tuple[AttachmentReference, ...] = ()
    context: AttachmentContext = field(default_factory=AttachmentContext)

    def __post_init__(self) -> None:
        _require(self.text, AttachmentText)
        _require(self.column, AttachmentColumnIndex)
        _require(self.rowspan, AttachmentCellSpan)
        _require(self.colspan, AttachmentCellSpan)
        _require(self.context, AttachmentContext)
        _require_items(self.references, AttachmentReference)


@dataclass(frozen=True, slots=True, kw_only=True)
class AttachmentTable:
    """列と行の対応を保つ原文表。"""

    columns: tuple[AttachmentText, ...]
    rows: tuple[tuple[AttachmentTableCell, ...], ...]
    column_contexts: tuple[AttachmentContext, ...] = ()

    def __post_init__(self) -> None:
        _require_items(self.columns, AttachmentText)
        _require_items(self.rows, tuple)
        for row in self.rows:
            _require_items(row, AttachmentTableCell)
        _require_items(self.column_contexts, AttachmentContext)
        if self.column_contexts and len(self.column_contexts) != len(self.columns):
            raise AttachmentDomainError("table column contexts must match headings")


@dataclass(frozen=True, slots=True, kw_only=True)
class AttachmentParagraph:
    text: AttachmentText
    is_heading: bool = False
    context: AttachmentContext = field(default_factory=AttachmentContext)
    references: tuple[AttachmentReference, ...] = ()

    def __post_init__(self) -> None:
        _require(self.text, AttachmentText)
        _require(self.is_heading, bool)
        _require(self.context, AttachmentContext)
        _require_items(self.references, AttachmentReference)


@dataclass(frozen=True, slots=True, kw_only=True)
class AttachmentTableBlock:
    table: AttachmentTable
    context: AttachmentContext = field(default_factory=AttachmentContext)
    references: tuple[AttachmentReference, ...] = ()

    def __post_init__(self) -> None:
        _require(self.table, AttachmentTable)
        _require(self.context, AttachmentContext)
        _require_items(self.references, AttachmentReference)


@dataclass(frozen=True, slots=True, kw_only=True)
class AttachmentFigure:
    reference: AttachmentText
    description: AttachmentText
    context: AttachmentContext = field(default_factory=AttachmentContext)
    references: tuple[AttachmentReference, ...] = ()

    def __post_init__(self) -> None:
        _require(self.reference, AttachmentText)
        _require(self.description, AttachmentText)
        _require(self.context, AttachmentContext)
        _require_items(self.references, AttachmentReference)


type AttachmentBlock = AttachmentParagraph | AttachmentTableBlock | AttachmentFigure


@dataclass(frozen=True, slots=True, kw_only=True)
class AttachmentBody:
    """子項目の本文を含まない、項目自身の順序付き原文本文。"""

    blocks: tuple[AttachmentBlock, ...] = ()
    text: AttachmentText | None = None

    def __post_init__(self) -> None:
        _require_items(
            self.blocks, (AttachmentParagraph, AttachmentTableBlock, AttachmentFigure)
        )
        _require(self.text, AttachmentText, optional=True)


# 添付文書自体: 改訂・原本の所在・掲載製品・項目階層


@dataclass(frozen=True, slots=True)
class AttachmentRevision:
    """添付文書の改訂情報。"""

    source_label: RevisionSourceLabel
    year_month: RevisionYearMonth
    version: RevisionVersion
    metadata: AttachmentMetadata = field(default_factory=AttachmentMetadata)

    def __post_init__(self) -> None:
        _require(self.source_label, RevisionSourceLabel)
        _require(self.year_month, RevisionYearMonth)
        _require(self.version, RevisionVersion)
        _require(self.metadata, AttachmentMetadata)


@dataclass(frozen=True, slots=True)
class AttachmentSource:
    """原本ファイルとPMDA公開先を表す値。"""

    pmda_url: AttachmentUrl
    sha256: AttachmentSha256 | None = None

    def __post_init__(self) -> None:
        _require(self.pmda_url, AttachmentUrl)
        _require(self.sha256, AttachmentSha256, optional=True)


@dataclass(frozen=True, slots=True)
class AttachmentProduct:
    """添付文書に記載された製品の値。"""

    product_code: AttachmentProductCode
    brand_name: AttachmentBrandName
    english_name: AttachmentEnglishName | None = None

    def __post_init__(self) -> None:
        _require(self.product_code, AttachmentProductCode)
        _require(self.brand_name, AttachmentBrandName)
        _require(self.english_name, AttachmentEnglishName, optional=True)


@dataclass(frozen=True, slots=True)
class AttachmentSection:
    """標準項目名と原文見出しを区別し、配下の項目を所有する。"""

    code: NumberedSectionCode
    title: AttachmentSectionTitle
    body: AttachmentBody | None = None
    header: AttachmentText | None = None
    children: tuple[AttachmentSection, ...] = ()

    def __post_init__(self) -> None:
        _require(self.code, NumberedSectionCode)
        _require(self.title, AttachmentSectionTitle)
        _require(self.body, AttachmentBody, optional=True)
        _require(self.header, AttachmentText, optional=True)
        _require_items(self.children, AttachmentSection)
        if any(child.parent_code != self.code for child in self.children):
            raise AttachmentDomainError(
                "section children must have the owning parent code"
            )

    def walk(self) -> tuple[AttachmentSection, ...]:
        """自身と配下を保存順に返す。"""
        return (self, *(section for child in self.children for section in child.walk()))

    @property
    def parent_code(self) -> NumberedSectionCode | None:
        """項目番号から導出した直接の親。"""
        return self.code.parent_code


@dataclass(frozen=True, slots=True, eq=False)
class AttachmentProductRevision(ImmutableMapping[JsonValue]):
    """医薬品情報の出典改訂。未知metadataを含む独立したスナップショット。"""

    def __post_init__(self) -> None:
        _require(self._data, Mapping)
        super().__post_init__()


@dataclass(frozen=True, slots=True)
class MedicineDocumentReference:
    """医薬品情報の出典となる添付文書参照。"""

    document_id: DocumentId
    pmda_url: PmdaUrl
    revision: AttachmentProductRevision

    def __post_init__(self) -> None:
        _require(self.document_id, DocumentId)
        _require(self.pmda_url, PmdaUrl)
        _require(self.revision, AttachmentProductRevision)
