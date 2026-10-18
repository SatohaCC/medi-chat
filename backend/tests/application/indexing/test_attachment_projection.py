"""TC-008〜012: 原本と検索単位の独立した投影。"""

from dataclasses import replace

from backend.application.indexing.attachment_projection import project_attachment
from backend.domain.attachment.primitives import (
    AttachmentBrandName,
    AttachmentCellSpan,
    AttachmentColumnIndex,
    AttachmentProductCode,
    AttachmentSectionTitle,
    AttachmentText,
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
    AttachmentRevision,
    AttachmentSection,
    AttachmentTable,
    AttachmentTableBlock,
    AttachmentTableCell,
)
from backend.domain.retrieval.value_objects import (
    SearchFigure,
    SearchParagraph,
    SearchTableBlock,
)
from backend.tests.domain.attachment.test_attachment_domain import _document


def test_original_body_and_revision_order_survive_projection():
    blocks = (
        AttachmentParagraph(text=AttachmentText(" 前 Ａ①\n ")),
        AttachmentTableBlock(
            table=AttachmentTable(
                columns=(AttachmentText("列"),),
                rows=(
                    (
                        AttachmentTableCell(
                            text=AttachmentText("表"), column=AttachmentColumnIndex(0)
                        ),
                    ),
                ),
            )
        ),
        AttachmentFigure(
            reference=AttachmentText("figure.gif"),
            description=AttachmentText(" 図の説明 "),
        ),
        AttachmentParagraph(text=AttachmentText("後")),
    )
    revisions = (
        AttachmentRevision(
            source_label=RevisionSourceLabel("以前"),
            year_month=RevisionYearMonth("2020-01"),
            version=RevisionVersion("1"),
            metadata=AttachmentMetadata({"unknown": ["残す"]}),
        ),
        AttachmentRevision(
            source_label=RevisionSourceLabel("今回"),
            year_month=RevisionYearMonth("2026-10"),
            version=RevisionVersion("2"),
        ),
    )
    document = replace(
        _document(),
        revisions=revisions,
        sections=(
            AttachmentSection(
                NumberedSectionCode("1"),
                AttachmentSectionTitle("警告"),
                AttachmentBody(blocks=blocks),
            ),
        ),
    )
    (unit,) = project_attachment(document)
    assert unit.section_title is not None
    assert unit.section_title.value == "警告"
    assert document.sections[0].body is not None
    assert document.sections[0].body.blocks == blocks
    assert [type(block).__name__ for block in unit.blocks] == [
        "SearchParagraph",
        "SearchTableBlock",
        "SearchFigure",
        "SearchParagraph",
    ]
    first = unit.blocks[0]
    figure = unit.blocks[2]
    assert isinstance(first, SearchParagraph)
    assert isinstance(figure, SearchFigure)
    assert first.text.value == " 前 Ａ①\n "
    assert figure.description.value == " 図の説明 "
    assert figure.reference.value == "figure.gif"
    assert [revision["year_month"] for revision in unit.revisions] == [
        "2020-01",
        "2026-10",
    ]
    assert unit.revisions[0]["metadata"] == {"unknown": ["残す"]}


def test_major_number_owns_child_bodies_even_without_own_body():
    def section(code, text):
        return AttachmentSection(
            NumberedSectionCode(code),
            AttachmentSectionTitle("項目"),
            AttachmentBody(
                blocks=()
                if text is None
                else (AttachmentParagraph(text=AttachmentText(text)),)
            ),
        )

    document = replace(
        _document(),
        sections=(
            replace(section("1", "親本文"), children=(section("1.1", "子本文"),)),
            replace(section("2", None), children=(section("2.1", "別の子"),)),
        ),
    )
    units = project_attachment(document)
    assert [unit.unit_id.value for unit in units] == [
        "doc-001:1",
        "doc-001:2",
    ]
    assert units[0].text.value == "親本文\n\n1.1 項目\n\n子本文"
    assert units[1].text.value == "2.1 項目\n\n別の子"
    assert len(document.sections) == 2


def test_source_independent_nested_sections_keep_heading_presence_and_child_ownership():
    child = AttachmentSection(
        NumberedSectionCode("10.1"),
        AttachmentSectionTitle("併用禁忌"),
        AttachmentBody(blocks=(AttachmentParagraph(text=AttachmentText("本文")),)),
        header=None,
    )
    major = AttachmentSection(
        NumberedSectionCode("10"),
        AttachmentSectionTitle("相互作用"),
        children=(child,),
    )
    document = replace(_document(), sections=(major,))
    (unit,) = project_attachment(document)
    assert unit.section_code.value == "10"
    block = unit.blocks[0]
    assert isinstance(block, SearchParagraph)
    assert block.context.section_code is not None
    assert block.context.section_code.value == "10.1"
    assert not block.is_heading
    assert document.sections[0].header is None
    assert document.sections[0].children == (child,)


