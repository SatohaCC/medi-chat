"""添付文書 bounded context のドメインモデルを検証する。"""

from dataclasses import FrozenInstanceError, replace

import pytest
from backend.domain.attachment.entities import (
    AttachmentDocument,
)
from backend.domain.attachment.exceptions import AttachmentDomainError
from backend.domain.attachment.identifiers import DocumentId
from backend.domain.attachment.primitives import (
    AttachmentBrandName,
    AttachmentEnglishName,
    AttachmentProductCode,
    AttachmentSectionTitle,
    AttachmentSha256,
    AttachmentUrl,
    NumberedSectionCode,
    RevisionSourceLabel,
    RevisionVersion,
    RevisionYearMonth,
    SectionCode,
)
from backend.domain.attachment.value_objects import (
    AttachmentProduct,
    AttachmentRevision,
    AttachmentSection,
    AttachmentSource,
)
from backend.domain.foundation.exceptions import DomainValidationError
from backend.domain.foundation.primitives.primitives import BaseHttpUrl


@pytest.mark.parametrize("url_type", [BaseHttpUrl, AttachmentUrl])
@pytest.mark.parametrize(
    "url",
    [
        "https://example.test/a①?q=Ａ#②",
        "https://example.test/a%2Fb?q=%EF%BC%A1",
        "http://example.test:8080/doc",
        "https://[::1]/doc",
    ],
)
def test_attachment_url_preserves_reference(
    url_type: type[BaseHttpUrl], url: str
) -> None:
    assert url_type(f"  {url}  ").value == url


@pytest.mark.parametrize("url_type", [BaseHttpUrl, AttachmentUrl])
@pytest.mark.parametrize(
    "url",
    [
        "https://@/doc",
        "https:///doc",
        "https://[bad/doc",
        "https://example.test:bad/doc",
        "https://example.test:65536/doc",
        "ftp://example.test/doc",
        "",
    ],
)
def test_attachment_url_rejects_invalid_reference_with_domain_error(
    url_type: type[BaseHttpUrl], url: str
) -> None:
    with pytest.raises(DomainValidationError):
        url_type(url)


@pytest.mark.parametrize("url_type", [BaseHttpUrl, AttachmentUrl])
def test_attachment_url_rejects_non_string_with_domain_error(
    url_type: type[BaseHttpUrl],
) -> None:
    with pytest.raises(DomainValidationError):
        url_type(None)  # type: ignore[arg-type]


def test_revision_preserves_labels_and_normalizes_month() -> None:
    revision = AttachmentRevision(
        source_label=RevisionSourceLabel(" 今回 "),
        year_month=RevisionYearMonth(" ２０２６-０８ "),
        version=RevisionVersion(" 第５版 "),
    )
    assert revision.source_label.value == " 今回 "
    assert revision.year_month.value == "2026-08"
    assert revision.version.value == " 第５版 "
    assert replace(revision) == revision
    with pytest.raises((FrozenInstanceError, AttributeError)):
        revision.version = RevisionVersion("第6版")  # type: ignore[misc]


@pytest.mark.parametrize(
    "primitive", [RevisionSourceLabel, RevisionYearMonth, RevisionVersion]
)
@pytest.mark.parametrize("raw", ["", "  ", None, 123])
def test_revision_primitives_reject_invalid_text(primitive, raw) -> None:
    with pytest.raises(DomainValidationError):
        primitive(raw)


@pytest.mark.parametrize("raw", ["2026-00", "2026-13", "2026-8", "26-08"])
def test_revision_year_month_rejects_invalid_format(raw: str) -> None:
    with pytest.raises(DomainValidationError):
        RevisionYearMonth(raw)


@pytest.mark.parametrize("raw", ["2026-01", "2026-12"])
def test_revision_year_month_accepts_month_boundaries(raw: str) -> None:
    assert RevisionYearMonth(raw).value == raw


def _document() -> AttachmentDocument:
    return AttachmentDocument(
        document_id=DocumentId(" doc-001 "),
        source=AttachmentSource(
            pmda_url=AttachmentUrl(
                " https://www.pmda.go.jp/PmdaSearch/iyakuDetail/doc-001 "
            ),
            sha256=AttachmentSha256("A" * 64),
        ),
        revisions=(
            AttachmentRevision(
                source_label=RevisionSourceLabel("今回"),
                year_month=RevisionYearMonth("2026-08"),
                version=RevisionVersion("第5版"),
            ),
        ),
        products=(
            AttachmentProduct(
                AttachmentProductCode("1141007F1063"),
                AttachmentBrandName("カロナール錠200"),
            ),
        ),
        sections=(
            AttachmentSection(
                NumberedSectionCode("1"),
                AttachmentSectionTitle("警告"),
                children=(
                    AttachmentSection(
                        NumberedSectionCode("1.1"), AttachmentSectionTitle("重要な警告")
                    ),
                ),
            ),
        ),
    )


