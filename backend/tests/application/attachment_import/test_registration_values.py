"""原本の製品コードを公開YJ Primitiveへ明示変換する登録境界。"""

import pytest
from backend.application.attachment_import.registration_contract import (
    registration_version,
)
from backend.domain.attachment.entities import AttachmentDocument
from backend.domain.attachment.exceptions import MissingOrInvalidYjError
from backend.domain.attachment.identifiers import DocumentId
from backend.domain.attachment.primitives import (
    AttachmentBrandName,
    AttachmentProductCode,
    AttachmentSha256,
    AttachmentUrl,
    RevisionSourceLabel,
    RevisionVersion,
    RevisionYearMonth,
)
from backend.domain.attachment.value_objects import (
    AttachmentProduct,
    AttachmentRevision,
    AttachmentSource,
)
from backend.domain.medicine.identifiers import YjCode


def document(code):
    return AttachmentDocument(
        document_id=DocumentId("test-document"),
        source=AttachmentSource(
            AttachmentUrl("https://example.test/original"), AttachmentSha256("a" * 64)
        ),
        revisions=(
            AttachmentRevision(
                RevisionSourceLabel("今回"),
                RevisionYearMonth("2026-01"),
                RevisionVersion("第1版"),
            ),
        ),
        products=(
            AttachmentProduct(
                AttachmentProductCode(code), AttachmentBrandName("テスト薬")
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
