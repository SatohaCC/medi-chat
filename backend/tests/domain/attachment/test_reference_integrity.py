from dataclasses import replace

import pytest
from backend.domain.attachment import primitives as p
from backend.domain.attachment import value_objects as v
from backend.domain.attachment.entities import AttachmentDocument
from backend.domain.attachment.exceptions import AttachmentDomainError
from backend.domain.attachment.identifiers import DocumentId
from backend.infrastructure.persistence.attachment_document_mapping import (
    document_from_payload,
    document_to_payload,
)


def document(target, *, cell):
    reference = v.AttachmentReference(label=p.AttachmentText("参照"), target_id=target)
    block = (
        v.AttachmentTableBlock(
            table=v.AttachmentTable(
                columns=(p.AttachmentText("列"),),
                rows=(
                    (
                        v.AttachmentTableCell(
                            text=p.AttachmentText("本文"),
                            column=p.AttachmentColumnIndex(0),
                            references=(reference,),
                        ),
                    ),
                ),
            )
        )
        if cell
        else v.AttachmentParagraph(
            text=p.AttachmentText("本文"), references=(reference, reference)
        )
    )
    child = v.AttachmentSection(
        code=p.NumberedSectionCode("10.1"),
        title=p.AttachmentSectionTitle("子"),
        body=v.AttachmentBody(blocks=(block,)),
    )
    return AttachmentDocument(
        document_id=DocumentId("test"),
        source=v.AttachmentSource(p.AttachmentUrl("https://example.test/doc")),
        sections=(
            v.AttachmentSection(
                code=p.NumberedSectionCode("10"),
                title=p.AttachmentSectionTitle("親"),
                children=(child,),
            ),
        ),
        reference_targets=(
            v.AttachmentReferenceTarget(
                reference_id=p.AttachmentText("known"), text=p.AttachmentText("参照先")
            ),
        ),
    )


@pytest.mark.parametrize("cell", [False, True])
def test_missing_reference_target_is_rejected_on_direct_construction(cell):
    with pytest.raises(AttachmentDomainError, match="reference target"):
        document(p.AttachmentText("missing"), cell=cell)


@pytest.mark.parametrize("cell", [False, True])
@pytest.mark.parametrize("target", [None, p.AttachmentText("known")])
def test_valid_and_unresolved_references_round_trip(cell, target):
    original = document(target, cell=cell)
    assert document_from_payload(document_to_payload(original)) == original


@pytest.mark.parametrize("cell", [False, True])
def test_removing_referenced_target_is_rejected(cell):
    with pytest.raises(AttachmentDomainError, match="reference target"):
        replace(document(p.AttachmentText("known"), cell=cell), reference_targets=())


def test_stored_missing_reference_is_reported_as_invalid_structure():
    payload = document_to_payload(document(p.AttachmentText("known"), cell=True))
    payload["document"]["reference_targets"] = []
    with pytest.raises(ValueError, match="invalid stored attachment structure"):
        document_from_payload(payload)
