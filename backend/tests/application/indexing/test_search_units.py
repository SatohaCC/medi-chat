"""検索単位の本文保持と構造による選択を検証する。"""

import pytest
from backend.application.indexing.queries.models import SearchUnit
from backend.application.indexing.values import (
    EvidenceContextLabel,
    SearchUnitId,
    SearchUnitKind,
    SearchUnitSectionCode,
    SearchUnitText,
)
from backend.domain.attachment.identifiers import DocumentId
from backend.domain.foundation.exceptions import DomainValidationError


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
