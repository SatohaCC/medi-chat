"""DM-16/17: 現行JSON許容値・拒否と原文整形を固定する。"""

from copy import deepcopy
from dataclasses import replace

import pytest
from backend.domain.foundation.json_types import JsonValue
from backend.domain.medicine.identifiers import YjCode
from backend.domain.retrieval.primitives import (
    EvidenceBrandName,
    EvidenceContextLabel,
    EvidenceGenericName,
    EvidenceSourceUrl,
)
from backend.domain.retrieval.services import build_evidence as format_evidence
from backend.domain.retrieval.value_objects import EvidenceDocument, EvidenceProduct
from backend.infrastructure.evidence_mapping import build_evidence
from backend.tests.test_evidence_collection import make_evidence


def test_section_evidence_gets_current_revision_from_document_metadata():
    current: dict[str, JsonValue] = {
        "source_label": "今回",
        "year_month": "2026-10",
        "version": "第2版",
    }
    evidence = build_evidence(
        {
            "unit_id": "doc:1",
            "document_key": "doc",
            "kind": "section",
            "text": "警告本文",
        },
        {
            "document": {
                "revisions": [{"source_label": "前回", "version": "第1版"}, current]
            }
        },
        "logic",
    )
    assert evidence.to_dict()["document_revision"] == current


@pytest.mark.parametrize(
    ("generic", "products", "name"),
    [
        ("成分原文", [{"yj_code": None, "brand_name": ""}], "成分原文"),
        ("", [], "自由な文書ID"),
        ("成分原文", [{"yj_code": "自由コード", "brand_name": "商品原文"}], "商品原文"),
        (
            " Ａ成分① ",
            [{"yj_code": "自由コード", "brand_name": " Ｂ商品② "}],
            " Ｂ商品② ",
        ),
        (" Ａ成分① ", [{"yj_code": None, "brand_name": ""}], " Ａ成分① "),
    ],
)
@pytest.mark.parametrize("columns", [None, {}])
def test_allowed_values_and_original_information_are_preserved(
    generic, products, name, columns
):
    unit = {
        "unit_id": "自由な根拠ID",
        "document_key": "自由な文書ID",
        "product_yj_codes": ["自由コード"],
        "document_revision": {},
        "section": {},
        "text": "原文\n改行",
        "columns": columns,
        "references": [{"unknown": [True, None, {"text": "参照原文"}]}],
    }
    document = {
        "document": {"generic_name": generic, "products": products},
        "source": {"pmda_url": "https://example.test/document"},
    }
    before = deepcopy((unit, document))
    evidence = build_evidence(unit, document, "logic")
    assert evidence.to_dict() == {
        "unit_id": "自由な根拠ID",
        "document_id": "自由な文書ID",
        "product_name": name,
        "generic_name": generic,
        "product_yj_codes": ["自由コード"],
        "document_revision": {},
        "section": {},
        "kind": "",
        "excerpt": "原文\n改行",
        "columns": columns,
        "references": [{"unknown": [True, None, {"text": "参照原文"}]}],
        "url": "https://example.test/document",
        "retrieved_by": ["logic"],
    }
    assert (unit, document) == before


@pytest.mark.parametrize(
    ("change", "error"),
    [
        ({"unit_id": None}, TypeError),
        ({"document_key": None}, TypeError),
        ({"text": ["wrong"]}, TypeError),
        ({"section": {"code": 1}}, TypeError),
        ({"references": ["wrong"]}, TypeError),
    ],
)
def test_invalid_json_structure_is_not_fabricated_into_evidence(change, error):
    unit = {"unit_id": "id", "document_key": "doc", **change}
    with pytest.raises(error):
        build_evidence(unit, {}, "logic")


@pytest.mark.parametrize("missing", ["unit_id", "document_key"])
def test_missing_required_identifiers_are_rejected(missing):
    unit: dict[str, JsonValue] = {"unit_id": "id", "document_key": "doc"}
    unit.pop(missing)
    with pytest.raises(KeyError):
        build_evidence(unit, {}, "logic")


def test_scope_and_unit_url_have_existing_priority():
    evidence = build_evidence(
        {
            "unit_id": "id",
            "document_key": "doc",
            "text": "原見出し\n本文",
            "context_labels": ["原見出し"],
            "source": {"url": "https://example.test/unit"},
        },
        {"source": {"pmda_url": "https://example.test/document"}},
        "keyword",
    )
    assert evidence.excerpt == "原見出し\n本文"
    assert evidence.url == "https://example.test/unit"


def test_unused_invalid_document_url_and_unselected_brand_are_not_newly_rejected():
    evidence = build_evidence(
        {
            "unit_id": "id",
            "document_key": "doc",
            "product_yj_codes": ["selected"],
            "source": {"url": "unit-url"},
        },
        {
            "source": ["unused wrong type"],
            "document": {
                "products": [
                    {"yj_code": "selected", "brand_name": "選択原文"},
                    {"yj_code": "unselected", "brand_name": ["unused wrong type"]},
                ]
            },
        },
        "logic",
    )
    assert evidence.product_name == "選択原文"
    assert evidence.url == "unit-url"


def test_domain_formats_typed_original_values_without_io():
    original = replace(make_evidence(), excerpt="本文", url="")
    document = EvidenceDocument(
        EvidenceGenericName("原成分"),
        (EvidenceProduct(YjCode("1234567A0000"), EvidenceBrandName("原商品")),),
        EvidenceSourceUrl("document-url"),
    )
    formatted = format_evidence(original, document, (EvidenceContextLabel("成人"),))
    assert formatted.product_name == "原商品"
    assert formatted.generic_name == "原成分"
    assert formatted.excerpt == "〈成人〉 本文"
    assert formatted.url == "document-url"
    assert original.excerpt == "本文"


def test_mapping_normalizes_labels_without_changing_original_characters_or_order():
    evidence = build_evidence(
        {
            "unit_id": "id",
            "document_key": "doc",
            "text": "本文",
            "context_labels": [" Ａ① ", "成人", " Ａ① "],
        },
        {},
        "logic",
    )
    assert evidence.excerpt == "〈Ａ①〉 〈成人〉 〈Ａ①〉 本文"


@pytest.mark.parametrize("label", ["", "  "])
def test_mapping_rejects_empty_context_labels(label):
    from backend.domain.foundation.exceptions import DomainValidationError

    with pytest.raises(DomainValidationError):
        build_evidence(
            {"unit_id": "id", "document_key": "doc", "context_labels": [label]},
            {},
            "logic",
        )


@pytest.mark.parametrize("code", [["code"], {"code": "value"}, 123, True])
def test_product_code_is_validated_at_json_boundary(code):
    with pytest.raises(TypeError, match="JSON string"):
        build_evidence(
            {"unit_id": "id", "document_key": "doc"},
            {"document": {"products": [{"yj_code": code}]}},
            "logic",
        )


def test_product_selection_uses_normalized_ids_and_keeps_unselected_brand_unread():
    evidence = build_evidence(
        {"unit_id": "id", "document_key": "doc", "product_yj_codes": ["Ａ"]},
        {
            "document": {
                "products": [
                    {"yj_code": "A", "brand_name": "選択商品"},
                    {"yj_code": "B", "brand_name": ["未選択"]},
                ]
            }
        },
        "logic",
    )
    assert evidence.product_name == "選択商品"
    assert evidence.product_yj_codes == (YjCode("A"),)
