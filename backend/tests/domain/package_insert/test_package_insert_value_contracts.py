"""添付文書Primitiveの検証と構造・集約の不変条件。"""

from dataclasses import FrozenInstanceError, fields, replace
from typing import Any

import pytest
from backend.domain.foundation.exceptions import DomainError
from backend.domain.medicine.identifiers import YjCode
from backend.domain.package_insert import primitives as p
from backend.domain.package_insert import value_objects as v
from backend.domain.package_insert.entities import PackageInsertDocument
from backend.domain.package_insert.identifiers import DocumentId


@pytest.mark.parametrize(
    "kind",
    [
        p.PackageInsertBrandName,
        p.PackageInsertEnglishName,
        p.PackageInsertSectionTitle,
        p.RevisionSourceLabel,
        p.RevisionVersion,
    ],
)
def test_original_labels_are_nonempty_and_preserve_spelling(kind):
    raw = " テストＡ①\t"
    value = kind(raw)
    assert value.value == raw
    assert value == kind(raw)
    with pytest.raises(FrozenInstanceError):
        value.value = "変更"


@pytest.mark.parametrize(
    "kind",
    [
        p.PackageInsertBrandName,
        p.PackageInsertEnglishName,
        p.PackageInsertSectionTitle,
        p.RevisionSourceLabel,
        p.RevisionVersion,
    ],
)
@pytest.mark.parametrize("raw", ["", " \t　", None, 0, False, [], {}])
def test_original_labels_reject_invalid_values(kind, raw):
    with pytest.raises(DomainError):
        kind(raw)


@pytest.mark.parametrize("raw", [-1, True, False, 1.0, "0", None])
def test_source_order_rejects_invalid_values(raw):
    with pytest.raises(DomainError):
        p.PackageInsertSourceOrder(raw)


def test_source_order_is_zero_based_and_not_part_of_context_equality():
    first = v.PackageInsertContext(source_order=p.PackageInsertSourceOrder(0))
    assert first == v.PackageInsertContext(source_order=p.PackageInsertSourceOrder(9))
    assert first.source_order is not None
    assert first.source_order.value == 0


@pytest.mark.parametrize("raw", ["0000-01", "2026-00", "2026-13", "2026/01", "٢٠٢٦-01"])
def test_revision_month_rejects_invalid_calendar_values(raw):
    with pytest.raises(DomainError):
        p.RevisionYearMonth(raw)


@pytest.mark.parametrize("raw", ["0001-01", "9999-12", "２０２６-０１"])
def test_revision_month_accepts_valid_normalized_dates(raw):
    assert p.RevisionYearMonth(raw).value in {"0001-01", "9999-12", "2026-01"}


def examples() -> list[Any]:
    context = v.PackageInsertContext()
    reference = v.PackageInsertReference(label=p.PackageInsertText("原文"))
    cell = v.PackageInsertTableCell(
        text=p.PackageInsertText(""), column=p.PackageInsertColumnIndex(0)
    )
    table = v.PackageInsertTable(columns=(p.PackageInsertText("列"),), rows=((cell,),))
    paragraph = v.PackageInsertParagraph(text=p.PackageInsertText("\n 原文Ａ① "))
    section = v.PackageInsertSection(
        code=p.NumberedSectionCode("10"), title=p.PackageInsertSectionTitle("相互作用")
    )
    source = v.PackageInsertSource(p.PackageInsertUrl("https://example.test/original"))
    return [
        v.SectionDefinition(
            code=p.NumberedSectionCode("10"),
            title=p.DefinitionTitle("項目"),
            scope=p.SectionScope("テスト項目の範囲"),
        ),
        v.SectionTaxonomy(sections=()),
        v.InteractionColumnDefinition(
            id=p.InteractionColumnId("drug_name"), title=p.DefinitionTitle("薬剤名等")
        ),
        v.RegistrationVersion(
            document_id=DocumentId("doc"),
            source_sha256=p.PackageInsertSha256("a" * 64),
            yj_codes=frozenset({YjCode("1234567A0000")}),
            revised_at=p.RevisionYearMonth("2026-01"),
        ),
        v.PackageInsertReferenceTarget(
            reference_id=p.PackageInsertText("id"), text=p.PackageInsertText("原文")
        ),
        context,
        reference,
        cell,
        table,
        paragraph,
        v.PackageInsertTableBlock(table=table),
        v.PackageInsertFigure(
            reference=p.PackageInsertText("fig1"), description=p.PackageInsertText("")
        ),
        v.PackageInsertBody(),
        v.PackageInsertMetadata({}),
        v.PackageInsertProductRevision({}),
        v.PackageInsertRevision(
            p.RevisionSourceLabel("今回"),
            p.RevisionYearMonth("2026-01"),
            p.RevisionVersion("第1版"),
        ),
        source,
        v.PackageInsertProduct(
            p.PackageInsertProductCode("code"), p.PackageInsertBrandName("テスト薬")
        ),
        section,
        v.MedicineDocumentReference(
            DocumentId("doc"), p.PmdaUrl("url"), v.PackageInsertProductRevision({})
        ),
        PackageInsertDocument(document_id=DocumentId("doc"), source=source),
    ]


EXAMPLES = examples()


def test_defaults_and_optional_absence_are_valid_and_values_are_frozen():
    for value in EXAMPLES:
        assert replace(value) == value
        with pytest.raises(FrozenInstanceError):
            setattr(value, fields(value)[0].name, None)


def test_registration_uses_yj_primitive_contract_without_second_regex():
    value = next(
        value for value in EXAMPLES if isinstance(value, v.RegistrationVersion)
    )
    assert replace(
        value, yj_codes=frozenset({YjCode("1234567a0000")})
    ).yj_codes == frozenset({YjCode("1234567a0000")})


def test_registration_requires_a_nonempty_product_set():
    value = next(
        value for value in EXAMPLES if isinstance(value, v.RegistrationVersion)
    )
    with pytest.raises(DomainError, match="at least one YJ"):
        replace(value, yj_codes=frozenset())
