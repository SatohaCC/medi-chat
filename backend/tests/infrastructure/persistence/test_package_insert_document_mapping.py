"""PG-009/010: full structure, including fields excluded from equality."""

import json
from collections.abc import Mapping
from copy import deepcopy
from dataclasses import fields, is_dataclass

import pytest
from backend.domain.package_insert.entities import PackageInsertDocument
from backend.domain.package_insert.identifiers import DocumentId
from backend.domain.package_insert.primitives import (
    NumberedSectionCode,
    PackageInsertBrandName,
    PackageInsertCellSpan,
    PackageInsertColumnIndex,
    PackageInsertEnglishName,
    PackageInsertProductCode,
    PackageInsertSectionTitle,
    PackageInsertSha256,
    PackageInsertSourceOrder,
    PackageInsertText,
    PackageInsertUrl,
    RevisionSourceLabel,
    RevisionVersion,
    RevisionYearMonth,
)
from backend.domain.package_insert.value_objects import (
    PackageInsertBody,
    PackageInsertContext,
    PackageInsertFigure,
    PackageInsertMetadata,
    PackageInsertParagraph,
    PackageInsertProduct,
    PackageInsertReference,
    PackageInsertReferenceTarget,
    PackageInsertRevision,
    PackageInsertSection,
    PackageInsertSource,
    PackageInsertTable,
    PackageInsertTableBlock,
    PackageInsertTableCell,
)
from backend.infrastructure.persistence.mappings.package_insert_document_mapping import (
    document_from_payload,
    document_to_payload,
)


def complete_document() -> PackageInsertDocument:
    """Handwritten domain oracle; no decoder or persistence mapper is used."""
    context = PackageInsertContext(
        product_codes=(PackageInsertProductCode("1234567A0000"),),
        labels=(PackageInsertText(" テスト製品文脈\n"),),
        source_order=PackageInsertSourceOrder(19),
    )
    reference = PackageInsertReference(
        label=PackageInsertText("参照1"),
        target_id=PackageInsertText("ref1"),
        metadata=PackageInsertMetadata({"unknown": ["raw", {"flag": True}]}),
    )
    return PackageInsertDocument(
        document_id=DocumentId("test_complete"),
        source=PackageInsertSource(
            PackageInsertUrl("https://example.com/test.xml"),
            PackageInsertSha256("a" * 64),
        ),
        revisions=(
            PackageInsertRevision(
                RevisionSourceLabel("原本"),
                RevisionYearMonth("2026-10"),
                RevisionVersion("第2版"),
                PackageInsertMetadata({"raw": [None, 2, " 改訂 "]}),
            ),
        ),
        products=(
            PackageInsertProduct(
                PackageInsertProductCode("1234567A0000"),
                PackageInsertBrandName("テスト薬"),
                PackageInsertEnglishName("Test drug"),
            ),
        ),
        reference_targets=(
            PackageInsertReferenceTarget(
                reference_id=PackageInsertText("ref1"),
                text=PackageInsertText("原文参照\n"),
                context=context,
            ),
        ),
        sections=(
            PackageInsertSection(
                code=NumberedSectionCode("10"),
                title=PackageInsertSectionTitle("相互作用"),
                header=PackageInsertText(" 原本見出し "),
                body=PackageInsertBody(
                    text=PackageInsertText(" 原文\r\n"),
                    blocks=(
                        PackageInsertParagraph(
                            text=PackageInsertText(" 段落\n"),
                            is_heading=True,
                            context=context,
                            references=(reference,),
                        ),
                        PackageInsertTableBlock(
                            context=context,
                            references=(reference,),
                            table=PackageInsertTable(
                                columns=(
                                    PackageInsertText("薬剤名等"),
                                    PackageInsertText("機序"),
                                ),
                                column_contexts=(
                                    context,
                                    PackageInsertContext(
                                        source_order=PackageInsertSourceOrder(20)
                                    ),
                                ),
                                rows=(
                                    (
                                        PackageInsertTableCell(
                                            text=PackageInsertText(" セル "),
                                            column=PackageInsertColumnIndex(0),
                                            rowspan=PackageInsertCellSpan(2),
                                            colspan=PackageInsertCellSpan(2),
                                            references=(reference,),
                                            context=context,
                                        ),
                                    ),
                                ),
                            ),
                        ),
                        PackageInsertFigure(
                            reference=PackageInsertText("fig1.png"),
                            description=PackageInsertText("構造式"),
                            context=context,
                            references=(reference,),
                        ),
                    ),
                ),
                children=(
                    PackageInsertSection(
                        code=NumberedSectionCode("10.1"),
                        title=PackageInsertSectionTitle("併用禁忌"),
                        body=PackageInsertBody(),
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
    ].context.source_order == PackageInsertSourceOrder(19)
    assert restored.reference_targets[
        0
    ].context.source_order == PackageInsertSourceOrder(19)
    assert payload["schema_version"] == 1
    assert payload["transformer_version"] == "package-insert-domain.v1"


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
