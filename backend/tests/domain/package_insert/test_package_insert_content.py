"""TC-006〜009: 原本本文の不変条件。"""

from collections.abc import MutableSequence
from dataclasses import replace
from typing import cast

import pytest
from backend.domain.foundation.exceptions import DomainValidationError
from backend.domain.foundation.json_types import JsonValue
from backend.domain.package_insert.exceptions import PackageInsertDomainError
from backend.domain.package_insert.primitives import (
    PackageInsertColumnIndex,
    PackageInsertText,
)
from backend.domain.package_insert.value_objects import (
    PackageInsertBody,
    PackageInsertContext,
    PackageInsertMetadata,
    PackageInsertParagraph,
    PackageInsertReference,
    PackageInsertReferenceTarget,
    PackageInsertTable,
    PackageInsertTableBlock,
    PackageInsertTableCell,
)
from backend.tests.domain.package_insert.test_package_insert_domain import _document


@pytest.mark.parametrize("raw", ["", "  ", " Ａ①\n本文\n "])
def test_original_text_preserves_empty_whitespace_and_characters(raw):
    assert PackageInsertText(raw).value == raw
    assert PackageInsertText(raw) is not None
    absent = _document().sections[0]
    present = replace(
        absent,
        body=PackageInsertBody(
            blocks=(PackageInsertParagraph(text=PackageInsertText(raw)),)
        ),
    )
    assert absent.body is None
    assert present.body is not None
    paragraph = present.body.blocks[0]
    assert isinstance(paragraph, PackageInsertParagraph)
    assert paragraph.text.value == raw


@pytest.mark.parametrize("raw", [None, 123])
def test_original_text_rejects_non_strings(raw):
    with pytest.raises(DomainValidationError):
        PackageInsertText(raw)


def test_document_rejects_ambiguous_reference_targets():
    with pytest.raises(PackageInsertDomainError, match="duplicate reference"):
        replace(
            _document(),
            reference_targets=(
                PackageInsertReferenceTarget(
                    reference_id=PackageInsertText("ref1"), text=PackageInsertText("先")
                ),
                PackageInsertReferenceTarget(
                    reference_id=PackageInsertText("ref1"), text=PackageInsertText("別")
                ),
            ),
        )


def test_content_is_deeply_immutable_and_metadata_reads_are_independent():
    raw_values: list[JsonValue] = ["原文"]
    raw_metadata: dict[str, JsonValue] = {"unknown": raw_values}
    references = [
        PackageInsertReference(
            label=PackageInsertText("参照"),
            metadata=PackageInsertMetadata(raw_metadata),
        )
    ]
    labels = [PackageInsertText(" Ａ① ")]
    cells = [
        PackageInsertTableCell(
            text=PackageInsertText("セル\n改行"),
            column=PackageInsertColumnIndex(0),
            references=tuple(references),
        )
    ]
    rows = [tuple(cells)]
    blocks = [
        PackageInsertTableBlock(
            table=PackageInsertTable(
                columns=(PackageInsertText("列"),), rows=tuple(rows)
            ),
            context=PackageInsertContext(labels=tuple(labels)),
        )
    ]
    body = PackageInsertBody(blocks=tuple(blocks))
    raw_values.clear()
    references.clear()
    labels.clear()
    cells.clear()
    rows.clear()
    blocks.clear()
    block = body.blocks[0]
    assert isinstance(block, PackageInsertTableBlock)
    assert block.context.labels[0].value == " Ａ① "
    cell = block.table.rows[0][0]
    assert cell.text.value == "セル\n改行"
    exported = cell.references[0].metadata.to_dict()
    exported_values = exported["unknown"]
    assert isinstance(exported_values, list)
    exported_values.clear()
    assert cell.references[0].metadata["unknown"] == ["原文"]
    with pytest.raises((AttributeError, TypeError)):
        cast(MutableSequence[PackageInsertTableCell], block.table.rows[0])[0] = cell
