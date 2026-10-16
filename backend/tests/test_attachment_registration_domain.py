"""原本版ごとの検索単位IDと不変snapshotの契約。"""

import hashlib
from dataclasses import replace

import pytest
from backend.domain.attachment.identifiers import DocumentId
from backend.domain.attachment.primitives import AttachmentSha256, RevisionYearMonth
from backend.domain.attachment.value_objects import RegistrationVersion
from backend.domain.foundation.exceptions import DomainValidationError
from backend.domain.medicine.identifiers import YjCode
from backend.domain.retrieval.entities import SearchUnit, VersionSearchSnapshot
from backend.domain.retrieval.identifiers import SearchUnitId
from backend.domain.retrieval.primitives import (
    SearchUnitKind,
    SearchUnitSectionCode,
    SearchUnitText,
)
from backend.domain.retrieval.value_objects import VersionSearchIdentity

A = YjCode("3339003F5020")
B = YjCode("3961008F1020")


def version(name, codes, *, document_id=None):
    original = f'<document id="{name}">fixed original {name}</document>'.encode()
    return RegistrationVersion(
        document_id=DocumentId(document_id or name),
        source_sha256=AttachmentSha256(hashlib.sha256(original).hexdigest()),
        yj_codes=frozenset(codes),
        revised_at=RevisionYearMonth("2026-10"),
    )


def test_tc093_version_qualified_unit_ids_keep_document_identity_and_own_rows():
    old, new = (
        version("O", [A, B], document_id="same-doc"),
        version("N", [A], document_id="same-doc"),
    )
    assert old.document_id == new.document_id == DocumentId("same-doc")
    assert old.version_id != new.version_id
    old_id = VersionSearchIdentity(
        document_id=old.document_id,
        version_id=old.version_id,
        section_code=SearchUnitSectionCode("7.2"),
    )
    new_id = VersionSearchIdentity(
        document_id=new.document_id,
        version_id=new.version_id,
        section_code=SearchUnitSectionCode("7.2"),
    )
    expected_old_sha = hashlib.sha256(
        b'<document id="O">fixed original O</document>'
    ).hexdigest()
    expected_new_sha = hashlib.sha256(
        b'<document id="N">fixed original N</document>'
    ).hexdigest()
    assert old_id.unit_id == SearchUnitId(f"same-doc:{expected_old_sha}:7.2")
    assert new_id.unit_id == SearchUnitId(f"same-doc:{expected_new_sha}:7.2")
    assert old_id.unit_id != new_id.unit_id
    old_unit = SearchUnit(
        unit_id=old_id.unit_id,
        document_id=old.document_id,
        section_code=SearchUnitSectionCode("7.2"),
        kind=SearchUnitKind("section"),
        text=SearchUnitText("old original text"),
    )
    snapshot = VersionSearchSnapshot(
        document_id=old.document_id, version_id=old.version_id, units=(old_unit,)
    )
    assert snapshot.units == (old_unit,)
    assert snapshot.units[0].text == SearchUnitText("old original text")
    with pytest.raises(DomainValidationError):
        VersionSearchSnapshot(
            document_id=old.document_id, version_id=new.version_id, units=(old_unit,)
        )
    with pytest.raises(DomainValidationError):
        VersionSearchSnapshot(
            document_id=old.document_id,
            version_id=old.version_id,
            units=(old_unit, old_unit),
        )
    with pytest.raises(DomainValidationError):
        VersionSearchSnapshot(
            document_id=old.document_id,
            version_id=old.version_id,
            units=(replace(old_unit, unit_id=SearchUnitId("same-doc:7.2")),),
        )
