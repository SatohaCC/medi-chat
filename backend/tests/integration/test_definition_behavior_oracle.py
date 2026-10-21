"""TC05/10/12/14/16: fixed observations collected before decomposition."""

from __future__ import annotations

import json
from pathlib import Path

from backend.application.chat.answer_prompt_builder import build_answer_messages
from backend.application.chat.chat_models import ChatMessage, ChatResponse
from backend.application.indexing.text_projection import format_scoped_text
from backend.application.medicine.product_models import ResolvedMedicine
from backend.domain.medicine.identifiers import YjCode
from backend.domain.medicine.primitives import BrandName, GenericName
from backend.domain.medicine.value_objects import MedicineMatch as DomainMedicineMatch
from backend.infrastructure.morphology.keyword_extraction import extract_search_keywords
from backend.infrastructure.package_insert_definitions.loader import (
    get_package_insert_definitions,
    load_package_insert_definitions,
)
from backend.tests.integration.test_package_insert_catalog import _source
from backend.tests.support.paths import FIXTURES_ROOT

ORACLE = FIXTURES_ROOT / "definition-behavior-reference.json"


def observe() -> dict[str, object]:
    catalog = get_package_insert_definitions()
    source = _source(
        section={"code": "10.1", "title": "原文の併用禁忌"},
        columns={
            "drug_name": "原文薬剤",
            "clinical_symptoms_and_measures": "原文症状",
            "mechanism_and_risk_factors": "原文機序",
        },
        document_revision={
            "source_label": "今回",
            "year_month": "2026-09",
            "version": "第２版",
        },
        references=[
            {
                "kind": "HeaderRef",
                "target_section_code": "2",
                "target_url": "https://example.test/doc#2",
            }
        ],
    )
    medicine = ResolvedMedicine(
        medicine=DomainMedicineMatch(
            generic_name=GenericName("原文成分"),
            brand_names=tuple(BrandName(value) for value in ("原文薬剤",)),
            yj_codes=tuple(YjCode(value) for value in ("1234567A0000",)),
        ),
        document_ids=("document-1",),
    )
    conversation = [
        ChatMessage("system", "除外する会話system"),
        ChatMessage("user", "以前の質問"),
        ChatMessage("assistant", "以前の回答"),
        ChatMessage("user", "今回の質問"),
    ]
    prompts = {}
    for intent, qualifying in (
        ("interaction", ()),
        ("interaction", ("interaction", "warnings")),
        ("unknown", ()),
    ):
        for count in (0, 1, 2, 3):
            reply = ChatResponse(
                "",
                intent,
                "three_detectors",
                [medicine] * count,
                [source],
                qualifying_intents=qualifying,
            )
            prompts[f"{intent}/{','.join(qualifying)}/{count}"] = build_answer_messages(
                reply, conversation, answer_prompt_policy=catalog.answer_prompt_policy
            )
    texts = (
        "",
        "  ",
        "副作用は何がある？",
        "眠い",
        "空腹時に飲める？",
        "頭痛と頭痛",
        "患者さんの頭痛",
        "アルコールと一緒に飲んで平気？",
    )
    scoped = [
        ("本文", []),
        ("本文", ["成人"]),
        ("〈成人〉 本文", ["成人"]),
        ("本文\n続き", ["［条件］"]),
        ("あ" * 40, ["成人"]),
        ("あ" * 41, ["成人"]),
    ]
    return {
        "criteria": list(catalog.jev_settings.build_classification_criteria().items()),
        "intents": [
            [
                key,
                list(catalog.intent_policy.section_codes_for_intent(key)),
                catalog.answer_prompt_policy.intent_display_name(key),
            ]
            for key in (
                *(intent.id.value for intent in catalog.intent_policy.intents),
                "unknown",
            )
        ],
        "keywords": {
            text: extract_search_keywords(
                text,
                search_policy=catalog.text_search_policy,
                morphology_settings=catalog.morphology_settings,
            )
            for text in texts
        },
        "messages": prompts,
        "scope": [format_scoped_text(text, scope) for text, scope in scoped],
    }


def test_definition_behavior_matches_prechange_oracle() -> None:
    expected = json.loads(ORACLE.read_text(encoding="utf-8"))
    actual = json.loads(json.dumps(observe(), ensure_ascii=False))
    assert actual == expected


def test_tc05_titles_preserve_whitespace_and_alias_fallback(tmp_path: Path) -> None:
    from backend.infrastructure.package_insert_definitions.loader import (
        DEFINITIONS_PATH,
    )

    data = json.loads(DEFINITIONS_PATH.read_text(encoding="utf-8"))
    data["sections"]["1"]["title"] = "  全角Ａ警告  "
    data["sections"]["1"].pop("display_title", None)
    data["sections"]["1"].pop("classification_title", None)
    data["sections"]["10"]["title"] = "  全角Ｂ相互作用  "
    data["sections"]["10"]["display_title"] = "表示別名"
    data["sections"]["10"]["classification_title"] = "分類別名"
    path = tmp_path / "titles.json"
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    catalog = load_package_insert_definitions(path)
    assert (
        next(
            section.title.value
            for section in catalog.taxonomy.sections
            if section.code.value == "1"
        )
        == "  全角Ａ警告  "
    )
    assert (
        catalog.answer_prompt_policy.intent_display_name("warnings") == "  全角Ａ警告  "
    )
    assert catalog.jev_settings.build_classification_criteria()["warnings"].startswith(
        "1.   全角Ａ警告  ："
    )
    assert catalog.answer_prompt_policy.intent_display_name("interaction") == "表示別名"
    assert catalog.jev_settings.build_classification_criteria()[
        "interaction"
    ].startswith("10. 分類別名：")
    assert catalog.answer_prompt_policy.intent_display_name("unknown") == "unknown"
