"""原文を保持する値のコピー・比較・復元契約。"""

from dataclasses import FrozenInstanceError, replace

import pytest
from backend.domain.attachment.primitives import (
    AttachmentSectionTitle,
    AttachmentSha256,
    AttachmentUrl,
    NumberedSectionCode,
)
from backend.domain.attachment.value_objects import (
    AttachmentSection,
    AttachmentSource,
)
from backend.domain.foundation.exceptions import DomainValidationError
from backend.domain.retrieval.value_objects import (
    DocumentRevision,
    EvidenceColumns,
    EvidenceReference,
    EvidenceSection,
)


@pytest.mark.parametrize("value_type", [DocumentRevision, EvidenceReference])
def test_nested_metadata_is_independent_of_input_reads_and_exports(value_type):
    payload = {"unknown": {"history": [None, {"text": "原文"}]}}
    value = value_type(payload)
    payload["unknown"]["history"][1]["text"] = "入力変更"
    read = value["unknown"]
    read["history"][1]["text"] = "読取変更"
    public = value.to_dict()
    public["unknown"]["history"][1]["text"] = "出力変更"
    assert value == {"unknown": {"history": [None, {"text": "原文"}]}}
    assert replace(value) == value


@pytest.mark.parametrize(
    "value_type",
    [DocumentRevision, EvidenceReference, EvidenceSection, EvidenceColumns],
)
def test_mapping_contract_and_frozen_reconstruction(value_type):
    payload = {"code": "自由番号", "title": "原見出し"}
    value = value_type(payload)
    payload.clear()
    assert len(value) == 2
    assert list(value) == ["code", "title"]
    assert value == {"code": "自由番号", "title": "原見出し"}
    assert value != object()
    assert replace(value) == value
    with pytest.raises(KeyError):
        value["missing"]
    with pytest.raises((FrozenInstanceError, AttributeError)):
        value._data = {}
    public = value.to_dict()
    public.clear()
    assert len(value) == 2


def test_columns_default_to_empty_mapping():
    value = EvidenceColumns()
    assert value == {}
    assert value.to_dict() == {}


def test_source_hash_normalization():
    source = AttachmentSource(
        AttachmentUrl("https://example.test"), AttachmentSha256(" A" + "B" * 63 + " ")
    )
    assert source.sha256 is not None
    assert source.sha256.value == "a" + "b" * 63
    with pytest.raises(DomainValidationError):
        AttachmentSha256("invalid")


@pytest.mark.parametrize(
    ("code", "parent"),
    [("1", None), ("1.1", "1"), ("1.1.1", "1.1"), (" １０.２.３ ", "10.2")],
)
def test_section_parent_is_derived_from_normalized_code(code, parent):
    section = AttachmentSection(
        NumberedSectionCode(code), AttachmentSectionTitle("項目")
    )
    expected = NumberedSectionCode(parent) if parent is not None else None
    assert section.code.parent_code == expected
    assert section.parent_code == expected
    assert replace(
        section, code=NumberedSectionCode("2.3")
    ).parent_code == NumberedSectionCode("2")


@pytest.mark.parametrize("raw", ["a" * 63, "a" * 65, "g" * 64, "", None])
def test_source_hash_rejects_invalid_digest(raw):
    with pytest.raises(DomainValidationError):
        AttachmentSha256(raw)
