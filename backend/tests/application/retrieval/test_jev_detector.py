from __future__ import annotations

import unittest

from backend.application.retrieval.intent_contracts import IntentRequest, IntentResult
from backend.application.retrieval.jev_detector import detect_jev_criteria
from backend.domain.foundation.json_types import JsonValue
from backend.domain.retrieval.services import select_intents
from backend.infrastructure.intent.jev_intent_mapping import map_jev_intent_result
from backend.infrastructure.package_insert_definitions.loader import (
    get_package_insert_definitions,
)


class FakeJevIntentClassifier:
    is_available = True

    def __init__(self, response: dict[str, JsonValue]) -> None:
        self.response = response

    async def classify(self, request: IntentRequest) -> IntentResult:
        return map_jev_intent_result(self.response)


class JevDetectorTests(unittest.IsolatedAsyncioTestCase):
    def test_resolves_sections_without_mutating_response(self) -> None:
        response: dict[str, JsonValue] = {
            "answers": {
                "intent": {
                    "choice": "dosage",
                    "probabilities": {"dosage": 0.8},
                }
            }
        }

        mapped = map_jev_intent_result(response)
        selection = select_intents(
            mapped.candidates,
            mapped.choice,
            intent_policy=get_package_insert_definitions().intent_policy,
        )
        primary, intents, sections = (
            selection.primary.value if selection.primary is not None else None,
            [intent.value for intent in selection.qualifying_intents],
            [code.value for code in selection.section_codes],
        )

        self.assertEqual(primary, "dosage")
        self.assertEqual(intents, ["dosage"])
        self.assertEqual(sections, ["6", "7"])
        self.assertNotIn("qualifying_intents", response)

    async def test_returns_search_criteria(self) -> None:
        response: dict[str, JsonValue] = {
            "answers": {
                "intent": {
                    "choice": "warnings",
                    "probabilities": {"warnings": 0.9},
                }
            }
        }

        result = await detect_jev_criteria(
            FakeJevIntentClassifier(response),
            IntentRequest("警告は？"),
            intent_policy=get_package_insert_definitions().intent_policy,
        )

        self.assertEqual(len(result.search_criteria), 1)
        self.assertEqual(result.search_criteria[0].source, "jev")
        self.assertEqual(
            tuple(code.value for code in result.search_criteria[0].section_codes),
            ("1",),
        )
        assert result.raw_response is not None
        self.assertEqual(result.raw_response["qualifying_intents"], ["warnings"])
        self.assertNotIn("qualifying_intents", response)
