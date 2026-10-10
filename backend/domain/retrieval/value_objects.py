"""検索コンテキストのValue Object。"""

from dataclasses import dataclass

from ..attachment.identifiers import DocumentId
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
)


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
