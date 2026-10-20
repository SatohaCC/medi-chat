"""添付文書定義の一元管理と、各利用先への反映を検証する。"""

from __future__ import annotations

import json
from collections.abc import Callable, Iterator
from importlib import import_module
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pytest
from backend.application.chat.answer_prompt_builder import build_answer_system_prompt
from backend.application.medicine.product_models import ResolvedMedicine
from backend.application.retrieval.intent_contracts import IntentRequest
from backend.domain.attachment.identifiers import DocumentId
from backend.domain.medicine.identifiers import YjCode
from backend.domain.medicine.primitives import BrandName, GenericName
from backend.domain.medicine.value_objects import MedicineMatch as DomainMedicineMatch
from backend.domain.retrieval.identifiers import SearchUnitId
from backend.domain.retrieval.primitives import (
    DetectionSource,
    EvidenceExcerpt,
    EvidenceGenericName,
    EvidenceProductName,
    EvidenceSourceUrl,
    SearchUnitKind,
)
from backend.domain.retrieval.services import (
    detect_intents_from_keywords,
    evidence_section_sort_key,
    format_scoped_text,
)
from backend.domain.retrieval.value_objects import (
    DocumentRevision,
    Evidence,
    EvidenceColumns,
    EvidenceReference,
    EvidenceSection,
)
from backend.domain.retrieval.value_objects import Evidence as ChatSource
from backend.infrastructure.evidence_mapping import build_evidence as evidence_from_unit
from backend.infrastructure.intent.jev_classifier import JevIntentClassifier
from backend.infrastructure.morphology.keyword_extraction import extract_search_keywords
from backend.infrastructure.package_insert_definitions import loader as catalog_loader
from backend.infrastructure.package_insert_definitions.loader import (
    PackageInsertDefinitions,
    get_package_insert_definitions,
    load_package_insert_definitions,
)
from backend.infrastructure.pmda_xml.transform import transform


@pytest.fixture
def catalog_data() -> dict[str, Any]:
    return json.loads(catalog_loader.DEFINITIONS_PATH.read_text(encoding="utf-8"))


@pytest.fixture
def activate_catalog(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[Callable[[dict[str, Any]], PackageInsertDefinitions]]:
    def activate(data: dict[str, Any]) -> PackageInsertDefinitions:
        path = tmp_path / "catalog.json"
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        monkeypatch.setattr(catalog_loader, "DEFINITIONS_PATH", path)
        get_package_insert_definitions.cache_clear()
        return get_package_insert_definitions()

    yield activate
    get_package_insert_definitions.cache_clear()


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
    "consumer",
    [
        "keyword_intent",
        "section_codes",
        "text_keywords",
        "janome_adapter",
        "answer_prompt",
        "jev",
    ],
)
async def test_明示注入したカタログを再読込せず各利用先に反映する(
    tmp_path: Path,
    catalog_data: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
    consumer: str,
) -> None:
    catalog_data["sections"]["27"] = {
        "title": "注入した追加項目",
        "xml_tags": ["SupplementarySection"],
    }
    catalog_data["intents"]["supplementary"] = {
        "sections": ["27"],
        "keywords": [{"text": "追補", "exclude_from_text_search": True}],
        "keyword_priority": 27,
        "classification": {"description": "注入した追加項目を参照する質問"},
    }
    catalog_data["answer_prompt"]["citation_examples"].append("27")
    path = tmp_path / "injected-catalog.json"
    path.write_text(json.dumps(catalog_data, ensure_ascii=False), encoding="utf-8")
    catalog = load_package_insert_definitions(path)

    def forbid_catalog_reload(
        *args: object, **kwargs: object
    ) -> PackageInsertDefinitions:
        pytest.fail("明示注入後にバックエンドが共有カタログを再読込した")

    for module_name in (
        "backend.domain.retrieval.services",
        "backend.infrastructure.morphology.keyword_extraction",
        "backend.application.chat.answer_prompt_builder",
        "backend.infrastructure.intent.jev_classifier",
        "backend.infrastructure.package_insert_definitions.loader",
    ):
        monkeypatch.setattr(
            import_module(module_name),
            "get_package_insert_definitions",
            forbid_catalog_reload,
            raising=False,
        )
    monkeypatch.setattr(
        catalog_loader, "load_package_insert_definitions", forbid_catalog_reload
    )

    if consumer == "keyword_intent":
        assert detect_intents_from_keywords(
            "追補について", intent_policy=catalog.intent_policy
        ) == ("supplementary",)
    elif consumer == "section_codes":
        assert catalog.intent_policy.section_codes_for_intent("supplementary") == (
            "27",
        )
    elif consumer == "text_keywords":
        assert (
            extract_search_keywords(
                "追補",
                search_policy=catalog.text_search_policy,
                morphology_settings=catalog.morphology_settings,
            )
            == []
        )
    elif consumer == "janome_adapter":
        from backend.infrastructure.morphology.janome_keyword_extractor import (
            JanomeKeywordExtractor,
        )

        adapter = JanomeKeywordExtractor(
            search_policy=catalog.text_search_policy,
            morphology_settings=catalog.morphology_settings,
        )
        assert adapter.extract_keywords("追補") == ()
    elif consumer == "answer_prompt":
        source = _source(document_revision={"version": "第2版"})
        prompt = build_answer_system_prompt(
            [source],
            [],
            "supplementary",
            answer_prompt_policy=catalog.answer_prompt_policy,
        )
        assert "注入した追加項目 (supplementary)" in prompt
        assert "27. 注入した追加項目" in prompt
        assert "原文の見出し" in prompt
        assert "原文の本文" in prompt
        assert "https://example.test/source" in prompt
        assert "第2版" in prompt
    else:
        client = SimpleNamespace(system_one=AsyncMock(return_value={"answers": {}}))
        classifier = JevIntentClassifier(
            api_key="", classification_settings=catalog.jev_settings
        )
        monkeypatch.setattr(classifier, "_client", client)
        monkeypatch.setattr(
            "backend.infrastructure.intent.jev_classifier.ts.Choice",
            lambda **values: SimpleNamespace(**values),
        )

        await classifier.classify(IntentRequest("追補は？"))

        client.system_one.assert_awaited_once()
        request = client.system_one.call_args.kwargs
        assert request["state"] == {"question": "追補は？"}
        assert request["questions"]["intent"].criteria["supplementary"] == (
            "27. 注入した追加項目：注入した追加項目を参照する質問"
        )


