"""Jevの公開JSONと業務型の境界変換。"""

from copy import deepcopy

from ...application.retrieval.intent_contracts import IntentResult
from ...domain.foundation.json_types import JsonValue
from ...domain.retrieval.primitives import IntentName, Probability
from ...domain.retrieval.value_objects import IntentCandidate


def map_jev_intent_result(
    raw_response: dict[str, JsonValue] | None, *, is_available: bool = True
) -> IntentResult:
    if not is_available:
        return IntentResult(is_available=False)
    payload = deepcopy(raw_response)
    if not payload or "error" in payload:
        return IntentResult(is_available=True, raw_response=payload)
    answers = payload.get("answers")
    intent = answers.get("intent") if isinstance(answers, dict) else None
    selection = intent if isinstance(intent, dict) else {}
    choice = selection.get("choice")
    probabilities = selection.get("probabilities")
    items = probabilities.items() if isinstance(probabilities, dict) else ()
    return IntentResult(
        is_available=True,
        raw_response=payload,
        candidates=tuple(
            IntentCandidate(IntentName(name), Probability(probability))
            for name, probability in items
            if isinstance(probability, (int, float))
        ),
        choice=choice if isinstance(choice, str) else None,
        publish_selection=True,
    )
