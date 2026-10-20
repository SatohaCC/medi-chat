"""TC08/10/15/21: explicit purpose policies never return to the definition source."""

from dataclasses import replace

import pytest
from backend.domain.foundation.json_types import JsonValue
from backend.domain.retrieval.primitives import SearchPolicyTerm
from backend.domain.retrieval.value_objects import SymptomKeywordRule


def test_tc15_mapping_uses_injected_heading_policy(monkeypatch) -> None:
    from backend.infrastructure import evidence_mapping
    from backend.infrastructure.package_insert_definitions import loader

    definitions = loader.get_package_insert_definitions()
    policy = replace(
        definitions.text_search_policy,
        scope_heading_texts=frozenset({SearchPolicyTerm("特別見出し")}),
    )

    def forbid(*args, **kwargs):
        pytest.fail("explicit mapping policy reloaded definition source")

    monkeypatch.setattr(loader, "get_package_insert_definitions", forbid)
    monkeypatch.setattr(loader, "load_package_insert_definitions", forbid)
    heading: dict[str, JsonValue] = {"kind": "item", "text": "特別見出し"}
    body: dict[str, JsonValue] = {"kind": "item", "text": "保持する原文本文"}
    assert evidence_mapping.is_scope_heading_only(heading, text_search_policy=policy)
    assert not evidence_mapping.is_scope_heading_only(
        heading, text_search_policy=definitions.text_search_policy
    )
    assert not evidence_mapping.is_scope_heading_only(body, text_search_policy=policy)


def test_janome_business_and_morphology_settings_are_independent(monkeypatch) -> None:
    from backend.infrastructure.morphology.definition_settings import (
        JanomeMorphologySettings,
    )
    from backend.infrastructure.morphology.janome_keyword_extractor import (
        JanomeKeywordExtractor,
    )
    from backend.infrastructure.package_insert_definitions import loader

    definitions = loader.get_package_insert_definitions()
    default = JanomeKeywordExtractor(
        search_policy=definitions.text_search_policy,
        morphology_settings=definitions.morphology_settings,
    )
    business = JanomeKeywordExtractor(
        search_policy=replace(
            definitions.text_search_policy,
            stop_words=definitions.text_search_policy.stop_words
            | {SearchPolicyTerm("改善")},
            symptom_rules=(
                SymptomKeywordRule(
                    adjective=SearchPolicyTerm("眠い"),
                    keywords=(SearchPolicyTerm("眠気変更"),),
                ),
            ),
        ),
        morphology_settings=definitions.morphology_settings,
    )
    morphology = JanomeKeywordExtractor(
        search_policy=definitions.text_search_policy,
        morphology_settings=JanomeMorphologySettings(ignored_noun_suffixes=frozenset()),
    )

    def forbid(*args, **kwargs):
        pytest.fail("explicit Janome settings reloaded definition source")

    monkeypatch.setattr(loader, "get_package_insert_definitions", forbid)
    monkeypatch.setattr(loader, "load_package_insert_definitions", forbid)
    assert default.extract_keywords("改善点") == ("改善",)
    assert morphology.extract_keywords("改善点") == ("改善点", "改善")
    assert business.extract_keywords("改善点") == ()
    assert business.extract_keywords("眠い") == ("眠気変更",)
    assert default.extract_keywords("眠い") == ("眠気", "傾眠")
