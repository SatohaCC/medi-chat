"""型付き定義の所有・注入と原文保持を検証する。"""

from dataclasses import FrozenInstanceError, replace
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pytest
from backend.application.chat.queries.policies.answer_prompt import (
    build_answer_system_prompt,
)
from backend.application.indexing.queries.models import DocumentRevision
from backend.application.indexing.queries.policies.text_projection import (
    format_scoped_text,
)
from backend.application.indexing.values import (
    SearchSectionCode,
    SearchUnitId,
    SearchUnitKind,
)
from backend.application.retrieval.queries.models import (
    Evidence,
    EvidenceColumns,
    EvidenceReference,
    EvidenceSection,
    IntentRequest,
)
from backend.application.retrieval.queries.models import Evidence as ChatSource
from backend.application.retrieval.queries.policies.selection import (
    detect_intents_from_keywords,
    evidence_section_sort_key,
)
from backend.application.retrieval.queries.policies.standard import (
    DEFAULT_RETRIEVAL_POLICY,
    EvidenceRetrievalPolicy,
)
from backend.application.retrieval.values import (
    DetectionSource,
    EvidenceExcerpt,
    EvidenceGenericName,
    EvidenceProductName,
    EvidenceSourceUrl,
)
from backend.domain.attachment.exceptions import AttachmentDomainError
from backend.domain.attachment.identifiers import DocumentId
from backend.domain.attachment.primitives import (
    DefinitionTitle,
    NumberedSectionCode,
    SectionScope,
)
from backend.domain.attachment.value_objects import SectionDefinition, SectionTaxonomy
from backend.domain.foundation.exceptions import DomainValidationError
from backend.domain.medicine.identifiers import YjCode
from backend.infrastructure.intent.jev_classifier import JevIntentClassifier
from backend.infrastructure.morphology.janome_keyword_extractor import (
    JanomeKeywordExtractor,
)
from backend.infrastructure.package_insert_definitions import (
    definition_assembly as assembly,
)
from backend.infrastructure.package_insert_definitions.definition_assembly import (
    build_package_insert_definitions,
    get_package_insert_definitions,
)
from backend.infrastructure.package_insert_definitions.xml_settings import (
    DEFAULT_XML_TAGS,
    build_xml_settings,
)
from backend.infrastructure.pmda_xml.pmda_xml_decoder import PmdaXmlDecoder
from backend.tests.support.definition_fixtures import supplementary_definitions


