from dataclasses import replace

import pytest
from backend.domain.package_insert import primitives as p
from backend.domain.package_insert import value_objects as v
from backend.domain.package_insert.entities import PackageInsertDocument
from backend.domain.package_insert.exceptions import PackageInsertDomainError
from backend.domain.package_insert.identifiers import DocumentId
from backend.infrastructure.persistence.mappings.package_insert_document_mapping import (
    document_from_payload,
    document_to_payload,
)


def document(target, *, cell):
    reference = v.PackageInsertReference(
        label=p.PackageInsertText("参照"), target_id=target
    )
    block = (
        v.PackageInsertTableBlock(
            table=v.PackageInsertTable(
                columns=(p.PackageInsertText("列"),),
                rows=(
                    (
                        v.PackageInsertTableCell(
                            text=p.PackageInsertText("本文"),
                            column=p.PackageInsertColumnIndex(0),
                            references=(reference,),
                        ),
                    ),
                ),
            )
        )
        if cell
        else v.PackageInsertParagraph(
            text=p.PackageInsertText("本文"), references=(reference, reference)
        )
    )
    child = v.PackageInsertSection(
        code=p.NumberedSectionCode("10.1"),
        title=p.PackageInsertSectionTitle("子"),
        body=v.PackageInsertBody(blocks=(block,)),
    )
    return PackageInsertDocument(
        document_id=DocumentId("test"),
        source=v.PackageInsertSource(p.PackageInsertUrl("https://example.test/doc")),
        sections=(
            v.PackageInsertSection(
                code=p.NumberedSectionCode("10"),
                title=p.PackageInsertSectionTitle("親"),
                children=(child,),
            ),
        ),
        reference_targets=(
            v.PackageInsertReferenceTarget(
                reference_id=p.PackageInsertText("known"),
                text=p.PackageInsertText("参照先"),
            ),
        ),
    )


@pytest.mark.parametrize("cell", [False, True])
def test_missing_reference_target_is_rejected_on_direct_construction(cell):
    with pytest.raises(PackageInsertDomainError, match="reference target"):
        document(p.PackageInsertText("missing"), cell=cell)


@pytest.mark.parametrize("cell", [False, True])
@pytest.mark.parametrize("target", [None, p.PackageInsertText("known")])
def test_valid_and_unresolved_references_round_trip(cell, target):
    original = document(target, cell=cell)
    assert document_from_payload(document_to_payload(original)) == original


@pytest.mark.parametrize("cell", [False, True])
def test_removing_referenced_target_is_rejected(cell):
    with pytest.raises(PackageInsertDomainError, match="reference target"):
        replace(document(p.PackageInsertText("known"), cell=cell), reference_targets=())


def test_stored_missing_reference_is_reported_as_invalid_structure():
    payload = document_to_payload(document(p.PackageInsertText("known"), cell=True))
    payload["document"]["reference_targets"] = []
    with pytest.raises(ValueError, match="invalid stored package_insert structure"):
        document_from_payload(payload)
