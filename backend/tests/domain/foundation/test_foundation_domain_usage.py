"""Primitiveが共通検証を使うことを検証する。"""

import pytest
from backend.domain.attachment.identifiers import DocumentId
from backend.domain.attachment.primitives import SectionCode
from backend.domain.foundation.exceptions import DomainValidationError
from backend.domain.foundation.primitives.primitives import BaseString


def test_attachment_primitives_use_foundation_normalization_and_validation():
    assert issubclass(DocumentId, BaseString)
    assert DocumentId("  doc-001  ").value == "doc-001"
    assert SectionCode(" １.１ ").value == "1.1"
    with pytest.raises(DomainValidationError):
        DocumentId(123)  # pyright: ignore[reportArgumentType]
    with pytest.raises(DomainValidationError):
        DocumentId(" ")
    with pytest.raises(DomainValidationError):
        SectionCode("1.a").require_numbered()


def test_base_string_requires_non_empty_validation():
    assert BaseString("  Ａ  B  ").value == "A  B"
    with pytest.raises(DomainValidationError):
        BaseString("")
    with pytest.raises(DomainValidationError):
        BaseString(" ")
    with pytest.raises(DomainValidationError):
        BaseString(123)  # pyright: ignore[reportArgumentType]