def test_読み込みを共有して利用先からの変更を防ぐ() -> None:
    catalog = get_package_insert_definitions()
    assert get_package_insert_definitions() is catalog
    section_code = next(
        section.code
        for section in catalog.taxonomy.sections
        if section.code.value == "16.7"
    )
    assert section_code.parent_code is not None
    assert section_code.parent_code.value == "16"
    assert catalog.intent_policy.section_codes_for_intent("interaction") == (
        "10",
        "10.1",
        "10.2",
        "16.7",
    )
    assert (
        catalog.answer_prompt_policy.intent_display_name(
            "precautions_related_to_dosage"
        )
        == "用法及び用量に関連する注意"
    )
    assert catalog.answer_prompt_policy.intent_display_name("unknown") == "unknown"
    with pytest.raises(TypeError):
        catalog.taxonomy.sections[0] = catalog.taxonomy.sections[1]  # type: ignore[index]
    criteria = catalog.jev_settings.build_classification_criteria()
    criteria["warnings"] = "変更"
    assert catalog.jev_settings.build_classification_criteria()["warnings"].startswith(
        "1. 警告："
    )
    sections = list(catalog.intent_policy.section_codes_for_intent("interaction"))
    assert sections is not None
    sections.clear()
    assert list(catalog.intent_policy.section_codes_for_intent("interaction")) == [
        "10",
        "10.1",
        "10.2",
        "16.7",
    ]


