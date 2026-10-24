"""意図判定の契約を用いた添付文書の検索条件生成。"""

from copy import deepcopy

from backend.application.retrieval.interfaces.intent_classifier import (
    IntentClassifier,
)
from backend.application.retrieval.queries.models import (
    IntentPolicy,
    IntentRequest,
    JevDetectionResult,
    SearchCriteria,
)
from backend.application.retrieval.queries.policies.selection import select_intents
from backend.application.retrieval.values import DetectionSource
from backend.domain.foundation.json_types import JsonValue


async def detect_jev_criteria(
    classifier: IntentClassifier,
    request: IntentRequest,
    *,
    intent_policy: IntentPolicy,
    baseline_intent: str | None = None,
) -> JevDetectionResult:
    """交換可能な意図判定の結果を添付文書検索の条件へ変換する。"""
    result = await classifier.classify(request)
    if not result.is_available:
        return JevDetectionResult()

    selection = select_intents(
        result.candidates,
        result.choice,
        intent_policy=intent_policy,
        baseline_intent=baseline_intent,
    )
    response_for_client = deepcopy(result.raw_response)
    if result.publish_selection and response_for_client is not None:
        response_for_client["qualifying_intents"] = list[JsonValue](
            intent.value for intent in selection.qualifying_intents
        )
    criteria = []
    if (
        selection.primary is not None
        and selection.primary.value
        and selection.primary.value != intent_policy.general_intent.value
        and selection.section_codes
    ):
        criteria.append(
            SearchCriteria(
                source=DetectionSource.JEV,
                intent=selection.primary,
                section_codes=selection.section_codes,
            )
        )
    return JevDetectionResult(
        criteria,
        response_for_client,
        tuple(intent.value for intent in selection.qualifying_intents),
    )
