"""検索コンテキストのValue Object。"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field

from ..attachment.identifiers import DocumentId
from ..foundation.exceptions import DomainValidationError
from ..foundation.json_types import JsonValue
from ..foundation.value_objects import ImmutableMapping
from ..medicine.identifiers import YjCode
from .identifiers import SearchUnitId
from .primitives import (
    DetectionSource,
    EvidenceBrandName,
    EvidenceExcerpt,
    EvidenceGenericName,
    EvidenceProductName,
    EvidenceSourceUrl,
    IntentKeywordText,
    IntentName,
    KeywordPriority,
    Probability,
    SearchCellSpan,
    SearchColumnIndex,
    SearchKeyword,
    SearchPolicyTerm,
    SearchSectionCode,
    SearchUnitKind,
    SearchUnitProductCode,
    SearchUnitSectionCode,
    SearchUnitText,
)


def _require(
    value: object, expected: type | tuple[type, ...], *, optional: bool = False
) -> None:
    if optional and value is None:
        return
    if not isinstance(value, expected):
        raise DomainValidationError(
            f"invalid retrieval field type: expected {expected}"
        )


def _require_items(
    values: object, item_type: type | tuple[type, ...], container: type = tuple
) -> None:
    if not isinstance(values, container):
        raise DomainValidationError(f"expected immutable {container.__name__}")
    if not isinstance(values, Iterable):
        raise DomainValidationError("collection must be iterable")
    for item in values:
        _require(item, item_type)


@dataclass(frozen=True, slots=True, kw_only=True)
class IntentKeyword:
    text: IntentKeywordText
    exclude_from_text_search: bool

    def __post_init__(self) -> None:
        _require(self.exclude_from_text_search, bool)
        if not isinstance(self.text, IntentKeywordText):
            raise DomainValidationError("intent keyword requires IntentKeywordText")


@dataclass(frozen=True, slots=True, kw_only=True)
class SearchIntentDefinition:
    id: IntentName
    section_codes: tuple[SearchSectionCode, ...]
    keywords: tuple[IntentKeyword, ...]
    keyword_priority: KeywordPriority | None

    def __post_init__(self) -> None:
        _require(self.id, IntentName)
        _require_items(self.section_codes, SearchSectionCode)
        _require_items(self.keywords, IntentKeyword)
        _require(self.keyword_priority, KeywordPriority, optional=True)
        if len(self.section_codes) != len(set(self.section_codes)):
            raise DomainValidationError("duplicate search section")
        if self.keywords and (not self.section_codes or self.keyword_priority is None):
            raise DomainValidationError("keyword intent requires sections and priority")
        if not self.keywords and self.keyword_priority is not None:
            raise DomainValidationError("keyword priority requires keywords")


@dataclass(frozen=True, slots=True, kw_only=True)
class IntentPolicy:
    intents: tuple[SearchIntentDefinition, ...]
    fallback_intent: IntentName
    general_intent: IntentName

    def __post_init__(self) -> None:
        _require_items(self.intents, SearchIntentDefinition)
        _require(self.fallback_intent, IntentName)
        _require(self.general_intent, IntentName)
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
            keyword.text.value for intent in self.intents for keyword in intent.keywords
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
                key=lambda intent: (
                    intent.keyword_priority.value
                    if intent.keyword_priority is not None
                    else 0
                ),
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
class SymptomKeywordRule:
    adjective: SearchPolicyTerm
    keywords: tuple[SearchPolicyTerm, ...]

    def __post_init__(self) -> None:
        _require(self.adjective, SearchPolicyTerm)
        _require_items(self.keywords, SearchPolicyTerm)


@dataclass(frozen=True, slots=True, kw_only=True)
class TextSearchPolicy:
    stop_words: frozenset[SearchPolicyTerm]
    symptom_rules: tuple[SymptomKeywordRule, ...]
    scope_heading_texts: frozenset[SearchPolicyTerm]

    def __post_init__(self) -> None:
        _require_items(self.stop_words, SearchPolicyTerm, frozenset)
        _require_items(self.symptom_rules, SymptomKeywordRule)
        _require_items(self.scope_heading_texts, SearchPolicyTerm, frozenset)


@dataclass(frozen=True, slots=True, kw_only=True)
class SearchContentContext:
    product_codes: tuple[SearchUnitProductCode, ...] = ()
    labels: tuple[SearchUnitText, ...] = ()
    section_code: SearchUnitSectionCode | None = None
    section_title: SearchUnitText | None = None

    def __post_init__(self) -> None:
        _require_items(self.product_codes, SearchUnitProductCode)
        _require_items(self.labels, SearchUnitText)
        _require(self.section_code, SearchUnitSectionCode, optional=True)
        _require(self.section_title, SearchUnitText, optional=True)


@dataclass(frozen=True, slots=True, kw_only=True)
class SearchContentReference:
    label: SearchUnitText
    target_id: SearchUnitText | None = None
    metadata: EvidenceReference = field(default_factory=lambda: EvidenceReference())

    def __post_init__(self) -> None:
        _require(self.label, SearchUnitText)
        _require(self.target_id, SearchUnitText, optional=True)
        _require(self.metadata, EvidenceReference)


@dataclass(frozen=True, slots=True, kw_only=True)
class SearchTableCell:
    text: SearchUnitText
    column: SearchColumnIndex
    rowspan: SearchCellSpan
    colspan: SearchCellSpan
    references: tuple[SearchContentReference, ...] = ()
    context: SearchContentContext = field(default_factory=SearchContentContext)

    def __post_init__(self) -> None:
        _require(self.text, SearchUnitText)
        _require(self.column, SearchColumnIndex)
        _require(self.rowspan, SearchCellSpan)
        _require(self.colspan, SearchCellSpan)
        _require_items(self.references, SearchContentReference)
        _require(self.context, SearchContentContext)


@dataclass(frozen=True, slots=True, kw_only=True)
class SearchTable:
    columns: tuple[SearchUnitText, ...]
    rows: tuple[tuple[SearchTableCell, ...], ...]

    def __post_init__(self) -> None:
        _require_items(self.columns, SearchUnitText)
        _require_items(self.rows, tuple)
        for row in self.rows:
            _require_items(row, SearchTableCell)


@dataclass(frozen=True, slots=True, kw_only=True)
class SearchParagraph:
    text: SearchUnitText
    is_heading: bool = False
    context: SearchContentContext
    references: tuple[SearchContentReference, ...] = ()

    def __post_init__(self) -> None:
        _require(self.text, SearchUnitText)
        _require(self.is_heading, bool)
        _require(self.context, SearchContentContext)
        _require_items(self.references, SearchContentReference)


@dataclass(frozen=True, slots=True, kw_only=True)
class SearchTableBlock:
    table: SearchTable
    context: SearchContentContext
    references: tuple[SearchContentReference, ...] = ()

    def __post_init__(self) -> None:
        _require(self.table, SearchTable)
        _require(self.context, SearchContentContext)
        _require_items(self.references, SearchContentReference)


@dataclass(frozen=True, slots=True, kw_only=True)
class SearchFigure:
    reference: SearchUnitText
    description: SearchUnitText
    context: SearchContentContext
    references: tuple[SearchContentReference, ...] = ()

    def __post_init__(self) -> None:
        _require(self.reference, SearchUnitText)
        _require(self.description, SearchUnitText)
        _require(self.context, SearchContentContext)
        _require_items(self.references, SearchContentReference)


type SearchContentBlock = SearchParagraph | SearchTableBlock | SearchFigure


@dataclass(frozen=True, slots=True)
class SearchCriteria:
    """3つの判定器が作る、添付文書検索の条件。"""

    source: DetectionSource
    intent: IntentName | None = None
    section_codes: tuple[SearchSectionCode, ...] = ()
    keywords: tuple[SearchKeyword, ...] = ()

    def __post_init__(self) -> None:
        _require(self.source, DetectionSource)
        _require(self.intent, IntentName, optional=True)
        _require_items(self.section_codes, SearchSectionCode)
        _require_items(self.keywords, SearchKeyword)


@dataclass(frozen=True, slots=True)
class IntentCandidate:
    """外部判定結果から取り出した意図と確率。"""

    intent: IntentName
    probability: Probability

    def __post_init__(self) -> None:
        _require(self.intent, IntentName)
        _require(self.probability, Probability)


@dataclass(frozen=True, slots=True)
class IntentSelection:
    """候補から業務上採用した意図と検索項目。"""

    primary: IntentName | None = None
    qualifying_intents: tuple[IntentName, ...] = ()
    section_codes: tuple[SearchSectionCode, ...] = ()

    def __post_init__(self) -> None:
        _require(self.primary, IntentName, optional=True)
        _require_items(self.qualifying_intents, IntentName)
        _require_items(self.section_codes, SearchSectionCode)


@dataclass(frozen=True, slots=True, eq=False)
class DocumentRevision(ImmutableMapping[JsonValue]):
    """根拠に含める原本の改訂情報。未知metadataも保持する。"""

    def __post_init__(self) -> None:
        _require(self._data, Mapping)
        super().__post_init__()


@dataclass(frozen=True, slots=True, eq=False)
class EvidenceReference(ImmutableMapping[JsonValue]):
    """原文の参照と未知metadataを保持する値。"""

    def __post_init__(self) -> None:
        _require(self._data, Mapping)
        super().__post_init__()


@dataclass(frozen=True, slots=True, eq=False)
class EvidenceSection(ImmutableMapping[str]):
    """原文の項目番号・見出しを形式制限なしで保持する値。"""

    def __post_init__(self) -> None:
        _require(self._data, Mapping)
        if any(
            not isinstance(key, str) or not isinstance(value, str)
            for key, value in self._data.items()
        ):
            raise DomainValidationError(
                "evidence mapping requires string keys and values"
            )
        super().__post_init__()


@dataclass(frozen=True, slots=True, eq=False)
class EvidenceColumns(ImmutableMapping[str]):
    """表の原文列を保持する値。"""

    def __post_init__(self) -> None:
        _require(self._data, Mapping)
        if any(
            not isinstance(key, str) or not isinstance(value, str)
            for key, value in self._data.items()
        ):
            raise DomainValidationError(
                "evidence mapping requires string keys and values"
            )
        super().__post_init__()


@dataclass(frozen=True, slots=True)
class EvidenceProduct:
    """根拠の表示に使う製品のスナップショット。"""

    yj_code: YjCode | None
    brand_name: EvidenceBrandName | None = None

    def __post_init__(self) -> None:
        _require(self.yj_code, YjCode, optional=True)
        _require(self.brand_name, EvidenceBrandName, optional=True)


@dataclass(frozen=True, slots=True)
class EvidenceDocument:
    """根拠の表示に使う文書のスナップショット。"""

    generic_name: EvidenceGenericName | None
    products: tuple[EvidenceProduct, ...]
    pmda_url: EvidenceSourceUrl | None = None

    def __post_init__(self) -> None:
        _require(self.generic_name, EvidenceGenericName, optional=True)
        _require_items(self.products, EvidenceProduct)
        _require(self.pmda_url, EvidenceSourceUrl, optional=True)


@dataclass(frozen=True, slots=True, kw_only=True)
class Evidence:
    """回答に使う原文・出典・取得経路の不変なスナップショット。"""

    unit_id: SearchUnitId
    document_id: DocumentId
    product_name: EvidenceProductName | None
    generic_name: EvidenceGenericName | None
    product_yj_codes: tuple[YjCode, ...]
    document_revision: DocumentRevision
    section: EvidenceSection
    kind: SearchUnitKind | None
    excerpt: EvidenceExcerpt
    url: EvidenceSourceUrl | None
    columns: EvidenceColumns | None = None
    references: tuple[EvidenceReference, ...] = ()
    retrieved_by: frozenset[DetectionSource] = frozenset()

    def __post_init__(self) -> None:
        _require(self.unit_id, SearchUnitId)
        _require(self.document_id, DocumentId)
        _require(self.product_name, EvidenceProductName, optional=True)
        _require(self.generic_name, EvidenceGenericName, optional=True)
        _require_items(self.product_yj_codes, YjCode)
        _require(self.document_revision, DocumentRevision)
        _require(self.section, EvidenceSection)
        _require(self.kind, SearchUnitKind, optional=True)
        _require(self.excerpt, EvidenceExcerpt)
        _require(self.url, EvidenceSourceUrl, optional=True)
        _require(self.columns, EvidenceColumns, optional=True)
        _require_items(self.references, EvidenceReference)
        _require_items(self.retrieved_by, DetectionSource, frozenset)

    def to_dict(self) -> dict[str, JsonValue]:
        """公開境界へ渡す、内部値から独立したJSON情報。"""
        return {
            "unit_id": self.unit_id.value,
            "document_id": self.document_id.value,
            "product_name": self.product_name.value
            if self.product_name is not None
            else "",
            "generic_name": self.generic_name.value
            if self.generic_name is not None
            else "",
            "product_yj_codes": [code.value for code in self.product_yj_codes],
            "document_revision": dict(self.document_revision),
            "section": dict(self.section),
            "kind": self.kind.value if self.kind is not None else "",
            "excerpt": self.excerpt.value,
            "columns": dict(self.columns) if self.columns is not None else None,
            "references": [dict(ref) for ref in self.references],
            "url": self.url.value if self.url is not None else "",
            "retrieved_by": [
                source.value
                for source in DetectionSource
                if source in self.retrieved_by
            ],
        }
