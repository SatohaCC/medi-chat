"""検索単位の本文保持と構造による選択を検証する。"""

import pytest
from backend.domain.attachment.identifiers import DocumentId
from backend.domain.foundation.exceptions import DomainValidationError
from backend.domain.retrieval.entities import SearchUnit
from backend.domain.retrieval.identifiers import SearchUnitId
from backend.domain.retrieval.primitives import (
    EvidenceContextLabel,
    SearchUnitKind,
    SearchUnitProductCode,
    SearchUnitSectionCode,
    SearchUnitText,
)
from backend.domain.retrieval.services import select_units
from backend.domain.retrieval.value_objects import SearchUnitCriteria


def test_attachment_search_criteria_deduplicate_and_service_filters_units() -> None:
    criteria = SearchUnitCriteria(
        section_codes=frozenset(
            (SearchUnitSectionCode("1"), SearchUnitSectionCode("1"))
        ),
        product_codes=frozenset(
            (
                SearchUnitProductCode("1141007F1063"),
                SearchUnitProductCode("1141007F1063"),
            )
        ),
    )
    units = (
        SearchUnit(
            unit_id=SearchUnitId("unit-1"),
            document_id=DocumentId("doc-001"),
            section_code=SearchUnitSectionCode("1"),
            kind=SearchUnitKind("item"),
            text=SearchUnitText("肝障害"),
            product_codes=(SearchUnitProductCode("1141007F1063"),),
        ),
        SearchUnit(
            unit_id=SearchUnitId("unit-2"),
            document_id=DocumentId("doc-001"),
            section_code=SearchUnitSectionCode("2"),
            kind=SearchUnitKind("item"),
            text=SearchUnitText("別項目"),
            product_codes=(SearchUnitProductCode("1141007F1063"),),
        ),
    )

    assert criteria.section_codes == frozenset({SearchUnitSectionCode("1")})
    assert criteria.product_codes == frozenset({SearchUnitProductCode("1141007F1063")})
    assert select_units(units, criteria) == (units[0],)


def test_search_criteria_values_are_independent_of_condition_order() -> None:
    first = SearchUnitCriteria(
        section_codes=frozenset(
            (SearchUnitSectionCode("1"), SearchUnitSectionCode("2"))
        ),
    )
    second = SearchUnitCriteria(
        section_codes=frozenset(
            (SearchUnitSectionCode("2"), SearchUnitSectionCode("1"))
        ),
    )
    assert first == second
    assert hash(first) == hash(second)
    assert SearchUnitCriteria().section_codes == frozenset()
    assert SearchUnitCriteria().product_codes == frozenset()


def test_search_unit_keeps_context_label_order_and_duplicates():
    labels = ["  成人  ", "腎機能", "成人"]
    unit = SearchUnit(
        unit_id=SearchUnitId("doc:1"),
        document_id=DocumentId("doc"),
        section_code=SearchUnitSectionCode("1"),
        kind=SearchUnitKind("section"),
        text=SearchUnitText("原文"),
        context_labels=tuple(EvidenceContextLabel(label) for label in labels),
    )
    labels.clear()
    assert tuple(label.value for label in unit.context_labels) == (
        "成人",
        "腎機能",
        "成人",
    )


@pytest.mark.parametrize("raw", ["", " ", None, 123])
def test_context_label_rejects_empty_and_non_string(raw):
    with pytest.raises(DomainValidationError):
        EvidenceContextLabel(raw)


def test_context_label_preserves_original_characters():
    assert EvidenceContextLabel("  Ａ① 成人  ").value == "Ａ① 成人"


@pytest.mark.parametrize("text", ["", "  ", " Ａ①\n本文\n "])
def test_search_unit_text_preserves_empty_values_and_original_text(text):
    assert SearchUnitText(text).value == text


@pytest.mark.parametrize("text", [None, 123, ["本文"]])
def test_search_unit_text_rejects_non_strings(text):
    with pytest.raises(DomainValidationError):
        SearchUnitText(text)
