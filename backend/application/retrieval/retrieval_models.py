"""根拠取得ユースケースの出力。"""

from dataclasses import dataclass, field

from backend.application.medicine.product_models import ResolvedMedicine

from ...domain.attachment.identifiers import DocumentId
from ...domain.foundation.json_types import JsonValue
from ...domain.retrieval.identifiers import SearchUnitId
from ...domain.retrieval.primitives import DetectionSource
from ...domain.retrieval.value_objects import (
    DocumentRevision,
    Evidence,
    EvidenceColumns,
    EvidenceReference,
    EvidenceSection,
    IntentPolicy,
)


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


__all__ = [
    "DetectionSource",
    "DocumentId",
    "DocumentRevision",
    "Evidence",
    "EvidenceColumns",
    "EvidenceReference",
    "EvidenceSection",
    "IntentPolicy",
    "RetrievalResult",
    "SearchUnitId",
]