@pytest.mark.parametrize(
    ("keys", "value", "error"),
    [
        (("schema_version",), 2, "unsupported catalog version"),
        (("sections", "1", "title"), "", "expected nonempty text"),
        (("sections", "1", "typo"), "値", "unknown fields"),
        (("sections", "1", "xml_tags"), "Warnings", "expected a list"),
        (("sections", "2", "xml_tags"), ["Warnings"], "duplicate XML tag"),
        (
            ("sections", "2", "xml_contexts"),
            [{"parent_tag": "Pharmacokinetics", "tag": "OtherInformation"}],
            "duplicate XML context",
        ),
        (
            ("sections", "16.8", "xml_contexts"),
            [{"parent_tag": "Unknown", "tag": "OtherInformation"}],
            "invalid parent XML tag",
        ),
        (
            ("sections", "16.8", "xml_contexts"),
            [{"parent_tag": "Pharmacokinetics", "tag": "Warnings"}],
            "also global",
        ),
        (("intents", "warnings", "sections"), ["999"], "unknown section codes"),
        (("intents", "warnings", "sections"), ["1", "1"], "duplicate values"),
        (
            ("intents", "warnings", "classification", "sections"),
            ["2"],
            "must refer to search sections",
        ),
        (("intents", "warnings", "keyword_priority"), 1, "duplicate keyword priority"),
        (("intents", "warnings", "keyword_priority"), True, "positive integer"),
        (("intents", "warnings", "keywords", 0, "text"), "禁忌", "duplicate keyword"),
        (
            ("intents", "warnings", "keywords", 0, "exclude_from_text_search"),
            "false",
            "expected a boolean",
        ),
        (("intents", "warnings", "sections"), [], "keywords require search sections"),
        (("intents", "composition", "keyword_priority"), 27, "requires keywords"),
        (("fallback_intent",), "unknown", "must exist without sections"),
        (("general_intent",), "document_search", "invalid classification roles"),
        (("answer_prompt", "citation_examples"), ["999"], "unknown section codes"),
        (
            ("answer_prompt", "multiple_intents_template"),
            "{section:999}",
            "unknown section reference",
        ),
        (
            ("answer_prompt", "multiple_intents_template"),
            "{invalid}",
            "invalid section reference",
        ),
        (
            ("intents", "interaction", "answer_guidance", "minimum_medicines"),
            0,
            "positive integer",
        ),
        (("interaction_columns", 1, "id"), "drug_name", "duplicate column ID"),
        (("interaction_columns", 1, "xml_tag"), "DrugName", "duplicate column ID"),
        (("xml", "header_tags"), ["Warnings"], "cannot be document headers"),
        (
            ("text_search", "additional_stop_words"),
            ["警告"],
            "define keyword exclusions on the keyword itself",
        ),
    ],
)
def test_設定不備を読み込み時に拒否する(
    tmp_path: Path,
    catalog_data: dict[str, Any],
    keys: tuple[str | int, ...],
    value: Any,
    error: str,
) -> None:
    target: Any = catalog_data
    for key in keys[:-1]:
        target = target[key]
    target[keys[-1]] = value
    path = tmp_path / "invalid.json"
    path.write_text(json.dumps(catalog_data, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(ValueError, match=error):
        load_package_insert_definitions(path)


@pytest.mark.parametrize(
    ("keys", "error"),
    [
        (("sections", "9"), "unknown parent section"),
        (("sections", "1", "title"), "missing fields"),
    ],
)
def test_必須定義の削除を検出する(
    tmp_path: Path, catalog_data: dict[str, Any], keys: tuple[str, ...], error: str
) -> None:
    target: Any = catalog_data
    for key in keys[:-1]:
        target = target[key]
    del target[keys[-1]]
    path = tmp_path / "missing.json"
    path.write_text(json.dumps(catalog_data), encoding="utf-8")
    with pytest.raises(ValueError, match=error):
        load_package_insert_definitions(path)


def test_JSON重複キーと破損とファイル欠落を通知する(tmp_path: Path) -> None:
    path = tmp_path / "catalog.json"
    with pytest.raises(FileNotFoundError):
        load_package_insert_definitions(path)
    path.write_text('{"schema_version": 1, "schema_version": 1}', encoding="utf-8")
    with pytest.raises(ValueError, match="Duplicate JSON key: schema_version"):
        load_package_insert_definitions(path)
    path.write_text('{"schema_version":', encoding="utf-8")
    with pytest.raises(ValueError):
        load_package_insert_definitions(path)


def test_新しい項目の定義だけで検索とプロンプトとXMLに反映する(
    tmp_path: Path,
    catalog_data: dict[str, Any],
    activate_catalog: Callable[[dict[str, Any]], PackageInsertDefinitions],
) -> None:
    catalog_data["sections"]["27"] = {
        "title": "追加の項目",
        "xml_tags": ["SupplementarySection"],
    }
    catalog_data["intents"]["supplementary"] = {
        "sections": ["27"],
        "keywords": [{"text": "追補", "exclude_from_text_search": True}],
        "keyword_priority": 27,
        "classification": {"description": "追加項目を参照する質問"},
    }
    catalog_data["answer_prompt"]["citation_examples"].append("27")
    catalog = activate_catalog(catalog_data)

    assert detect_intents_from_keywords(
        "追補について", intent_policy=catalog.intent_policy
    ) == ("supplementary",)
    assert catalog.intent_policy.section_codes_for_intent("supplementary") == ("27",)
    assert extract_search_keywords("追補") == []
    assert (
        catalog.jev_settings.build_classification_criteria()["supplementary"]
        == "27. 追加の項目：追加項目を参照する質問"
    )
    prompt = build_answer_system_prompt(
        [], [], "supplementary", answer_prompt_policy=catalog.answer_prompt_policy
    )
    assert "追加の項目 (supplementary)" in prompt
    assert "27. 追加の項目" in prompt

    xml = tmp_path / "insert.xml"
    xml.write_text(
        '<PackIns drugType="Medicine"><PackageInsertNo>001</PackageInsertNo><CompanyIdentifier>000001</CompanyIdentifier><SupplementarySection><Lang>追補の本文</Lang></SupplementarySection></PackIns>',
        encoding="utf-8",
    )
    output = tmp_path / "structured"
    transform(xml, output)
    units = [
        json.loads(line)
        for line in (output / "search_units.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert units[0]["section"] == {"code": "27", "title": "追加の項目"}
    assert (
        units[0]["text"]
        == '<h3 data-section-code="27">27 追加の項目</h3><p>追補の本文</p>'
    )


@pytest.mark.asyncio
async def test_共通定義からJevの分類条件を渡す(
    catalog_data: dict[str, Any],
    activate_catalog: Callable[[dict[str, Any]], PackageInsertDefinitions],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    catalog_data["sections"]["1"]["title"] = "変更した警告名"
    activate_catalog(catalog_data)
    client = SimpleNamespace(system_one=AsyncMock(return_value={"answers": {}}))
    classifier = JevIntentClassifier(api_key="")
    monkeypatch.setattr(classifier, "_client", client)
    monkeypatch.setattr(
        "backend.infrastructure.intent.jev_classifier.ts.Choice",
        lambda **values: SimpleNamespace(**values),
    )

    await classifier.classify(IntentRequest("警告は？"))

    request = client.system_one.call_args.kwargs
    assert request["state"] == {"question": "警告は？"}
    assert (
        request["questions"]["intent"]
        .criteria["warnings"]
        .startswith("1. 変更した警告名：")
    )
    assert len(request["questions"]["intent"].criteria) == 33


def test_列定義の変更がXMLと回答用の表示に反映する(
    tmp_path: Path,
    catalog_data: dict[str, Any],
    activate_catalog: Callable[[dict[str, Any]], PackageInsertDefinitions],
) -> None:
    catalog_data["interaction_columns"].append(
        {"id": "extra_detail", "xml_tag": "ExtraDetail", "title": "追加情報"}
    )
    activate_catalog(catalog_data)
    xml = tmp_path / "insert.xml"
    xml.write_text(
        '<PackIns drugType="Medicine"><PackageInsertNo>001</PackageInsertNo><CompanyIdentifier>000001</CompanyIdentifier><Interactions><ContraIndicatedCombinations><Drug><DrugName><Lang>相手薬</Lang></DrugName><ExtraDetail><Lang>追加本文</Lang></ExtraDetail></Drug></ContraIndicatedCombinations></Interactions></PackIns>',
        encoding="utf-8",
    )
    output = tmp_path / "structured"
    transform(xml, output)
    unit = json.loads(
        (output / "search_units.jsonl").read_text(encoding="utf-8").splitlines()[0]
    )

    assert "追加情報" in unit["text"]
    assert "追加本文" in unit["text"]
    prompt = build_answer_system_prompt(
        [evidence_from_unit(unit, {}, "logic")],
        [],
        "interaction",
        answer_prompt_policy=get_package_insert_definitions().answer_prompt_policy,
    )
    assert "追加情報" in prompt
    assert "追加本文" in prompt


def test_既存列名の変更がXMLの原文を保って回答用表示に反映する(
    tmp_path: Path,
    catalog_data: dict[str, Any],
    activate_catalog: Callable[[dict[str, Any]], PackageInsertDefinitions],
) -> None:
    catalog_data["interaction_columns"][0]["title"] = "変更した薬剤列名"
    activate_catalog(catalog_data)
    xml = tmp_path / "insert.xml"
    xml.write_text(
        '<PackIns drugType="Medicine"><PackageInsertNo>001</PackageInsertNo>'
        "<CompanyIdentifier>000001</CompanyIdentifier><Interactions>"
        "<ContraIndicatedCombinations><Drug><DrugName><Lang>相手薬の原文</Lang>"
        "</DrugName></Drug></ContraIndicatedCombinations></Interactions></PackIns>",
        encoding="utf-8",
    )
    output = tmp_path / "structured"
    transform(xml, output)
    unit = json.loads(
        (output / "search_units.jsonl").read_text(encoding="utf-8").splitlines()[0]
    )

    assert "相手薬の原文" in unit["text"]
    assert "変更した薬剤列名" in unit["text"]
    prompt = build_answer_system_prompt(
        [evidence_from_unit(unit, {}, "logic")],
        [],
        "interaction",
        answer_prompt_policy=get_package_insert_definitions().answer_prompt_policy,
    )
    assert "変更した薬剤列名" in prompt
    assert "相手薬の原文" in prompt
    assert "薬剤名: 相手薬の原文" not in prompt


def test_tc14_列順の変更がXMLと回答の順に反映する(
    tmp_path: Path,
    catalog_data: dict[str, Any],
    activate_catalog: Callable[[dict[str, Any]], PackageInsertDefinitions],
) -> None:
    catalog_data["interaction_columns"].reverse()
    activate_catalog(catalog_data)
    xml = tmp_path / "insert.xml"
    xml.write_text(
        '<PackIns drugType="Medicine"><PackageInsertNo>001</PackageInsertNo>'
        "<CompanyIdentifier>000001</CompanyIdentifier><Interactions>"
        "<ContraIndicatedCombinations><Drug><DrugName><Lang>原文薬剤</Lang></DrugName>"
        "<ClinSymptomsAndMeasures><Lang>原文症状</Lang></ClinSymptomsAndMeasures>"
        "<MechanismAndRiskFactors><Lang>原文機序</Lang></MechanismAndRiskFactors>"
        "</Drug></ContraIndicatedCombinations></Interactions></PackIns>",
        encoding="utf-8",
    )
    output = tmp_path / "structured"
    transform(xml, output)
    unit = json.loads(
        (output / "search_units.jsonl").read_text(encoding="utf-8").splitlines()[0]
    )
    prompt = build_answer_system_prompt(
        [evidence_from_unit(unit, {}, "logic")],
        [],
        "interaction",
        answer_prompt_policy=get_package_insert_definitions().answer_prompt_policy,
    )
    for text in (unit["text"], prompt):
        assert text.index("原文機序") < text.index("原文症状") < text.index("原文薬剤")


def test_専用指示の項目名を生成し根拠原文を保持する(
    catalog_data: dict[str, Any],
    activate_catalog: Callable[[dict[str, Any]], PackageInsertDefinitions],
) -> None:
    catalog_data["sections"]["10"]["title"] = "変更した相互作用名"
    catalog_data["sections"]["10.1"]["title"] = "変更した併用禁忌名"
    catalog_data["sections"]["16"]["title"] = "変更した動態名"
    activate_catalog(catalog_data)
    medicine = ResolvedMedicine(
        medicine=DomainMedicineMatch(
            generic_name=GenericName("成分"),
            brand_names=tuple(BrandName(value) for value in ("製品",)),
            yj_codes=tuple(YjCode(value) for value in ("1234567A0000",)),
        ),
        document_ids=("document-1",),
    )
    source = _source(
        url="https://example.test/source", document_revision={"version": "第2版"}
    )

    prompt = build_answer_system_prompt(
        [source],
        [medicine, medicine],
        "interaction",
        ["interaction", "pharmacokinetics"],
        answer_prompt_policy=get_package_insert_definitions().answer_prompt_policy,
    )

    assert "7. 【複数薬剤の変更した相互作用名に関する指示】" in prompt
    assert "変更した併用禁忌名・併用注意" in prompt
    assert "変更した動態名と用法及び用量" in prompt
    assert "原文の見出し" in prompt
    assert "原文の本文" in prompt
    assert "https://example.test/source" in prompt
    assert "第2版" in prompt
    single = build_answer_system_prompt(
        [],
        [medicine],
        "interaction",
        answer_prompt_policy=get_package_insert_definitions().answer_prompt_policy,
    )
    assert "複数薬剤の" not in single


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
