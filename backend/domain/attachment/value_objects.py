"""添付文書ドメインの不変Value Object。

AttachmentRevision / Source / Product / Section は添付文書自体の構造を表す。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from ..foundation.value_objects import ImmutableMapping
from ..json_types import JsonValue
from ..medicine.identifiers import YjCode
from .exceptions import AttachmentDomainError, MissingOrInvalidYjError
from .identifiers import ArtifactFileId, DocumentId, DocumentVersionId
from .primitives import (
    AttachmentBrandName,
    AttachmentCellSpan,
    AttachmentColumnIndex,
    AttachmentEnglishName,
    AttachmentProductCode,
    AttachmentSectionTitle,
    AttachmentSha256,
    AttachmentText,
    AttachmentUrl,
    DefinitionTitle,
    InteractionColumnId,
    NumberedSectionCode,
    RegistrationSequence,
    RevisionSourceLabel,
    RevisionVersion,
    RevisionYearMonth,
)

if TYPE_CHECKING:
    from .entities import AttachmentRegistration


@dataclass(frozen=True, slots=True, kw_only=True)
class SectionDefinition:
    code: NumberedSectionCode
    title: DefinitionTitle


@dataclass(frozen=True, slots=True, kw_only=True)
class SectionTaxonomy:
    sections: tuple[SectionDefinition, ...]

    def __post_init__(self) -> None:
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


@dataclass(frozen=True, slots=True, kw_only=True)
class RegistrationVersion:
    document_id: DocumentId
    source_sha256: AttachmentSha256
    yj_codes: frozenset[YjCode]
    owned_file_ids: frozenset[ArtifactFileId] = frozenset()

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
            or any(
                not isinstance(code, YjCode)
                or re.fullmatch(r"[0-9A-Z]{12}", code.value) is None
                for code in self.yj_codes
            )
        ):
            raise MissingOrInvalidYjError("missing_or_invalid_yj")
        if not isinstance(self.owned_file_ids, frozenset) or any(
            not isinstance(file_id, ArtifactFileId) for file_id in self.owned_file_ids
        ):
            raise AttachmentDomainError(
                "owned file identities must be an immutable set"
            )

    @property
    def version_id(self) -> DocumentVersionId:
        return DocumentVersionId(f"{self.document_id}:{self.source_sha256}")


@dataclass(frozen=True, slots=True)
class ActiveRegistration:
    yj_code: YjCode
    version_id: DocumentVersionId


@dataclass(frozen=True, slots=True, kw_only=True)
class RegistrationReceipt:
    version: RegistrationVersion
    sequence: RegistrationSequence
    replaced_yj_codes: frozenset[YjCode]
    artifacts_deleted: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.sequence, RegistrationSequence):
            raise AttachmentDomainError("receipt sequence must be typed")
        if (
            not isinstance(self.replaced_yj_codes, frozenset)
            or not self.replaced_yj_codes <= self.version.yj_codes
        ):
            raise AttachmentDomainError(
                "replaced YJ codes must be an immutable subset of input products"
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class RegistrationProposal:
    """非公開の置換案。採用されるまで元snapshotを変更しない。"""

    before: AttachmentRegistration
    after: AttachmentRegistration
    receipt: RegistrationReceipt
    reused: bool


def _require_tuples(*values: object) -> None:
    if any(not isinstance(value, tuple) for value in values):
        raise AttachmentDomainError("content collections must be tuples")


@dataclass(frozen=True, slots=True, kw_only=True)
class AttachmentReferenceTarget:
    """原文内で参照可能な要素。タグや保存形式には依存しない。"""

    reference_id: AttachmentText
    text: AttachmentText
    context: AttachmentContext = field(default_factory=lambda: AttachmentContext())


@dataclass(frozen=True, slots=True, eq=False)
class AttachmentMetadata(ImmutableMapping[JsonValue]):
    """原本の未知metadataも失わない独立した値。"""


@dataclass(frozen=True, slots=True, kw_only=True)
class AttachmentContext:
    """原文の適用対象と文脈の順序。"""

    product_codes: tuple[AttachmentProductCode, ...] = ()
    labels: tuple[AttachmentText, ...] = ()

    def __post_init__(self) -> None:
        _require_tuples(self.product_codes, self.labels)


@dataclass(frozen=True, slots=True, kw_only=True)
class AttachmentReference:
    """本文中の参照表示と原文内の参照先。"""

    label: AttachmentText
    target_id: AttachmentText | None = None
    metadata: AttachmentMetadata = field(default_factory=AttachmentMetadata)


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
        _require_tuples(self.references)


@dataclass(frozen=True, slots=True, kw_only=True)
class AttachmentTable:
    """列と行の対応を保つ原文表。"""

    columns: tuple[AttachmentText, ...]
    rows: tuple[tuple[AttachmentTableCell, ...], ...]
    column_contexts: tuple[AttachmentContext, ...] = ()

    def __post_init__(self) -> None:
        _require_tuples(self.columns, self.rows, self.column_contexts, *self.rows)
        if self.column_contexts and len(self.column_contexts) != len(self.columns):
            raise AttachmentDomainError("table column contexts must match headings")


@dataclass(frozen=True, slots=True, kw_only=True)
class AttachmentParagraph:
    text: AttachmentText
    context: AttachmentContext = field(default_factory=AttachmentContext)
    references: tuple[AttachmentReference, ...] = ()

    def __post_init__(self) -> None:
        _require_tuples(self.references)


@dataclass(frozen=True, slots=True, kw_only=True)
class AttachmentTableBlock:
    table: AttachmentTable
    context: AttachmentContext = field(default_factory=AttachmentContext)
    references: tuple[AttachmentReference, ...] = ()

    def __post_init__(self) -> None:
        _require_tuples(self.references)


@dataclass(frozen=True, slots=True, kw_only=True)
class AttachmentFigure:
    reference: AttachmentText
    description: AttachmentText
    context: AttachmentContext = field(default_factory=AttachmentContext)
    references: tuple[AttachmentReference, ...] = ()

    def __post_init__(self) -> None:
        _require_tuples(self.references)


type AttachmentBlock = AttachmentParagraph | AttachmentTableBlock | AttachmentFigure


@dataclass(frozen=True, slots=True, kw_only=True)
class AttachmentBody:
    """子項目の本文を含まない、項目自身の順序付き原文本文。"""

    blocks: tuple[AttachmentBlock, ...] = ()
    text: AttachmentText | None = None

    def __post_init__(self) -> None:
        _require_tuples(self.blocks)


# 添付文書自体: 改訂・原本の所在・掲載製品・項目階層


@dataclass(frozen=True, slots=True)
class AttachmentRevision:
    """添付文書の改訂情報。"""

    source_label: RevisionSourceLabel
    year_month: RevisionYearMonth
    version: RevisionVersion
    metadata: AttachmentMetadata = field(default_factory=AttachmentMetadata)


@dataclass(frozen=True, slots=True)
class AttachmentSource:
    """原本ファイルとPMDA公開先を表す値。"""

    pmda_url: AttachmentUrl
    sha256: AttachmentSha256 | None = None


@dataclass(frozen=True, slots=True)
class AttachmentProduct:
    """添付文書に記載された製品の値。"""

    product_code: AttachmentProductCode
    brand_name: AttachmentBrandName
    english_name: AttachmentEnglishName | None = None


@dataclass(frozen=True, slots=True)
class AttachmentSection:
    """添付文書の項目番号と正式名称。"""

    code: NumberedSectionCode
    title: AttachmentSectionTitle
    body: AttachmentBody | None = None

    @property
    def parent_code(self) -> NumberedSectionCode | None:
        """項目番号から導出した直接の親。"""
        return self.code.parent_code


@dataclass(frozen=True, slots=True, eq=False)
class AttachmentProductRevision(ImmutableMapping[JsonValue]):
    """医薬品情報の出典改訂。未知metadataを含む独立したスナップショット。"""


@dataclass(frozen=True, slots=True)
class AttachmentProductMatch:
    """照合・特定された医薬品情報。識別子を持つ製品Entityの投影値。"""

    generic_name: str
    brand_names: tuple[str, ...]
    yj_codes: tuple[str, ...]
    document_ids: tuple[str, ...]
    matched_aliases: tuple[str, ...] = ()
