"""DM-15/16: 実ドメイン値のネスト情報保持と変更耐性。"""

from collections.abc import Mapping
from contextlib import suppress
from copy import deepcopy

import pytest
from backend.application.indexing.medicine_catalog import _ProductGroup
from backend.domain.attachment.entities import AttachmentProductRecord
from backend.domain.attachment.identifiers import DocumentId
from backend.domain.attachment.primitives import PmdaUrl, ProductGroupId
from backend.domain.attachment.value_objects import (
    AttachmentProductMatch,
    AttachmentProductRevision,
)
from backend.domain.foundation.exceptions import DomainValidationError
from backend.domain.json_types import JsonValue
from backend.domain.medicine.identifiers import YjCode
from backend.domain.retrieval.primitives import DetectionSource, Probability
from backend.tests.test_evidence_collection import make_evidence


def test_domain_primitives_validate_and_remain_immutable():
    document_id = DocumentId("  document-1  ")
    assert document_id.value == "document-1"
    with pytest.raises(DomainValidationError):
        DocumentId(123)  # pyright: ignore[reportArgumentType]
    with pytest.raises(DomainValidationError):
        Probability(float("nan"))
    with pytest.raises(DomainValidationError):
        Probability(1.1)
    with pytest.raises(DomainValidationError):
        DetectionSource("unknown")
    assert DetectionSource(" logic ") is DetectionSource.LOGIC
    with pytest.raises(AttributeError):
        document_id.value = "changed"  # pyright: ignore[reportAttributeAccessIssue]


def test_medicine_match_is_a_deeply_immutable_value_object():
    brand_names = ["商品"]
    match = AttachmentProductMatch(
        generic_name="成分",
        brand_names=tuple(brand_names),
        yj_codes=("1234567A0000",),
        document_ids=("document",),
    )
    brand_names.append("後から追加")
    assert match.brand_names == ("商品",)
    assert match.yj_codes == ("1234567A0000",)
    with pytest.raises((AttributeError, TypeError)):
        match.yj_codes = ("changed",)  # pyright: ignore[reportAttributeAccessIssue]


def test_medicine_group_keeps_aggregate_state_private():
    medicine = AttachmentProductRecord(
        document_id=DocumentId("document"),
        yj_code=YjCode("1234567A0000"),
        brand_name="商品",
        generic_name="成分",
        english_name="",
        hiragana_name="",
        pmda_url=PmdaUrl("https://example.test"),
        revision=AttachmentProductRevision({}),
    )
    group = _ProductGroup(
        ingredient_id=ProductGroupId("成分"),
        generic_name="成分",
        medicines=[medicine],
        matched_aliases=["商品"],
    )

    exposed_medicines = group.medicines
    exposed_aliases = group.matched_aliases
    exposed_medicines.clear()
    exposed_aliases.clear()

    assert group.medicines == [medicine]
    assert group.matched_aliases == ["商品"]


def test_medicine_revision_is_independent_of_input_and_public_output():
    payload: dict[str, JsonValue] = {
        "unknown": {"history": [None, {"version": "原文"}]}
    }
    expected = deepcopy(payload)
    medicines = [
        AttachmentProductRecord(
            document_id=DocumentId("自由なID"),
            yj_code=None,
            brand_name="",
            generic_name="",
            english_name="",
            hiragana_name="",
            pmda_url=PmdaUrl("https://example.test"),
            revision=AttachmentProductRevision(payload),
        )
        for _ in range(2)
    ]
    _change_revision(payload, "input changed")
    assert medicines[0].revision == expected
    output = medicines[0].revision
    with suppress(TypeError, AttributeError):
        _change_revision(output, "output changed")
    assert medicines[0].revision == medicines[1].revision == expected


def _change_revision(value: Mapping[str, JsonValue], version: str) -> None:
    unknown = value["unknown"]
    assert isinstance(unknown, dict)
    history = unknown["history"]
    assert isinstance(history, list)
    entry = history[1]
    assert isinstance(entry, dict)
    entry["version"] = version


@pytest.mark.parametrize(
    ("field", "payload"),
    [
        ("document_revision", {"history": [None, {"value": "原文"}]}),
        ("references", [{"metadata": [None, {"value": "参照原文"}]}]),
        ("section", {"code": "自由番号", "title": "原見出し"}),
        ("columns", {"drug_name": "原文列"}),
        ("product_yj_codes", ["自由な識別子"]),
    ],
)
def test_evidence_nested_values_are_independent_of_input_and_output(field, payload):
    expected = deepcopy(payload)
    first = make_evidence(**{field: payload})
    second = make_evidence(**{field: payload})
    if isinstance(payload, dict):
        payload.clear()
    else:
        payload.clear()
    actual = getattr(first, field)
    assert (
        dict(actual) == expected
        if isinstance(expected, dict)
        else [code.value for code in actual] == expected
        if field == "product_yj_codes"
        else list(actual) == expected
    )
    try:
        if field == "references":
            actual[0]["metadata"][1]["value"] = "公開変更"
        elif field == "document_revision":
            actual["history"][1]["value"] = "公開変更"
        elif isinstance(expected, dict):
            actual.clear()
        else:
            actual.clear()
    except TypeError, AttributeError:
        pass
    next_output = getattr(first, field)
    assert (
        dict(next_output) == expected
        if isinstance(expected, dict)
        else [code.value for code in next_output] == expected
        if field == "product_yj_codes"
        else list(next_output) == expected
    )
    assert first == second
    with suppress(TypeError, AttributeError):
        setattr(first, field, payload)
    assert first == second
