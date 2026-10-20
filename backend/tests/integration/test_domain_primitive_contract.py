"""Primitive統一後の値比較・復元・公開境界の契約を検証する。"""

import json
from dataclasses import FrozenInstanceError, replace

import pytest
from backend.application.chat.chat_models import ChatResponse
from backend.domain.attachment.identifiers import DocumentId
from backend.domain.attachment.primitives import (
    AttachmentProductCode,
    AttachmentUrl,
    PmdaUrl,
    SectionCode,
)
from backend.domain.foundation.exceptions import DomainValidationError
from backend.domain.foundation.primitives.base import DomainPrimitive
from backend.domain.medicine.identifiers import YjCode
from backend.domain.medicine.primitives import ProductGroupId
from backend.domain.retrieval.identifiers import SearchUnitId
from backend.domain.retrieval.primitives import (
    DetectionSource,
    EvidenceExcerpt,
    IntentName,
    Probability,
    SearchKeyword,
    SearchSectionCode,
    SearchUnitKind,
)
from backend.domain.retrieval.value_objects import (
    IntentCandidate,
    IntentSelection,
    SearchCriteria,
)
from backend.presentation.chat_dto_mapper import chat_response_to_api
from backend.tests.domain.retrieval.test_evidence_collection import make_evidence


@pytest.mark.parametrize(
    "primitive",
    [
        DocumentId("doc"),
        PmdaUrl("url"),
        SectionCode("1"),
        YjCode("1234567A0000"),
        ProductGroupId("成分"),
        IntentName("warnings"),
        SearchKeyword("症状"),
        Probability(0.2),
        SearchUnitId("unit"),
        SectionCode("1.1"),
        AttachmentProductCode("code"),
        SearchUnitKind("item"),
        AttachmentUrl("https://example.test/doc"),
    ],
)
def test_primitives_have_typed_value_equality_and_immutable_restoration(primitive):
    assert isinstance(primitive, DomainPrimitive)
    assert not isinstance(primitive, (str, float))
    assert primitive != primitive.value
    assert primitive == type(primitive)(primitive.value)
    assert type(primitive).from_value(primitive) is primitive
    assert len({primitive, type(primitive)(primitive.value)}) == 1
    assert hasattr(primitive, "__dict__") is False
    with pytest.raises(FrozenInstanceError):
        primitive.value = "changed"  # pyright: ignore[reportAttributeAccessIssue]


def test_different_primitive_types_do_not_compare_equal():
    assert DocumentId("same") != SearchUnitId("same")
    with pytest.raises(DomainValidationError):
        DocumentId.from_value(SearchUnitId("same"))  # pyright: ignore[reportArgumentType]


@pytest.mark.parametrize("value", [True, False, float("nan"), float("inf"), -0.1, 1.1])
def test_probability_rejects_invalid_raw_values(value):
    with pytest.raises(DomainValidationError):
        Probability(value)


def test_dataclass_reconstruction_preserves_search_primitives():
    values = (
        SearchCriteria(
            DetectionSource("logic"),
            IntentName("warnings"),
            (SearchSectionCode("1"),),
            (SearchKeyword("症状"),),
        ),
        IntentCandidate(IntentName("warnings"), Probability(0.2)),
        IntentSelection(
            IntentName("warnings"), (IntentName("warnings"),), (SearchSectionCode("1"),)
        ),
    )
    for value in values:
        assert replace(value) == value
        assert hasattr(value, "__dict__") is False


def test_evidence_json_and_api_keep_basic_values_after_reconstruction():
    evidence = make_evidence()
    reconstructed = replace(evidence, excerpt=EvidenceExcerpt("更新した原文"))
    payload = reconstructed.to_dict()
    assert payload["unit_id"] == evidence.unit_id.value
    assert payload["document_id"] == evidence.document_id.value
    assert "document_key" not in payload
    assert payload["product_yj_codes"] == [
        code.value for code in evidence.product_yj_codes
    ]
    assert payload["excerpt"] == "更新した原文"
    assert json.loads(json.dumps(payload, ensure_ascii=False)) == payload
    reply = ChatResponse(
        answer="回答",
        intent="warnings",
        retrieval_strategy="three_detectors",
        sources=[reconstructed],
    )
    assert chat_response_to_api(reply).model_dump(mode="json")["sources"] == [payload]


def test_search_section_codes_preserve_existing_non_numeric_input_contract():
    criteria = SearchCriteria(
        DetectionSource.LOGIC, section_codes=(SearchSectionCode("custom-section"),)
    )
    assert criteria.section_codes == (SearchSectionCode("custom-section"),)
    with pytest.raises(DomainValidationError):
        SectionCode("custom-section").require_numbered()
