from __future__ import annotations

import unittest

from backend.application.retrieval.morphology_detector import detect_morphology_criteria
from backend.domain.retrieval.services import detect_fixed_keyword_criteria
from backend.infrastructure.morphology.janome_keyword_extractor import (
    JanomeKeywordExtractor,
)
from backend.infrastructure.package_insert_definitions.loader import (
    get_package_insert_definitions,
)


class SearchDetectorTests(unittest.TestCase):
    def test_fixed_keyword_detector_returns_section_codes(self) -> None:
        target = detect_fixed_keyword_criteria(
            "副作用について教えて", get_package_insert_definitions().intent_policy
        )

        self.assertIsNotNone(target)
        assert target is not None
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

        self.assertIsNotNone(target)
        assert target is not None
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

