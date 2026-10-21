"""外部技術に依存しない意図判定の契約。"""

from dataclasses import dataclass
from typing import Protocol

from backend.application.medicine.product_models import ResolvedMedicine
from backend.application.retrieval.search_models import IntentCandidate

from ...domain.foundation.json_types import JsonValue


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


class IntentClassifier(Protocol):
    """意図判定を交換するためのport。"""

    async def classify(self, request: IntentRequest) -> IntentResult:
        raise NotImplementedError
