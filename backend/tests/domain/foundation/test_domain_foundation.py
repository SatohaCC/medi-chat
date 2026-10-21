"""foundationの生成時検証と既存ドメインの接続契約。"""

import uuid

import pytest
from backend.application.retrieval.search_models import IntentCandidate, SearchCriteria
from backend.application.retrieval.search_values import (
    DetectionSource,
    IntentName,
    Probability,
    SearchKeyword,
)
from backend.domain.attachment.exceptions import AttachmentDomainError
from backend.domain.attachment.identifiers import DocumentId
from backend.domain.foundation.exceptions import (
    DomainError,
    DomainValidationError,
)
from backend.domain.foundation.primitives.identifiers import (
    EntityStringId,
    EntityUUID,
)
from backend.domain.foundation.primitives.primitives import BaseString


class RecordId(EntityStringId):
    pass


def test_uuid_generation_uses_standard_library_and_preserves_subclass():
    class GeneratedId(EntityUUID):
        pass

    first = GeneratedId.generate()
    second = GeneratedId.generate()
    assert type(first) is GeneratedId
    assert first.value.version == second.value.version == 7
    assert first.value.variant == uuid.RFC_4122
    assert first.value.int < second.value.int
    assert GeneratedId.parse(str(first.value)) == first
    with pytest.raises(DomainValidationError):
        GeneratedId.parse(uuid.uuid4())


def test_existing_scalar_and_search_contracts_use_foundation():
    key = DocumentId("  Ａ  ")
    assert isinstance(key, BaseString)
    assert key.value == "A"
    with pytest.raises(DomainValidationError):
        DocumentId("")
    criteria = SearchCriteria(
        DetectionSource("logic"), keywords=(SearchKeyword(" Ａ "),)
    )
    assert criteria.source.value == "logic"
    assert (
        IntentCandidate(IntentName(" interaction "), Probability(1)).probability.value
        == 1.0
    )
    with pytest.raises(DomainValidationError):
        DocumentId(123)  # pyright: ignore[reportArgumentType]
    assert issubclass(DomainValidationError, DomainError)
    assert issubclass(AttachmentDomainError, DomainError)
