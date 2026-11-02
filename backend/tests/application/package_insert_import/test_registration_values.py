"""原本の製品コードを公開YJ Primitiveへ明示変換する登録境界。"""

import pytest
from backend.application.package_insert_import.policies import registration_version
from backend.domain.medicine.identifiers import YjCode
from backend.domain.package_insert.entities import PackageInsertDocument
from backend.domain.package_insert.exceptions import MissingOrInvalidYjError
from backend.domain.package_insert.identifiers import DocumentId
from backend.domain.package_insert.primitives import (
    PackageInsertBrandName,
    PackageInsertProductCode,
    PackageInsertSha256,
    PackageInsertUrl,
    RevisionSourceLabel,
    RevisionVersion,
    RevisionYearMonth,
)
from backend.domain.package_insert.value_objects import (
    PackageInsertProduct,
    PackageInsertRevision,
    PackageInsertSource,
)


def document(code):
    return PackageInsertDocument(
        document_id=DocumentId("test-document"),
        source=PackageInsertSource(
            PackageInsertUrl("https://example.test/original"),
            PackageInsertSha256("a" * 64),
        ),
        revisions=(
            PackageInsertRevision(
                RevisionSourceLabel("今回"),
                RevisionYearMonth("2026-01"),
                RevisionVersion("第1版"),
            ),
        ),
        products=(
            PackageInsertProduct(
                PackageInsertProductCode(code), PackageInsertBrandName("テスト薬")
            ),
        ),
    )


def test_invalid_original_product_code_keeps_registration_error_category():
    with pytest.raises(MissingOrInvalidYjError):
        registration_version(document("not-yj"))


def test_registration_accepts_domain_normalization_and_lowercase():
    assert registration_version(
        document(" １２３４５６７ａ００００ ")
    ).yj_codes == frozenset({YjCode("1234567a0000")})


@pytest.mark.parametrize("chunk_bytes,expected", [(3, [3, 3, 1]), (4, [4, 3])])
def test_upload_part_size_uses_explicit_transport_setting(chunk_bytes, expected):
    from backend.application.file_upload.commands.models import UploadSpec

    spec = UploadSpec("テスト.xml", 7, "a" * 64)
    assert [
        spec.part_size(i, chunk_bytes=chunk_bytes) for i in range(len(expected))
    ] == expected
    with pytest.raises(ValueError):
        spec.part_size(len(expected), chunk_bytes=chunk_bytes)
    with pytest.raises(ValueError):
        spec.part_size(0, chunk_bytes=0)
