"""TC-006〜009: 原本本文の不変条件。"""

from collections.abc import MutableSequence
from dataclasses import replace
from typing import cast

import pytest
from backend.domain.attachment.exceptions import AttachmentDomainError
from backend.domain.attachment.primitives import (
    AttachmentColumnIndex,
    AttachmentText,
)
from backend.domain.attachment.value_objects import (
    AttachmentBlock,
    AttachmentBody,
    AttachmentContext,
    AttachmentMetadata,
    AttachmentParagraph,
    AttachmentReference,
    AttachmentReferenceTarget,
    AttachmentTable,
    AttachmentTableBlock,
    AttachmentTableCell,
)
from backend.domain.foundation.exceptions import DomainValidationError
from backend.domain.foundation.json_types import JsonValue
from backend.tests.test_attachment_domain import _document


@pytest.mark.parametrize("raw", ["", "  ", " Ａ①\n本文\n "])
def test_original_text_preserves_empty_whitespace_and_characters(raw):
    assert AttachmentText(raw).value == raw
    assert AttachmentText(raw) is not None
    absent = _document().sections[0]
    present = replace(
        absent,
        body=AttachmentBody(blocks=(AttachmentParagraph(text=AttachmentText(raw)),)),
    )
    assert absent.body is None
    assert present.body is not None
    paragraph = present.body.blocks[0]
    assert isinstance(paragraph, AttachmentParagraph)
    assert paragraph.text.value == raw


@pytest.mark.parametrize("raw", [None, 123])
def test_original_text_rejects_non_strings(raw):
    with pytest.raises(DomainValidationError):
        AttachmentText(raw)


def test_document_rejects_ambiguous_reference_targets():
    with pytest.raises(AttachmentDomainError, match="duplicate reference"):
        replace(
            _document(),
            reference_targets=(
                AttachmentReferenceTarget(
                    reference_id=AttachmentText("ref1"), text=AttachmentText("先")
                ),
                AttachmentReferenceTarget(
                    reference_id=AttachmentText("ref1"), text=AttachmentText("別")
                ),
            ),
        )


def test_content_is_deeply_immutable_and_metadata_reads_are_independent():
    raw_values: list[JsonValue] = ["原文"]
    raw_metadata: dict[str, JsonValue] = {"unknown": raw_values}
    references = [
        AttachmentReference(
            label=AttachmentText("参照"), metadata=AttachmentMetadata(raw_metadata)
        )
    ]
    labels = [AttachmentText(" Ａ① ")]
    cells = [
        AttachmentTableCell(
            text=AttachmentText("セル\n改行"),
            column=AttachmentColumnIndex(0),
            references=tuple(references),
        )
    ]
    rows = [tuple(cells)]
    blocks = [
        AttachmentTableBlock(
            table=AttachmentTable(columns=(AttachmentText("列"),), rows=tuple(rows)),
            context=AttachmentContext(labels=tuple(labels)),
        )
    ]
    body = AttachmentBody(blocks=tuple(blocks))
    raw_values.clear()
    references.clear()
    labels.clear()
    cells.clear()
    rows.clear()
    blocks.clear()
    block = body.blocks[0]
    assert isinstance(block, AttachmentTableBlock)
    assert block.context.labels[0].value == " Ａ① "
    cell = block.table.rows[0][0]
    assert cell.text.value == "セル\n改行"
    exported = cell.references[0].metadata.to_dict()
    exported_values = exported["unknown"]
    assert isinstance(exported_values, list)
    exported_values.clear()
    assert cell.references[0].metadata["unknown"] == ["原文"]
    with pytest.raises((AttributeError, TypeError)):
        cast(MutableSequence[AttachmentTableCell], block.table.rows[0])[0] = cell


def test_body_rejects_mutable_input_collection():
    with pytest.raises(AttachmentDomainError, match="tuple"):
        AttachmentBody(
            blocks=cast(
                tuple[AttachmentBlock, ...],
                [AttachmentParagraph(text=AttachmentText("本文"))],
            )
        )