def _source(**values: Any) -> ChatSource:
    columns = values.pop("columns", None)
    retrieved_by = values.pop("retrieved_by", None)
    references = values.pop("references", ())
    return ChatSource(
        unit_id=SearchUnitId.from_value(values.pop("unit_id", "unit-1")),
        document_id=DocumentId("document-1"),
        product_name=EvidenceProductName("テスト製品"),
        generic_name=EvidenceGenericName("テスト成分"),
        product_yj_codes=(YjCode("1234567A0000"),),
        document_revision=DocumentRevision(values.pop("document_revision", {})),
        url=EvidenceSourceUrl(values.pop("url", "https://example.test/source")),
        section=EvidenceSection(
            values.pop("section", {"code": "1", "title": "原文の見出し"})
        ),
        kind=SearchUnitKind("item"),
        excerpt=EvidenceExcerpt("原文の本文"),
        columns=EvidenceColumns(columns) if columns is not None else None,
        references=tuple(EvidenceReference(ref) for ref in references),
        retrieved_by=frozenset({DetectionSource(retrieved_by)})
        if retrieved_by is not None
        else frozenset(),
        **values,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "consumer", ["keyword_intent", "text_keywords", "answer_prompt", "jev", "xml"]
)
async def test_typed_definition_injection_reaches_consumers_without_reload(
    monkeypatch, consumer
):
    definitions = supplementary_definitions()

    def forbid(*args, **kwargs):
        pytest.fail("explicitly injected definitions were rebuilt")

    monkeypatch.setattr(assembly, "build_package_insert_definitions", forbid)
    monkeypatch.setattr(assembly, "get_package_insert_definitions", forbid)
    if consumer == "keyword_intent":
        assert detect_intents_from_keywords(
            "追補について", intent_policy=definitions.intent_policy
        ) == ("supplementary",)
    elif consumer == "text_keywords":
        adapter = JanomeKeywordExtractor(
            search_policy=definitions.text_search_policy,
            morphology_settings=definitions.morphology_settings,
        )
        assert adapter.extract_keywords("追補") == ()
    elif consumer == "answer_prompt":
        prompt = build_answer_system_prompt(
            [_source()],
            [],
            "supplementary",
            answer_prompt_policy=definitions.answer_prompt_policy,
        )
        assert "追加項目の正式名称" in prompt
        assert "27. 追加項目の正式名称" in prompt
        assert "原文の本文" in prompt
    elif consumer == "jev":
        client = SimpleNamespace(system_one=AsyncMock(return_value={"answers": {}}))
        classifier = JevIntentClassifier(
            api_key="", classification_settings=definitions.jev_settings
        )
        monkeypatch.setattr(classifier, "_client", client)
        await classifier.classify(IntentRequest("追補は？"))
        request = client.system_one.call_args.kwargs
        assert request["state"] == {"question": "追補は？"}
        assert (
            request["questions"]["intent"].criteria["supplementary"]
            == "27. 追加項目の正式名称：追加項目の内容に関する質問"
        )
    else:
        from backend.tests.support.attachment_import_fixtures import xml_source

        document = PmdaXmlDecoder(xml_settings=definitions.xml_settings).decode(
            xml_source(
                "<SupplementarySection><Detail><Lang>テスト原文</Lang></Detail></SupplementarySection>"
            )
        )
        assert document.document is not None
        assert (
            definitions.xml_settings.sections_by_xml_tag["SupplementarySection"].title
            == "追加項目の正式名称"
        )


def test_constant_definitions_are_immutable_and_criteria_copy_is_independent():
    definitions = get_package_insert_definitions()
    assert definitions is get_package_insert_definitions()
    with pytest.raises(FrozenInstanceError):
        definitions.taxonomy.sections[0].title = DefinitionTitle("変更")  # pyright: ignore[reportAttributeAccessIssue]
    with pytest.raises(TypeError):
        definitions.jev_settings.criteria["warnings"] = "変更"  # pyright: ignore[reportIndexIssue]
    copied = definitions.jev_settings.build_classification_criteria()
    copied["warnings"] = "変更"
    assert definitions.jev_settings.criteria["warnings"].startswith("1. 警告：")


def test_always_reference_policy_is_independent_from_question_intents():
    definitions = get_package_insert_definitions()
    custom = build_package_insert_definitions(
        retrieval_policy=EvidenceRetrievalPolicy(
            always_retrieved_sections=(SearchSectionCode("9.2"),)
        )
    )
    assert custom.intent_policy == definitions.intent_policy
    assert custom.jev_settings == definitions.jev_settings
    assert custom.retrieval_policy != DEFAULT_RETRIEVAL_POLICY
    assert not hasattr(custom.intent_policy, "always_retrieved_sections")


def test_references_to_unknown_sections_are_rejected():
    with pytest.raises(ValueError, match="unknown policy sections"):
        build_package_insert_definitions(
            retrieval_policy=EvidenceRetrievalPolicy(
                always_retrieved_sections=(SearchSectionCode("99"),)
            )
        )


def test_domain_taxonomy_rejects_duplicate_or_missing_parent():
    section = SectionDefinition(
        code=NumberedSectionCode("1"),
        title=DefinitionTitle("警告"),
        scope=SectionScope("テスト警告の範囲"),
    )
    with pytest.raises(AttachmentDomainError, match="duplicate section"):
        SectionTaxonomy(sections=(section, section))
    with pytest.raises(AttachmentDomainError, match="unknown parent"):
        SectionTaxonomy(sections=(replace(section, code=NumberedSectionCode("1.1")),))
    with pytest.raises(DomainValidationError):
        SectionScope(" ")


