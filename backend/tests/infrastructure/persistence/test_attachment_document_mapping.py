"""PG-009/010: full structure, including fields excluded from equality."""

import json
from collections.abc import Mapping
from copy import deepcopy
from dataclasses import fields, is_dataclass

import pytest
from backend.domain.attachment.entities import AttachmentDocument
from backend.domain.attachment.identifiers import DocumentId
from backend.domain.attachment.primitives import (
    AttachmentBrandName,
    AttachmentCellSpan,
    AttachmentColumnIndex,
    AttachmentEnglishName,
    AttachmentProductCode,
    AttachmentSectionTitle,
    AttachmentSha256,
    AttachmentSourceOrder,
    AttachmentText,
    AttachmentUrl,
    NumberedSectionCode,
    RevisionSourceLabel,
    RevisionVersion,
    RevisionYearMonth,
)
from backend.domain.attachment.value_objects import (
    AttachmentBody,
    AttachmentContext,
    AttachmentFigure,
    AttachmentMetadata,
    AttachmentParagraph,
    AttachmentProduct,
    AttachmentReference,
    AttachmentReferenceTarget,
    AttachmentRevision,
    AttachmentSection,
    AttachmentSource,
    AttachmentTable,
    AttachmentTableBlock,
    AttachmentTableCell,
)
from backend.infrastructure.persistence.attachment_document_mapping import (
    document_from_payload,
    document_to_payload,
)


def complete_document() -> AttachmentDocument:
    """Handwritten domain oracle; no decoder or persistence mapper is used."""
    context = AttachmentContext(
        product_codes=(AttachmentProductCode("1234567A0000"),),
        labels=(AttachmentText(" テスト製品文脈\n"),),
        source_order=AttachmentSourceOrder(19),
    )
    reference = AttachmentReference(
        label=AttachmentText("参照1"),
        target_id=AttachmentText("ref1"),
        metadata=AttachmentMetadata({"unknown": ["raw", {"flag": True}]}),
    )
    return AttachmentDocument(
        document_id=DocumentId("test_complete"),
        source=AttachmentSource(
            AttachmentUrl("https://example.com/test.xml"), AttachmentSha256("a" * 64)
        ),
        revisions=(
            AttachmentRevision(
                RevisionSourceLabel("原本"),
                RevisionYearMonth("2026-10"),
                RevisionVersion("第2版"),
                AttachmentMetadata({"raw": [None, 2, " 改訂 "]}),
            ),
        ),
        products=(
            AttachmentProduct(
                AttachmentProductCode("1234567A0000"),
                AttachmentBrandName("テスト薬"),
                AttachmentEnglishName("Test drug"),
            ),
        ),
        reference_targets=(
            AttachmentReferenceTarget(
                reference_id=AttachmentText("ref1"),
                text=AttachmentText("原文参照\n"),
                context=context,
            ),
        ),
        sections=(
            AttachmentSection(
                code=NumberedSectionCode("10"),
                title=AttachmentSectionTitle("相互作用"),
                header=AttachmentText(" 原本見出し "),
                body=AttachmentBody(
                    text=AttachmentText(" 原文\r\n"),
                    blocks=(
                        AttachmentParagraph(
                            text=AttachmentText(" 段落\n"),
                            is_heading=True,
                            context=context,
                            references=(reference,),
                        ),
                        AttachmentTableBlock(
                            context=context,
                            references=(reference,),
                            table=AttachmentTable(
                                columns=(
                                    AttachmentText("薬剤名等"),
                                    AttachmentText("機序"),
                                ),
                                column_contexts=(
                                    context,
                                    AttachmentContext(
                                        source_order=AttachmentSourceOrder(20)
                                    ),
                                ),
                                rows=(
                                    (
                                        AttachmentTableCell(
                                            text=AttachmentText(" セル "),
                                            column=AttachmentColumnIndex(0),
                                            rowspan=AttachmentCellSpan(2),
                                            colspan=AttachmentCellSpan(2),
                                            references=(reference,),
                                            context=context,
                                        ),
                                    ),
                                ),
                            ),
                        ),
                        AttachmentFigure(
                            reference=AttachmentText("fig1.png"),
                            description=AttachmentText("構造式"),
                            context=context,
                            references=(reference,),
                        ),
                    ),
                ),
                children=(
                    AttachmentSection(
                        code=NumberedSectionCode("10.1"),
                        title=AttachmentSectionTitle("併用禁忌"),
                        body=AttachmentBody(),
                    ),
                ),
            ),
        ),
    )


def observe(value: object) -> object:
    """Observe every field, deliberately bypassing dataclass equality."""
    if isinstance(value, Mapping):
        return {key: observe(item) for key, item in value.items()}
    if is_dataclass(value) and not isinstance(value, type):
        return (
            type(value).__name__,
            {
                field.name: observe(getattr(value, field.name))
                for field in fields(value)
            },
        )
    if isinstance(value, tuple):
        return tuple(observe(item) for item in value)
    return value


def test_pg009_complete_structure_survives_json_roundtrip() -> None:
    original = complete_document()
    payload = document_to_payload(original)
    restored = document_from_payload(
        json.loads(json.dumps(payload, ensure_ascii=False))
    )
    assert observe(restored) == observe(original)
    assert restored.sections[0].body is not None
    assert restored.sections[0].body.blocks[
        0
    ].context.source_order == AttachmentSourceOrder(19)
    assert restored.reference_targets[0].context.source_order == AttachmentSourceOrder(
        19
    )
    assert payload["schema_version"] == 1
    assert payload["transformer_version"] == "attachment-domain.v1"


@pytest.mark.parametrize(
    "damage",
    [
        "schema",
        "transformer",
        "missing",
        "invariant",
        "reference",
        "source_order",
        "heading",
    ],
)
def test_pg010_corrupt_structure_is_rejected(damage: str) -> None:
    payload = deepcopy(document_to_payload(complete_document()))
    if damage == "schema":
        payload["schema_version"] = 999
    elif damage == "transformer":
        payload["transformer_version"] = "future"
    elif damage == "missing":
        del payload["document"]["source"]
    elif damage == "invariant":
        payload["document"]["sections"][0]["children"][0]["code"] = "11.1"
    elif damage == "source_order":
        payload["document"]["sections"][0]["body"]["blocks"][0]["context"][
            "source_order"
        ] = True
    elif damage == "heading":
        payload["document"]["sections"][0]["body"]["blocks"][0]["is_heading"] = 1
    else:
        payload["document"]["reference_targets"] = []
    with pytest.raises(ValueError):
        document_from_payload(payload)
