"""TC01/03/04/05: purpose-owned definitions and projection regression."""

import inspect
from dataclasses import fields
from pathlib import Path

import pytest


def test_purpose_models_keep_same_default_targets_and_labels() -> None:
    from backend.infrastructure.package_insert_definitions.assembly import (
        get_package_insert_definitions,
    )

    definitions = get_package_insert_definitions()
    assert get_package_insert_definitions() is definitions
    assert definitions.intent_policy.section_codes_for_intent("interaction") == (
        "10",
        "10.1",
        "10.2",
        "16.7",
    )
    assert definitions.answer_prompt_policy.intent_display_name("warnings") == "警告"
    assert definitions.answer_prompt_policy.intent_display_name("unknown") == "unknown"
    assert definitions.jev_settings.build_classification_criteria()[
        "warnings"
    ].startswith("1. 警告：")
    assert "ignored_noun_suffixes" not in {
        field.name for field in fields(definitions.text_search_policy)
    }
    assert definitions.morphology_settings.ignored_noun_suffixes
    assert not hasattr(definitions.intent_policy, "answer_prompt")
    assert not hasattr(definitions.intent_policy, "sections_by_xml_tag")
    assert not hasattr(definitions.answer_prompt_policy, "text_search")
    with pytest.raises(TypeError):
        definitions.jev_settings.criteria["warnings"] = "changed"  # pyright: ignore[reportIndexIssue]
    copied = definitions.jev_settings.build_classification_criteria()
    copied["warnings"] = "changed"
    assert definitions.jev_settings.build_classification_criteria()[
        "warnings"
    ].startswith("1. 警告：")


def test_canonical_title_projection_preserves_raw_text(tmp_path: Path) -> None:
    from backend.tests.support.definition_fixtures import renamed_definitions

    definitions = renamed_definitions()
    assert (
        definitions.answer_prompt_policy.intent_display_name("warnings")
        == "  全角Ａ警告  "
    )
    assert definitions.jev_settings.build_classification_criteria()[
        "warnings"
    ].startswith("1.   全角Ａ警告  ：")
    assert (
        definitions.xml_settings.sections_by_xml_tag["Warnings"].title
        == "  全角Ａ警告  "
    )


def test_tc01_single_source_bytes_and_tc03_constructor_ownership() -> None:
    from backend.application.chat.queries.chat import (
        ChatQueries,
    )
    from backend.domain.attachment.value_objects import SectionDefinition
    from backend.infrastructure.intent.jev_classifier import JevIntentClassifier
    from backend.infrastructure.morphology.janome_keyword_extractor import (
        JanomeKeywordExtractor,
    )

    # Definition source is Python; JSON source/loader are no longer supported.
    from backend.infrastructure.package_insert_definitions import assembly
    from backend.infrastructure.persistence.postgres_runtime import PostgresRuntime
    from backend.infrastructure.pmda_xml.decoder import PmdaXmlDecoder
    from backend.presentation.chat_service import AppChatService
    from backend.project_paths import PROJECT_ROOT

    assert not hasattr(assembly, "load_package_insert_definitions")
    assert not hasattr(assembly, "DEFINITIONS_PATH")
    assert not (PROJECT_ROOT / "package_inserts").exists()
    assert {field.name for field in fields(SectionDefinition)} == {
        "code",
        "title",
        "scope",
    }
    for constructor, required in (
        (ChatQueries, {"intent_policy", "answer_prompt_policy"}),
        (AppChatService, {"application_service"}),
        (JevIntentClassifier, {"classification_settings"}),
        (JanomeKeywordExtractor, {"search_policy", "morphology_settings"}),
        (PostgresRuntime, {"text_search_policy", "workers"}),
        (PmdaXmlDecoder, {"xml_settings"}),
    ):
        names = set(inspect.signature(constructor).parameters)
        assert required <= names
        assert "catalog" not in names


@pytest.mark.parametrize(
    "member",
    [
        "answer_prompt_policy.intent_labels",
        "answer_prompt_policy.guidance",
        "xml_settings.sections_by_xml_tag",
        "xml_settings.sections_by_xml_context",
        "xml_settings.atomic_units",
        "jev_settings.criteria",
    ],
)
def test_tc04_every_purpose_nested_mapping_is_readonly(member: str) -> None:
    from backend.infrastructure.package_insert_definitions.assembly import (
        get_package_insert_definitions,
    )

    definitions = get_package_insert_definitions()
    purpose, name = member.split(".")
    mapping = getattr(getattr(definitions, purpose), name)
    before = dict(mapping)
    with pytest.raises(TypeError):
        mapping["mutation-probe"] = "changed"
    assert dict(mapping) == before
    assert get_package_insert_definitions() is definitions