@pytest.mark.parametrize("reverse", [False, True])
def test_column_titles_and_order_are_projected_without_rewriting_source(reverse):
    definitions = get_package_insert_definitions()
    columns = tuple(
        replace(c, title=DefinitionTitle("テスト薬剤列"))
        if c.id.value == "drug_name"
        else c
        for c in definitions.interaction_columns
    )
    if reverse:
        columns = tuple(reversed(columns))
    custom = build_package_insert_definitions(interaction_columns=columns)
    assert [c.id for c in custom.answer_prompt_policy.interaction_columns] == [
        c.id.value for c in columns
    ]
    assert [c.id for c in custom.xml_settings.interaction_columns] == [
        c.id.value for c in columns
    ]
    source = _source(
        columns={
            "drug_name": "原文薬剤",
            "clinical_symptoms_and_measures": "原文症状",
            "mechanism_and_risk_factors": "原文機序",
        }
    )
    prompt = build_answer_system_prompt(
        [source], [], "interaction", answer_prompt_policy=custom.answer_prompt_policy
    )
    assert "テスト薬剤列: 原文薬剤" in prompt
    assert "原文症状" in prompt and "原文機序" in prompt


def test_xml_duplicate_tag_is_rejected():
    definitions = get_package_insert_definitions()
    with pytest.raises(ValueError, match="duplicate XML tag"):
        build_xml_settings(
            definitions.taxonomy,
            definitions.interaction_columns,
            tags=DEFAULT_XML_TAGS + (DEFAULT_XML_TAGS[0],),
        )


def test_typed_policy_rejects_duplicate_and_unknown_references():
    from backend.application.retrieval.queries.policies.standard import (
        ClassificationRule,
    )
    from backend.application.retrieval.values import IntentName
    from backend.infrastructure.package_insert_definitions.jev_settings import (
        build_jev_settings,
    )
    from backend.infrastructure.package_insert_definitions.xml_settings import (
        XmlTagMapping,
    )

    code = SearchSectionCode("1")
    with pytest.raises(DomainValidationError, match="duplicate always-retrieved"):
        EvidenceRetrievalPolicy(always_retrieved_sections=(code, code))
    with pytest.raises(DomainValidationError, match="duplicate classification"):
        ClassificationRule(intent=IntentName("test"), section_codes=(code, code))
    with pytest.raises(DomainValidationError, match="requires description"):
        ClassificationRule(intent=IntentName("test"), section_codes=())
    definitions = get_package_insert_definitions()
    with pytest.raises(ValueError, match="unknown classification section"):
        build_jev_settings(
            definitions.taxonomy,
            (
                ClassificationRule(
                    intent=IntentName("test"), section_codes=(SearchSectionCode("99"),)
                ),
            ),
        )
    with pytest.raises(ValueError, match="unknown XML sections"):
        build_xml_settings(
            definitions.taxonomy,
            definitions.interaction_columns,
            tags=DEFAULT_XML_TAGS + (XmlTagMapping(tag="Test", section_code="99"),),
        )
    with pytest.raises(ValueError, match="duplicate interaction column"):
        build_xml_settings(
            definitions.taxonomy,
            definitions.interaction_columns + (definitions.interaction_columns[0],),
        )


@pytest.mark.parametrize(
    ("message", "intent"),
    [
        ("副作用と併用について", ("interaction", "adverse_events", "indications")),
        ("妊娠可能な人は？", ("reproductive_potential", "pregnancy")),
        ("妊娠中は？", ("pregnancy",)),
        ("主要文献は？", ("contact_info",)),
        ("作用機序は？", ("indications", "pharmacology")),
        ("こんにちは", ()),
    ],
)
def test_固定キーワードの全分類を取得する(
    message: str, intent: tuple[str, ...]
) -> None:
    assert (
        detect_intents_from_keywords(
            message, intent_policy=get_package_insert_definitions().intent_policy
        )
        == intent
    )


