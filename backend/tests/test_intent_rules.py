"""Tests for fixed keyword intents and package insert section mappings."""

from __future__ import annotations

import unittest

from backend.domain.retrieval.services import detect_intent_from_keywords
from package_inserts.catalog_loader import get_package_insert_catalog


def get_section_codes_for_intent(intent: str) -> list[str] | None:
    codes = get_package_insert_catalog().section_codes_for_intent(intent)
    return list(codes) if codes else None


class IntentRuleTests(unittest.TestCase):
    def test_detect_intent_from_keywords(self) -> None:
        self.assertEqual(
            detect_intent_from_keywords(
                "副作用について教えて", catalog=get_package_insert_catalog()
            ),
            "adverse_events",
        )
        self.assertEqual(
            detect_intent_from_keywords(
                "1日何錠飲みますか？", catalog=get_package_insert_catalog()
            ),
            "dosage",
        )
        self.assertEqual(
            detect_intent_from_keywords(
                "併用しても大丈夫？", catalog=get_package_insert_catalog()
            ),
            "interaction",
        )
        self.assertEqual(
            detect_intent_from_keywords(
                "妊娠中に飲める？", catalog=get_package_insert_catalog()
            ),
            "pregnancy",
        )
        self.assertEqual(
            detect_intent_from_keywords(
                "薬のメカニズムは？", catalog=get_package_insert_catalog()
            ),
            "pharmacology",
        )
        self.assertEqual(
            detect_intent_from_keywords(
                "一般質問です", catalog=get_package_insert_catalog()
            ),
            "document_search",
        )

    def test_get_section_codes_for_intent(self) -> None:
        self.assertEqual(
            get_section_codes_for_intent("interaction"), ["10", "10.1", "10.2", "16.7"]
        )
        self.assertEqual(get_section_codes_for_intent("dosage"), ["6", "7"])
        self.assertEqual(get_section_codes_for_intent("warnings"), ["1"])
        self.assertIsNone(get_section_codes_for_intent("unknown_intent"))
