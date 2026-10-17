"""API値と純粋DTOの間で公開情報が保たれることを検証する。"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import fields

import pytest
from backend.application.chat.chat_models import ChatMessage, ChatResponse
from backend.application.medicine.product_models import ResolvedMedicine
from backend.domain.foundation.json_types import JsonValue
from backend.domain.foundation.primitives.primitives import (
    BaseFiniteFloat,
    BaseString,
)
from backend.domain.medicine.value_objects import MedicineMatch
from backend.domain.retrieval.primitives import DetectionSource
from backend.domain.retrieval.value_objects import Evidence
from backend.presentation.chat_dto_mapper import (
    chat_message_from_api,
    chat_message_to_api,
    chat_response_to_api,
)
from backend.presentation.chat_models import ChatMessage as ApiChatMessage
from backend.presentation.chat_models import ChatResponse as ApiChatResponse
from backend.presentation.evidence_models import ChatSource as ApiChatSource
from backend.presentation.medicine_models import MedicineMatch as ApiMedicineMatch


def _assert_pure_value(value: object) -> None:
    """許可した実DTOと標準Python値だけを、全ネストで確認する。"""
    if isinstance(value, Mapping) and type(value) is not dict:
        _assert_pure_value(dict(value))
    elif isinstance(
        value, (ChatMessage, ChatResponse, ResolvedMedicine, MedicineMatch, Evidence)
    ):
        assert type(value) in (
            ChatMessage,
            ChatResponse,
            ResolvedMedicine,
            MedicineMatch,
            Evidence,
        )
        for field in fields(value):
            _assert_pure_value(getattr(value, field.name))
    elif isinstance(value, (list, tuple, frozenset)):
        assert type(value) in (list, tuple, frozenset)
        for item in value:
            _assert_pure_value(item)
    elif isinstance(value, dict):
        assert type(value) is dict
        for key, item in value.items():
            assert type(key) is str
            _assert_pure_value(item)
    else:
        if isinstance(
            value,
            (
                BaseFiniteFloat,
                BaseString,
                DetectionSource,
            ),
        ):
            return
        assert type(value) in (str, int, float, bool, type(None)), (
            f"純粋DTOに外部型が残った: {type(value)}"
        )


@pytest.fixture
def response_payload() -> dict[str, JsonValue]:
    return {
        "answer": "根拠に基づく回答。\n原文を保持します。",
        "intent": "interaction, pharmacokinetics",
        "retrieval_strategy": "three_detectors",
        "resolved_medicines": [
            {
                "generic_name": "テスト成分",
                "brand_names": ["テスト錠1mg", "テスト錠2mg"],
                "yj_codes": ["1234567A0000", "1234567A0001"],
                "document_ids": ["document-1", "document-2"],
                "matched_aliases": ["テスト錠", "テスト成分"],
            }
        ],
        "sources": [
            {
                "unit_id": "unit-1",
                "document_id": "document-1",
                "product_name": "テスト錠1mg",
                "generic_name": "テスト成分",
                "product_yj_codes": ["1234567A0000", "1234567A0001"],
                "document_revision": {
                    "source_label": "今回",
                    "year_month": "2026年10月",
                    "version": "第2版",
                    "metadata": {"number": 2, "verified": True, "missing": None},
                },
                "section": {"code": "10.1", "title": "原文の併用禁忌見出し"},
                "kind": "interaction_row",
                "excerpt": "原文の本文。\n次の行も保持。",
                "columns": {
                    "drug_name": "相手薬の原文",
                    "clinical_symptoms_and_measures": "症状・措置の原文",
                    "mechanism_and_risk_factors": "機序の原文",
                },
                "references": [
                    {
                        "kind": "SectionRef",
                        "target_section_code": "16.7",
                        "target_url": "https://example.test/insert#section-16-7",
                        "metadata": ["参照原文", 1, False, None, {"id": "ref-1"}],
                    }
                ],
                "url": "https://example.test/insert#section-10-1",
                "retrieved_by": ["logic", "jev", "keyword"],
            },
            {
                "unit_id": "unit-2",
                "document_id": "document-2",
                "product_name": "テスト錠2mg",
                "generic_name": "テスト成分",
                "product_yj_codes": ["1234567A0001"],
                "document_revision": {},
                "section": {"code": "16.7", "title": "原文の薬物相互作用見出し"},
                "kind": "item",
                "excerpt": "表のない原文。",
                "columns": None,
                "references": [],
                "url": "https://example.test/second-insert",
                "retrieved_by": [],
            },
        ],
        "needs_clarification": False,
        "notices": ["原文を確認してください。", "改訂情報を保持。"],
        "jev_response": {
            "qualifying_intents": ["interaction", "pharmacokinetics"],
            "answers": {
                "intent": {"interaction": 0.91, "pharmacokinetics": 0.73},
            },
            "metadata": [True, None, {"attempts": 1}],
        },
    }


def _application_response(payload):
    from backend.domain.attachment.identifiers import DocumentId
    from backend.domain.medicine.identifiers import YjCode
    from backend.domain.retrieval.identifiers import SearchUnitId
    from backend.domain.retrieval.value_objects import (
        DocumentRevision,
        EvidenceColumns,
        EvidenceReference,
        EvidenceSection,
    )

    return ChatResponse(
        answer=payload["answer"],
        intent=payload["intent"],
        retrieval_strategy=payload["retrieval_strategy"],
        needs_clarification=payload["needs_clarification"],
        notices=list(payload["notices"]),
        jev_response=payload["jev_response"],
        qualifying_intents=("interaction", "pharmacokinetics"),
        resolved_medicines=[
            ResolvedMedicine(
                medicine=MedicineMatch(
                    generic_name=m["generic_name"],
                    brand_names=tuple(m["brand_names"]),
                    yj_codes=tuple(m["yj_codes"]),
                    matched_aliases=tuple(m["matched_aliases"]),
                ),
                document_ids=tuple(m["document_ids"]),
            )
            for m in payload["resolved_medicines"]
        ],
        sources=[
            Evidence(
                unit_id=SearchUnitId(v["unit_id"]),
                document_id=DocumentId(v["document_id"]),
                product_name=v["product_name"],
                generic_name=v["generic_name"],
                product_yj_codes=tuple(YjCode(c) for c in v["product_yj_codes"]),
                document_revision=DocumentRevision(v["document_revision"]),
                section=EvidenceSection(v["section"]),
                kind=v["kind"],
                excerpt=v["excerpt"],
                columns=EvidenceColumns(v["columns"])
                if v["columns"] is not None
                else None,
                references=tuple(EvidenceReference(r) for r in v["references"]),
                url=v["url"],
                retrieved_by=frozenset(DetectionSource(d) for d in v["retrieved_by"]),
            )
            for v in payload["sources"]
        ],
    )


@pytest.mark.parametrize("scenario", ["message", "resolved", "unresolved"])
def test_directional_dto_mapping_preserves_public_information(
    scenario: str, response_payload: dict[str, JsonValue]
) -> None:
    if scenario == "message":
        messages = [
            (
                ApiChatMessage(role="user", content="  質問本文\n続き  "),
                "user",
                "質問本文\n続き",
            ),
            (
                ApiChatMessage(role="assistant", content="  回答本文  "),
                "assistant",
                "回答本文",
            ),
            (
                ApiChatMessage(role="system", content="  指示本文  "),
                "system",
                "指示本文",
            ),
        ]
        for api_message, role, content in messages:
            assert api_message.content == content
            message = chat_message_from_api(api_message)
            assert type(message) is ChatMessage
            _assert_pure_value(message)
            assert message.role == role
            assert message.content == content
            restored_message = chat_message_to_api(message)
            assert type(restored_message) is ApiChatMessage
            assert restored_message.model_dump(mode="json") == {
                "role": role,
                "content": content,
            }
        return

    if scenario == "unresolved":
        response_payload.update(
            answer="指定した薬剤の一部に対応する電子添文がありません。",
            retrieval_strategy="product_code_lookup",
            sources=[],
            needs_clarification=True,
            notices=["検索対象のYJコードを確認してください。"],
            jev_response=None,
        )

    api_response = ApiChatResponse.model_validate(response_payload)
    assert type(api_response.resolved_medicines[0]) is ApiMedicineMatch
    if scenario == "resolved":
        assert all(type(source) is ApiChatSource for source in api_response.sources)

    response = _application_response(response_payload)

    assert type(response) is ChatResponse
    assert type(response.resolved_medicines[0]) is ResolvedMedicine
    if scenario == "resolved":
        assert len(response.sources) == 2
        assert all(type(source) is Evidence for source in response.sources)
    else:
        assert response.needs_clarification is True
        assert response.sources == []
    _assert_pure_value(response)

    restored_response = chat_response_to_api(response)

    assert type(restored_response) is ApiChatResponse
    assert restored_response.model_dump(mode="json") == response_payload


@pytest.mark.parametrize("columns", [None, {}])
def test_empty_values_and_none_columns_remain_distinct(columns, response_payload):
    source = response_payload["sources"][0]
    source.update(columns=columns, section={}, document_revision={}, references=[])
    response = _application_response(response_payload)
    public = chat_response_to_api(response).model_dump(mode="json")
    assert public == response_payload
    assert "qualifying_intents" not in public