@pytest.mark.parametrize(
    ("codes", "expected_codes"),
    [
        (
            ["16.7", "10.2", "1", "3.2", "10", "2", "3.1"],
            ["1", "2", "3.1", "3.2", "10", "10.2", "16.7"],
        ),
        (["11.1", "9.5", "10.1", "9.4"], ["9.4", "9.5", "10.1", "11.1"]),
    ],
    ids=["existing_seven_codes", "approved_chapter_codes"],
)
def test_根拠一覧の項目番号順を維持する(
    codes: list[str],
    expected_codes: list[str],
) -> None:
    sources = [
        Evidence(
            unit_id=SearchUnitId(f"test_001:{index:03d}"),
            document_id=DocumentId("test_001"),
            product_name=EvidenceProductName("テスト薬"),
            generic_name=EvidenceGenericName("テスト成分"),
            product_yj_codes=(YjCode("1234567A0000"),),
            document_revision=DocumentRevision({}),
            section=EvidenceSection({"code": code}),
            kind=SearchUnitKind("text"),
            excerpt=EvidenceExcerpt("原文の本文"),
            url=EvidenceSourceUrl("https://example.test/package-insert"),
        )
        for index, code in enumerate(codes)
    ]
    source_codes = [
        source.section["code"]
        for source in sorted(sources, key=evidence_section_sort_key)
    ]
    assert source_codes == expected_codes


@pytest.mark.parametrize(
    ("text", "scope", "expected"),
    [
        ("本文", [], "本文"),
        ("本文", ["成人"], "〈成人〉 本文"),
        ("〈成人〉 本文", ["成人"], "〈成人〉 本文"),
        ("本文\n続き", ["［条件］"], "［条件］\n本文\n続き"),
    ],
)
def test_スコープ見出しを重複せず整形する(
    text: str, scope: list[str], expected: str
) -> None:
    assert format_scoped_text(text, scope) == expected


def test_section_scope_is_required_and_nonempty():
    from dataclasses import MISSING, fields

    scope_field = next(f for f in fields(SectionDefinition) if f.name == "scope")
    assert scope_field.default is MISSING
    assert scope_field.default_factory is MISSING
    definitions = get_package_insert_definitions()
    assert len(definitions.taxonomy.sections) == 54
    assert all(section.scope.value.strip() for section in definitions.taxonomy.sections)


def test_jev_includes_combined_sections_and_descendant_meanings():
    criteria = get_package_insert_definitions().jev_settings.criteria
    assert "5 効能又は効果に関連する注意：" in criteria["indications"]
    assert "7 用法及び用量に関連する注意：" in criteria["dosage"]
    assert "10.1 併用禁忌：" in criteria["interaction"]
    assert "10.2 併用注意：" in criteria["interaction"]
    assert "16.4 代謝：" in criteria["pharmacokinetics"]
    assert "16.7 薬物相互作用：" in criteria["pharmacokinetics"]
    assert "17.3 その他：" in criteria["clinical_studies"]
    assert "薬物動態" in criteria["pharmacokinetics"]


def test_child_scope_change_reaches_jev_without_changing_question_options():
    definitions = get_package_insert_definitions()
    taxonomy = replace(
        definitions.taxonomy,
        sections=tuple(
            replace(section, scope=SectionScope("テスト代謝範囲"))
            if section.code.value == "16.4"
            else section
            for section in definitions.taxonomy.sections
        ),
    )
    custom = build_package_insert_definitions(taxonomy=taxonomy)
    assert "テスト代謝範囲" in custom.jev_settings.criteria["pharmacokinetics"]
    assert tuple(custom.jev_settings.criteria) == tuple(
        definitions.jev_settings.criteria
    )
