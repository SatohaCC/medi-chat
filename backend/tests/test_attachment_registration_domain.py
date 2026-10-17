"""原本版ごとの識別と改訂年月による採用規則の契約。"""

import hashlib
from dataclasses import replace

import pytest
from backend.domain.attachment.exceptions import ConflictingRevisionError
from backend.domain.attachment.identifiers import DocumentId
from backend.domain.attachment.primitives import AttachmentSha256, RevisionYearMonth
from backend.domain.attachment.services import latest_attachment
from backend.domain.attachment.value_objects import RegistrationVersion
from backend.domain.medicine.identifiers import YjCode

A = YjCode("3339003F5020")
B = YjCode("3961008F1020")


def version(name, codes, *, document_id=None, revised_at="2026-10"):
    original = f'<document id="{name}">fixed original {name}</document>'.encode()
    return RegistrationVersion(
        document_id=DocumentId(document_id or name),
        source_sha256=AttachmentSha256(hashlib.sha256(original).hexdigest()),
        yj_codes=frozenset(codes),
        revised_at=RevisionYearMonth(revised_at),
    )


def test_tc093_registration_versions_keep_document_identity_and_select_latest():
    old = version("O", [A, B], document_id="same-doc", revised_at="2025-10")
    new = version("N", [A], document_id="same-doc", revised_at="2026-10")
    assert old.document_id == new.document_id == DocumentId("same-doc")
    assert old.version_id != new.version_id
    assert latest_attachment(old, new) == new
    assert latest_attachment(new, old) == new
    assert latest_attachment(new, new) == new
    with pytest.raises(ConflictingRevisionError):
        latest_attachment(replace(old, revised_at=RevisionYearMonth("2026-10")), new)
