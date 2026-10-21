"""意図判定の契約を用いた添付文書の検索条件生成。"""

from copy import deepcopy
from dataclasses import dataclass, field

from backend.application.retrieval.search_models import IntentPolicy, SearchCriteria
from backend.application.retrieval.search_policy import select_intents
from backend.application.retrieval.search_values import DetectionSource

from ...domain.foundation.json_types import JsonValue
from .intent_contracts import IntentClassifier, IntentRequest


@dataclass
class JevDetectionResult:
    """検索条件と利用側へ返す純粋な判定情報。"""

    search_criteria: list[SearchCriteria] = field(default_factory=list)
    raw_response: dict[str, JsonValue] | None = None
    qualifying_intents: tuple[str, ...] = ()


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
