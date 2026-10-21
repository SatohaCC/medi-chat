"""根拠取得ユースケースの出力。"""

from dataclasses import dataclass, field

from backend.application.medicine.product_models import ResolvedMedicine
from backend.application.retrieval.search_models import (
    Evidence,
)

from ...domain.foundation.json_types import JsonValue


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
