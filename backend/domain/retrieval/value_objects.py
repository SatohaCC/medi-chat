"""検索コンテキストのValue Object。"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, field

from ..attachment.identifiers import DocumentId, DocumentVersionId
from ..foundation.exceptions import DomainValidationError
from ..foundation.value_objects import ImmutableMapping
from ..json_types import JsonValue
from ..medicine.identifiers import YjCode
from .identifiers import SearchUnitId
from .primitives import (
    DetectionSource,
    EvidenceBrandName,
    EvidenceGenericName,
    EvidenceSourceUrl,
    IntentName,
    Probability,
    SearchKeyword,
    SearchSectionCode,
    SearchUnitProductCode,
    SearchUnitSectionCode,
    SearchUnitText,
)


@dataclass(frozen=True, slots=True, kw_only=True)
class IntentKeyword:
    text: str
    exclude_from_text_search: bool

    def __post_init__(self) -> None:
        if not self.text.strip():
            raise DomainValidationError("intent keyword must be nonempty")


@dataclass(frozen=True, slots=True, kw_only=True)
class SearchIntentDefinition:
    id: IntentName
    section_codes: tuple[SearchSectionCode, ...]
    keywords: tuple[IntentKeyword, ...]
    keyword_priority: int | None

    def __post_init__(self) -> None:
        if len(self.section_codes) != len(set(self.section_codes)):
            raise DomainValidationError("duplicate search section")
        if self.keywords and (
            not self.section_codes
            or self.keyword_priority is None
            or self.keyword_priority < 1
        ):
            raise DomainValidationError("keyword intent requires sections and priority")
        if not self.keywords and self.keyword_priority is not None:
            raise DomainValidationError("keyword priority requires keywords")


@dataclass(frozen=True, slots=True, kw_only=True)
class IntentPolicy:
    intents: tuple[SearchIntentDefinition, ...]
    fallback_intent: IntentName
    general_intent: IntentName

    def __post_init__(self) -> None:
        names = tuple(intent.id for intent in self.intents)
        if len(names) != len(set(names)) or self.fallback_intent == self.general_intent:
            raise DomainValidationError("intent definitions must be distinct")
        for name in (self.fallback_intent, self.general_intent):
            if name not in names or any(
                intent.section_codes for intent in self.intents if intent.id == name
            ):
                raise DomainValidationError(
                    "fallback/general intent must exist without sections"
                )
        priorities = tuple(
            intent.keyword_priority for intent in self.intents if intent.keywords
        )
        keywords = tuple(
            keyword.text for intent in self.intents for keyword in intent.keywords
        )
        if len(priorities) != len(set(priorities)) or len(keywords) != len(
            set(keywords)
        ):
            raise DomainValidationError("duplicate keyword or priority")

    @property
    def keyword_intents(self) -> tuple[SearchIntentDefinition, ...]:
        return tuple(
            sorted(
                (intent for intent in self.intents if intent.keywords),
                key=lambda intent: intent.keyword_priority or 0,
            )
        )

    def section_codes_for_intent(self, intent_id: str) -> tuple[str, ...]:
        return next(
            (
                tuple(code.value for code in intent.section_codes)
                for intent in self.intents
                if intent.id.value == intent_id
            ),
            (),
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class TextSearchPolicy:
    stop_words: frozenset[str]
    symptom_keywords_by_adjective: Mapping[str, tuple[str, ...]]
    scope_heading_texts: frozenset[str]


@dataclass(frozen=True, slots=True, kw_only=True)
class SearchDocumentVersion:
    document_id: DocumentId
    version_id: DocumentVersionId

    def __post_init__(self) -> None:
        prefix = f"{self.document_id}:"
        if (
            not self.version_id.value.startswith(prefix)
            or re.fullmatch(r"[0-9a-f]{64}", self.version_id.value[len(prefix) :])
            is None
        ):
            raise DomainValidationError(
                "search version must identify this document and its source SHA256"
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class VersionSearchIdentity(SearchDocumentVersion):
    section_code: SearchUnitSectionCode

    @property
    def unit_id(self) -> SearchUnitId:
        return SearchUnitId(f"{self.version_id}:{self.section_code}")


@dataclass(frozen=True, slots=True, kw_only=True)
class SearchContentContext:
    product_codes: tuple[SearchUnitProductCode, ...] = ()
    labels: tuple[SearchUnitText, ...] = ()


@dataclass(frozen=True, slots=True, kw_only=True)
class SearchContentReference:
    label: SearchUnitText
    target_id: SearchUnitText | None = None
    metadata: EvidenceReference = field(default_factory=lambda: EvidenceReference())


@dataclass(frozen=True, slots=True, kw_only=True)
class SearchTableCell:
    text: SearchUnitText
    column: int
    rowspan: int
    colspan: int
    references: tuple[SearchContentReference, ...] = ()
    context: SearchContentContext = field(default_factory=SearchContentContext)


@dataclass(frozen=True, slots=True, kw_only=True)
class SearchTable:
    columns: tuple[SearchUnitText, ...]
    rows: tuple[tuple[SearchTableCell, ...], ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class SearchParagraph:
    text: SearchUnitText
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


type SearchContentBlock = SearchParagraph | SearchTableBlock | SearchFigure


@dataclass(frozen=True, slots=True)
class SearchCriteria:
    """3つの判定器が作る、添付文書検索の条件。"""

    source: DetectionSource
    intent: IntentName | None = None
    section_codes: tuple[SearchSectionCode, ...] = ()
    keywords: tuple[SearchKeyword, ...] = ()


@dataclass(frozen=True, slots=True)
class IntentCandidate:
    """外部判定結果から取り出した意図と確率。"""

    intent: IntentName
    probability: Probability


@dataclass(frozen=True, slots=True)
class IntentSelection:
    """候補から業務上採用した意図と検索項目。"""

    primary: IntentName | None = None
    qualifying_intents: tuple[IntentName, ...] = ()
    section_codes: tuple[SearchSectionCode, ...] = ()


@dataclass(frozen=True, slots=True, eq=False)
class DocumentRevision(ImmutableMapping[JsonValue]):
    """根拠に含める原本の改訂情報。未知metadataも保持する。"""


@dataclass(frozen=True, slots=True, eq=False)
class EvidenceReference(ImmutableMapping[JsonValue]):
    """原文の参照と未知metadataを保持する値。"""


@dataclass(frozen=True, slots=True, eq=False)
class EvidenceSection(ImmutableMapping[str]):
    """原文の項目番号・見出しを形式制限なしで保持する値。"""


@dataclass(frozen=True, slots=True, eq=False)
class EvidenceColumns(ImmutableMapping[str]):
    """表の原文列を保持する値。"""


@dataclass(frozen=True, slots=True)
class EvidenceProduct:
    """根拠の表示に使う製品のスナップショット。"""

    yj_code: YjCode | None
    brand_name: EvidenceBrandName | None = None


@dataclass(frozen=True, slots=True)
class EvidenceDocument:
    """根拠の表示に使う文書のスナップショット。"""

    generic_name: EvidenceGenericName | None
    products: tuple[EvidenceProduct, ...]
    pmda_url: EvidenceSourceUrl | None = None


@dataclass(frozen=True, slots=True)
class SearchUnitCriteria:
    """項目・製品で検索単位を絞る、順序に意味を持たない条件。"""

    section_codes: frozenset[SearchUnitSectionCode] = frozenset()
    product_codes: frozenset[SearchUnitProductCode] = frozenset()


@dataclass(frozen=True, slots=True, kw_only=True)
class Evidence:
    """回答に使う原文・出典・取得経路の不変なスナップショット。"""

    unit_id: SearchUnitId
    document_id: DocumentId
    product_name: str
    generic_name: str
    product_yj_codes: tuple[YjCode, ...]
    document_revision: DocumentRevision
    section: EvidenceSection
    kind: str
    excerpt: str
    url: str
    columns: EvidenceColumns | None = None
    references: tuple[EvidenceReference, ...] = ()
    retrieved_by: frozenset[DetectionSource] = frozenset()

    def to_dict(self) -> dict[str, JsonValue]:
        """公開境界へ渡す、内部値から独立したJSON情報。"""
        return {
            "unit_id": self.unit_id.value,
            "document_id": self.document_id.value,
            "product_name": self.product_name,
            "generic_name": self.generic_name,
            "product_yj_codes": [code.value for code in self.product_yj_codes],
            "document_revision": dict(self.document_revision),
            "section": dict(self.section),
            "kind": self.kind,
            "excerpt": self.excerpt,
            "columns": dict(self.columns) if self.columns is not None else None,
            "references": [dict(ref) for ref in self.references],
            "url": self.url,
            "retrieved_by": [
                source.value
                for source in DetectionSource
                if source in self.retrieved_by
            ],
        }