def test_tables_keep_columns_spans_newlines_and_references_in_one_unit():
    table = AttachmentTable(
        columns=(
            AttachmentText("分類"),
            AttachmentText("頻度"),
            AttachmentText("症状"),
        ),
        rows=(
            (
                AttachmentTableCell(
                    text=AttachmentText("消化器"),
                    column=AttachmentColumnIndex(0),
                    rowspan=AttachmentCellSpan(2),
                ),
                AttachmentTableCell(
                    text=AttachmentText("頻度不明\n注意"),
                    column=AttachmentColumnIndex(1),
                    colspan=AttachmentCellSpan(2),
                    references=(
                        AttachmentReference(
                            label=AttachmentText("文献1"),
                            target_id=AttachmentText("ref1"),
                            metadata=AttachmentMetadata({"extra": ["保持"]}),
                        ),
                    ),
                ),
            ),
            (
                AttachmentTableCell(
                    text=AttachmentText("悪心\n嘔吐"),
                    column=AttachmentColumnIndex(1),
                    colspan=AttachmentCellSpan(2),
                ),
            ),
        ),
    )
    body = AttachmentBody(blocks=(AttachmentTableBlock(table=table),))
    children = tuple(
        AttachmentSection(
            NumberedSectionCode(code),
            AttachmentSectionTitle("表"),
            body if "." in code else None,
        )
        for code in ("10", "10.1", "10.2", "11", "11.2")
    )
    sections = (
        replace(children[0], children=(children[1], children[2])),
        replace(children[3], children=(children[4],)),
    )
    units = project_attachment(replace(_document(), sections=sections))
    assert [unit.section_code.value for unit in units] == ["10", "11"]
    assert [len(unit.blocks) for unit in units] == [2, 1]
    for unit in units:
        block = unit.blocks[0]
        assert isinstance(block, SearchTableBlock)
        snapshot = block.table
        assert [column.value for column in snapshot.columns] == ["分類", "頻度", "症状"]
        assert [
            (cell.column, cell.rowspan, cell.colspan, cell.text.value)
            for row in snapshot.rows
            for cell in row
        ] == [(0, 2, 1, "消化器"), (1, 1, 2, "頻度不明\n注意"), (1, 1, 2, "悪心\n嘔吐")]
        target_id = snapshot.rows[0][1].references[0].target_id
        assert target_id is not None
        assert target_id.value == "ref1"
        exported = snapshot.rows[0][1].references[0].metadata.to_dict()
        exported_values = exported["extra"]
        assert isinstance(exported_values, list)
        exported_values.clear()
        assert snapshot.rows[0][1].references[0].metadata["extra"] == ["保持"]
        assert snapshot is not table


def test_common_and_product_specific_contexts_stay_in_one_number():
    product_a = AttachmentProductCode("A")
    product_b = AttachmentProductCode("B")
    blocks = (
        AttachmentParagraph(text=AttachmentText("共通")),
        AttachmentParagraph(
            text=AttachmentText("Aのみ"),
            context=AttachmentContext(
                product_codes=(product_a,), labels=(AttachmentText(" Ａ製品 "),)
            ),
        ),
        AttachmentParagraph(
            text=AttachmentText("Bのみ"),
            context=AttachmentContext(product_codes=(product_b,)),
        ),
    )
    document = replace(
        _document(),
        products=(
            AttachmentProduct(product_a, AttachmentBrandName("製品A")),
            AttachmentProduct(product_b, AttachmentBrandName("製品B")),
        ),
        sections=(
            AttachmentSection(
                NumberedSectionCode("1"),
                AttachmentSectionTitle("警告"),
                AttachmentBody(blocks=blocks),
            ),
        ),
    )
    (unit,) = project_attachment(document)
    assert tuple(code.value for code in unit.product_codes) == ("A", "B")
    assert [
        tuple(code.value for code in block.context.product_codes)
        for block in unit.blocks
    ] == [(), ("A",), ("B",)]
    assert unit.blocks[1].context.labels[0].value == " Ａ製品 "
    assert unit.text.value == "共通\n\nAのみ\n\nBのみ"
