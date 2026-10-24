from __future__ import annotations

from dataclasses import dataclass, field

from backend.application.indexing.queries.models import DocumentRevision
from backend.application.indexing.values import (
    SearchSectionCode,
    SearchUnitId,
    SearchUnitKind,
)
from backend.application.medicine.queries.models import ResolvedMedicine
from backend.application.retrieval.values import (
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
    SearchKeyword,
    SearchPolicyTerm,
)
from backend.domain.attachment.identifiers import DocumentId
from backend.domain.foundation.exceptions import DomainValidationError
from backend.domain.foundation.json_types import JsonValue
from backend.domain.foundation.value_objects import ImmutableMapping
from backend.domain.medicine.identifiers import YjCode


@dataclass(frozen=True, slots=True, kw_only=True)
class IntentKeyword:
    text: IntentKeywordText
    exclude_from_text_search: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class SearchIntentDefinition:
    id: IntentName
    section_codes: tuple[SearchSectionCode, ...]
    keywords: tuple[IntentKeyword, ...]
    keyword_priority: KeywordPriority | None

    def __post_init__(self) -> None:
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


@dataclass(frozen=True, slots=True, kw_only=True)
class TextSearchPolicy:
    stop_words: frozenset[SearchPolicyTerm]
    symptom_rules: tuple[SymptomKeywordRule, ...]
    scope_heading_texts: frozenset[SearchPolicyTerm]


@dataclass(frozen=True, slots=True)
class SearchCriteria:
    """常時取得または質問の判定器が作る、添付文書検索の条件。"""

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


@dataclass
class RetrievalResult:
    """チャットやLLMに依存しない検索結果。"""

    intent: str
    retrieval_strategy: str
    resolved_medicines: list[ResolvedMedicine] = field(default_factory=list)
    sources: list[Evidence] = field(default_factory=list)
    needs_clarification: bool = False
    notices: list[str] = field(default_factory=list)
    jev_response: dict[str, JsonValue] | None = None
    qualifying_intents: tuple[str, ...] = ()


@dataclass
class IntentRequest:
    """意図を判定する質問と薬剤文脈。"""

    question: str
    medicines: tuple[ResolvedMedicine, ...] = ()


@dataclass
class IntentResult:
    """型付き候補が業務契約。raw_responseは解釈しない公開原本。"""

    is_available: bool
    raw_response: dict[str, JsonValue] | None = None
    candidates: tuple[IntentCandidate, ...] = ()
    choice: str | None = None
    publish_selection: bool = False


@dataclass
class JevDetectionResult:
    """検索条件と利用側へ返す純粋な判定情報。"""

    search_criteria: list[SearchCriteria] = field(default_factory=list)
    raw_response: dict[str, JsonValue] | None = None
    qualifying_intents: tuple[str, ...] = ()
