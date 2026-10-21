"""Tests for fixed keyword intents and package insert section mappings."""

from __future__ import annotations

import unittest

from backend.application.retrieval.search_policy import detect_intents_from_keywords
from backend.infrastructure.package_insert_definitions.loader import (
    get_package_insert_definitions,
)


def get_section_codes_for_intent(intent: str) -> list[str] | None:
    codes = get_package_insert_definitions().intent_policy.section_codes_for_intent(
        intent
    )
    return list(codes) if codes else None


class IntentRuleTests(unittest.TestCase):
    def test_detect_intents_from_keywords(self) -> None:
        self.assertEqual(
            detect_intents_from_keywords(
                "副作用について教えて",
                intent_policy=get_package_insert_definitions().intent_policy,
            ),
            ("adverse_events", "indications"),
        )
        self.assertEqual(
            detect_intents_from_keywords(
                "1日何錠飲みますか？",
                intent_policy=get_package_insert_definitions().intent_policy,
            ),
            ("dosage",),
        )
        self.assertEqual(
            detect_intents_from_keywords(
                "併用しても大丈夫？",
                intent_policy=get_package_insert_definitions().intent_policy,
            ),
            ("interaction",),
        )
        self.assertEqual(
            detect_intents_from_keywords(
                "妊娠中に飲める？",
                intent_policy=get_package_insert_definitions().intent_policy,
            ),
            ("pregnancy",),
        )
        self.assertEqual(
            detect_intents_from_keywords(
                "薬のメカニズムは？",
                intent_policy=get_package_insert_definitions().intent_policy,
            ),
            ("pharmacology",),
        )
        self.assertEqual(
            detect_intents_from_keywords(
                "一般質問です",
                intent_policy=get_package_insert_definitions().intent_policy,
            ),
            (),
        )

    def test_get_section_codes_for_intent(self) -> None:
        self.assertEqual(
            get_section_codes_for_intent("interaction"), ["10", "10.1", "10.2", "16.7"]
        )
        self.assertEqual(get_section_codes_for_intent("dosage"), ["6", "7"])
        self.assertEqual(get_section_codes_for_intent("warnings"), ["1"])
        self.assertIsNone(get_section_codes_for_intent("unknown_intent"))
