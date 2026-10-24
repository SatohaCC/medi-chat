"""外部技術に依存しない意図判定の契約。"""

from typing import Protocol

from backend.application.retrieval.queries.models import IntentRequest, IntentResult


class IntentClassifier(Protocol):
    """意図判定を交換するためのport。"""

    async def classify(self, request: IntentRequest) -> IntentResult:
        raise NotImplementedError
