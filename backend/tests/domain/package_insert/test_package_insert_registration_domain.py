"""原本版ごとの識別と改訂年月による採用規則の契約。"""

import hashlib
from dataclasses import replace

import pytest
from backend.domain.medicine.identifiers import YjCode
from backend.domain.package_insert.exceptions import ConflictingRevisionError
from backend.domain.package_insert.identifiers import DocumentId
from backend.domain.package_insert.primitives import (
    PackageInsertSha256,
    RevisionYearMonth,
)
from backend.domain.package_insert.services import latest_package_insert
from backend.domain.package_insert.value_objects import RegistrationVersion

A = YjCode("3339003F5020")
B = YjCode("3961008F1020")


def version(name, codes, *, document_id=None, revised_at="2026-10"):
    original = f'<document id="{name}">fixed original {name}</document>'.encode()
    return RegistrationVersion(
        document_id=DocumentId(document_id or name),
        source_sha256=PackageInsertSha256(hashlib.sha256(original).hexdigest()),
        yj_codes=frozenset(codes),
        revised_at=RevisionYearMonth(revised_at),
    )


def test_tc093_registration_versions_keep_document_identity_and_select_latest():
    old = version("O", [A, B], document_id="same-doc", revised_at="2025-10")
    new = version("N", [A], document_id="same-doc", revised_at="2026-10")
    assert old.document_id == new.document_id == DocumentId("same-doc")
    assert old.version_id != new.version_id
    assert latest_package_insert(old, new) == new
    assert latest_package_insert(new, old) == new
    assert latest_package_insert(new, new) == new
    with pytest.raises(ConflictingRevisionError):
        latest_package_insert(
            replace(old, revised_at=RevisionYearMonth("2026-10")), new
        )
