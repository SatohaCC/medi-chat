from __future__ import annotations

import unittest

from backend.application.retrieval.morphology_detector import detect_morphology_criteria
from backend.application.retrieval.search_policy import detect_fixed_keyword_criteria
from backend.infrastructure.morphology.janome_keyword_extractor import (
    JanomeKeywordExtractor,
)
from backend.infrastructure.package_insert_definitions.assembly import (
    get_package_insert_definitions,
)


class SearchDetectorTests(unittest.TestCase):
    def test_fixed_keyword_detector_returns_section_codes(self) -> None:
        target = detect_fixed_keyword_criteria(
            "副作用について教えて", get_package_insert_definitions().intent_policy
        )

        self.assertEqual(
            {item.intent.value for item in target if item.intent is not None},
            {"adverse_events", "indications"},
        )
        target = next(
            item
            for item in target
            if item.intent is not None and item.intent.value == "adverse_events"
        )
        self.assertEqual(target.source, "logic")
        assert target.intent is not None
        self.assertEqual(target.intent.value, "adverse_events")
        self.assertEqual(
            tuple(code.value for code in target.section_codes), ("11", "11.1", "11.2")
        )

    def test_morphology_detector_returns_nouns(self) -> None:
        target = detect_morphology_criteria(
            JanomeKeywordExtractor(
                search_policy=get_package_insert_definitions().text_search_policy,
                morphology_settings=get_package_insert_definitions().morphology_settings,
            ),
            "頭痛がする",
        )

        self.assertIsNotNone(target)
        assert target is not None
        self.assertEqual(target.source, "keyword")
        self.assertIn("頭痛", tuple(keyword.value for keyword in target.keywords))
        self.assertEqual(tuple(code.value for code in target.section_codes), ())

    def test_fixed_keyword_detector_detects_interaction_for_issho_ni_tsukaeru(
        self,
    ) -> None:
        target = detect_fixed_keyword_criteria(
            "@イトラコナゾールカプセル50mg「SW」 　一緒に使える？",
            get_package_insert_definitions().intent_policy,
        )

        self.assertEqual(len(target), 1)
        target = target[0]
        self.assertEqual(target.source, "logic")
        assert target.intent is not None
        self.assertEqual(target.intent.value, "interaction")
        self.assertEqual(
            tuple(code.value for code in target.section_codes),
            ("10", "10.1", "10.2", "16.7"),
        )
        self.assertEqual(target.keywords, ())

    def test_morphology_detector_excludes_at_mentions_and_product_aliases(self) -> None:
        target = detect_morphology_criteria(
            JanomeKeywordExtractor(
                search_policy=get_package_insert_definitions().text_search_policy,
                morphology_settings=get_package_insert_definitions().morphology_settings,
            ),
            "@イトラコナゾールカプセル50mg「SW」 　一緒に使える？",
            excluded_terms=(
                "イトラコナゾールカプセル50mg「SW」",
                "イトラコナゾール",
                "SW",
            ),
        )

        self.assertIsNone(target)

    def test_morphology_detector_preserves_unrelated_terms_without_whitespace(
        self,
    ) -> None:
        extractor = JanomeKeywordExtractor(
            search_policy=get_package_insert_definitions().text_search_policy,
            morphology_settings=get_package_insert_definitions().morphology_settings,
        )
        target = detect_morphology_criteria(
            extractor,
            "@旧販売名で頭痛が出た",
            excluded_terms=(),
        )
        self.assertIsNotNone(target)
        assert target is not None
        self.assertIn("頭痛", tuple(keyword.value for keyword in target.keywords))

        target_known = detect_morphology_criteria(
            extractor,
            "@ロキソニンで頭痛が出た",
            excluded_terms=("ロキソニン",),
        )
        self.assertIsNotNone(target_known)
        assert target_known is not None
        self.assertIn("頭痛", tuple(keyword.value for keyword in target_known.keywords))
        self.assertNotIn(
            "ロキソニン", tuple(keyword.value for keyword in target_known.keywords)
        )

    def test_morphology_detector_extracts_only_symptom_for_bracketed_medicine(
        self,
    ) -> None:
        extractor = JanomeKeywordExtractor(
            search_policy=get_package_insert_definitions().text_search_policy,
            morphology_settings=get_package_insert_definitions().morphology_settings,
        )
        for message in (
            "@イトラコナゾールカプセル50mg「SW」 で下痢する？",
            "@イトラコナゾールカプセル50mg「SW」で下痢する？",
        ):
            target = detect_morphology_criteria(
                extractor,
                message,
                excluded_terms=(
                    "イトラコナゾールカプセル50mg「SW」",
                    "イトラコナゾールカプセル",
                    "イトラコナゾール",
                    "SW",
                    "いとらこなぞーる",
                ),
            )
            self.assertIsNotNone(target)
            assert target is not None
            keywords = tuple(keyword.value for keyword in target.keywords)
            self.assertEqual(keywords, ("下痢",))
            self.assertNotIn("イトラコナゾール", keywords)
            self.assertNotIn("SW", keywords)
