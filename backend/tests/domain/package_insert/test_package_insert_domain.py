"""添付文書 bounded context のドメインモデルを検証する。"""

from dataclasses import FrozenInstanceError, replace

import pytest
from backend.domain.foundation.exceptions import DomainValidationError
from backend.domain.foundation.primitives.primitives import BaseHttpUrl
from backend.domain.package_insert.entities import (
    PackageInsertDocument,
)
from backend.domain.package_insert.exceptions import PackageInsertDomainError
from backend.domain.package_insert.identifiers import DocumentId
from backend.domain.package_insert.primitives import (
    NumberedSectionCode,
    PackageInsertBrandName,
    PackageInsertEnglishName,
    PackageInsertProductCode,
    PackageInsertSectionTitle,
    PackageInsertSha256,
    PackageInsertUrl,
    RevisionSourceLabel,
    RevisionVersion,
    RevisionYearMonth,
    SectionCode,
)
from backend.domain.package_insert.value_objects import (
    PackageInsertProduct,
    PackageInsertRevision,
    PackageInsertSection,
    PackageInsertSource,
)


@pytest.mark.parametrize("url_type", [BaseHttpUrl, PackageInsertUrl])
@pytest.mark.parametrize(
    "url",
    [
        "https://example.test/a①?q=Ａ#②",
        "https://example.test/a%2Fb?q=%EF%BC%A1",
        "http://example.test:8080/doc",
        "https://[::1]/doc",
    ],
)
def test_package_insert_url_preserves_reference(
    url_type: type[BaseHttpUrl], url: str
) -> None:
    assert url_type(f"  {url}  ").value == url


@pytest.mark.parametrize("url_type", [BaseHttpUrl, PackageInsertUrl])
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
def test_package_insert_url_rejects_invalid_reference_with_domain_error(
    url_type: type[BaseHttpUrl], url: str
) -> None:
    with pytest.raises(DomainValidationError):
        url_type(url)


@pytest.mark.parametrize("url_type", [BaseHttpUrl, PackageInsertUrl])
def test_package_insert_url_rejects_non_string_with_domain_error(
    url_type: type[BaseHttpUrl],
) -> None:
    with pytest.raises(DomainValidationError):
        url_type(None)  # type: ignore[arg-type]


def test_revision_preserves_labels_and_normalizes_month() -> None:
    revision = PackageInsertRevision(
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


def _document() -> PackageInsertDocument:
    return PackageInsertDocument(
        document_id=DocumentId(" doc-001 "),
        source=PackageInsertSource(
            pmda_url=PackageInsertUrl(
                " https://www.pmda.go.jp/PmdaSearch/iyakuDetail/doc-001 "
            ),
            sha256=PackageInsertSha256("A" * 64),
        ),
        revisions=(
            PackageInsertRevision(
                source_label=RevisionSourceLabel("今回"),
                year_month=RevisionYearMonth("2026-08"),
                version=RevisionVersion("第5版"),
            ),
        ),
        products=(
            PackageInsertProduct(
                PackageInsertProductCode("1141007F1063"),
                PackageInsertBrandName("カロナール錠200"),
            ),
        ),
        sections=(
            PackageInsertSection(
                NumberedSectionCode("1"),
                PackageInsertSectionTitle("警告"),
                children=(
                    PackageInsertSection(
                        NumberedSectionCode("1.1"),
                        PackageInsertSectionTitle("重要な警告"),
                    ),
                ),
            ),
        ),
    )


def test_package_insert_primitives_normalize_and_validate() -> None:
    assert DocumentId("  doc-001  ").value == "doc-001"
    assert SectionCode(" １.１ ").value == "1.1"
    with pytest.raises(DomainValidationError):
        DocumentId(" ")
    with pytest.raises(DomainValidationError):
        SectionCode("1.a").require_numbered()


@pytest.mark.parametrize(
    "primitive",
    [
        PackageInsertBrandName,
        PackageInsertEnglishName,
        PackageInsertSectionTitle,
    ],
)
def test_package_insert_text_primitives_preserve_original_and_reject_empty(
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
    product = PackageInsertProduct(
        PackageInsertProductCode("code"), PackageInsertBrandName("販売名")
    )
    assert product.english_name is None
    assert PackageInsertSource(PackageInsertUrl("https://example.test")).sha256 is None


def test_nested_section_ownership_and_duplicate_numbers_are_enforced() -> None:
    child = PackageInsertSection(
        NumberedSectionCode("10.1"), PackageInsertSectionTitle("子")
    )
    major = PackageInsertSection(
        NumberedSectionCode("10"), PackageInsertSectionTitle("親"), children=(child,)
    )
    assert major.walk() == (major, child)
    assert replace(_document(), sections=(major,)).sections == (major,)
    with pytest.raises(PackageInsertDomainError, match="owning parent"):
        PackageInsertSection(
            NumberedSectionCode("11"),
            PackageInsertSectionTitle("別の親"),
            children=(child,),
        )
    with pytest.raises(PackageInsertDomainError, match="duplicate sections"):
        replace(_document(), sections=(major, child))


def test_package_insert_document_keeps_immutable_value_objects_and_invariants() -> None:
    document = _document()

    assert document.document_id.value == "doc-001"
    with pytest.raises((FrozenInstanceError, AttributeError)):
        document.document_id = DocumentId("changed")  # type: ignore[misc]

    with pytest.raises(PackageInsertDomainError):
        PackageInsertDocument(
            document_id=DocumentId("doc-001"),
            source=document.source,
            revisions=document.revisions,
            products=(
                PackageInsertProduct(
                    PackageInsertProductCode("1141007F1063"),
                    PackageInsertBrandName("A"),
                ),
                PackageInsertProduct(
                    PackageInsertProductCode("1141007F1063"),
                    PackageInsertBrandName("B"),
                ),
            ),
            sections=document.sections,
        )


@pytest.mark.parametrize(
    "sections",
    [
        (
            PackageInsertSection(
                NumberedSectionCode("1"), PackageInsertSectionTitle("警告")
            ),
            PackageInsertSection(
                NumberedSectionCode("1"), PackageInsertSectionTitle("重複")
            ),
        ),
        (
            PackageInsertSection(
                NumberedSectionCode("1.1"),
                PackageInsertSectionTitle("警告"),
            ),
        ),
    ],
)
def test_document_rejects_duplicate_sections_and_missing_parent(sections):
    with pytest.raises(PackageInsertDomainError):
        replace(_document(), sections=sections)


def test_document_requires_direct_parent_and_accepts_complete_hierarchy():
    root = PackageInsertSection(
        NumberedSectionCode("1"), PackageInsertSectionTitle("親")
    )
    parent = PackageInsertSection(
        NumberedSectionCode("1.1"), PackageInsertSectionTitle("子")
    )
    child = PackageInsertSection(
        NumberedSectionCode("1.1.1"), PackageInsertSectionTitle("孫")
    )
    with pytest.raises(PackageInsertDomainError, match="section parent must exist"):
        replace(_document(), sections=(root, child))
    with pytest.raises(PackageInsertDomainError, match="major sections"):
        replace(_document(), sections=(child, root, parent))
    parent = replace(parent, children=(child,))
    root = replace(root, children=(parent,))
    document = replace(_document(), sections=(root,))
    assert document.sections[0].walk() == (root, parent, child)