def test_attachment_primitives_normalize_and_validate() -> None:
    assert DocumentId("  doc-001  ").value == "doc-001"
    assert SectionCode(" １.１ ").value == "1.1"
    with pytest.raises(DomainValidationError):
        DocumentId(" ")
    with pytest.raises(DomainValidationError):
        SectionCode("1.a").require_numbered()


@pytest.mark.parametrize(
    "primitive",
    [
        AttachmentBrandName,
        AttachmentEnglishName,
        AttachmentSectionTitle,
    ],
)
def test_attachment_text_primitives_preserve_original_and_reject_empty(
    primitive,
) -> None:
    assert primitive(" Ａ ").value == " Ａ "
    with pytest.raises(DomainValidationError):
        primitive(" ")
    with pytest.raises(DomainValidationError):
        primitive(None)


@pytest.mark.parametrize("raw", ["1.a", "", "1."])
def test_numbered_section_code_rejects_invalid_format(raw: str) -> None:
    with pytest.raises(DomainValidationError):
        NumberedSectionCode(raw)


def test_optional_product_name_and_source_hash_are_absent() -> None:
    product = AttachmentProduct(
        AttachmentProductCode("code"), AttachmentBrandName("販売名")
    )
    assert product.english_name is None
    assert AttachmentSource(AttachmentUrl("https://example.test")).sha256 is None


def test_nested_section_ownership_and_duplicate_numbers_are_enforced() -> None:
    child = AttachmentSection(NumberedSectionCode("10.1"), AttachmentSectionTitle("子"))
    major = AttachmentSection(
        NumberedSectionCode("10"), AttachmentSectionTitle("親"), children=(child,)
    )
    assert major.walk() == (major, child)
    assert replace(_document(), sections=(major,)).sections == (major,)
    with pytest.raises(AttachmentDomainError, match="owning parent"):
        AttachmentSection(
            NumberedSectionCode("11"),
            AttachmentSectionTitle("別の親"),
            children=(child,),
        )
    with pytest.raises(AttachmentDomainError, match="duplicate sections"):
        replace(_document(), sections=(major, child))


def test_attachment_document_keeps_immutable_value_objects_and_invariants() -> None:
    document = _document()

    assert document.document_id.value == "doc-001"
    with pytest.raises((FrozenInstanceError, AttributeError)):
        document.document_id = DocumentId("changed")  # type: ignore[misc]

    with pytest.raises(AttachmentDomainError):
        AttachmentDocument(
            document_id=DocumentId("doc-001"),
            source=document.source,
            revisions=document.revisions,
            products=(
                AttachmentProduct(
                    AttachmentProductCode("1141007F1063"), AttachmentBrandName("A")
                ),
                AttachmentProduct(
                    AttachmentProductCode("1141007F1063"), AttachmentBrandName("B")
                ),
            ),
            sections=document.sections,
        )


@pytest.mark.parametrize(
    "sections",
    [
        (
            AttachmentSection(NumberedSectionCode("1"), AttachmentSectionTitle("警告")),
            AttachmentSection(NumberedSectionCode("1"), AttachmentSectionTitle("重複")),
        ),
        (
            AttachmentSection(
                NumberedSectionCode("1.1"),
                AttachmentSectionTitle("警告"),
            ),
        ),
    ],
)
def test_document_rejects_duplicate_sections_and_missing_parent(sections):
    with pytest.raises(AttachmentDomainError):
        replace(_document(), sections=sections)


def test_document_requires_direct_parent_and_accepts_complete_hierarchy():
    root = AttachmentSection(NumberedSectionCode("1"), AttachmentSectionTitle("親"))
    parent = AttachmentSection(NumberedSectionCode("1.1"), AttachmentSectionTitle("子"))
    child = AttachmentSection(
        NumberedSectionCode("1.1.1"), AttachmentSectionTitle("孫")
    )
    with pytest.raises(AttachmentDomainError, match="section parent must exist"):
        replace(_document(), sections=(root, child))
    with pytest.raises(AttachmentDomainError, match="major sections"):
        replace(_document(), sections=(child, root, parent))
    parent = replace(parent, children=(child,))
    root = replace(root, children=(parent,))
    document = replace(_document(), sections=(root,))
    assert document.sections[0].walk() == (root, parent, child)
