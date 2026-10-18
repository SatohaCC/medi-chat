"""原本にない見出しを作らず、大項目単位で保存する受入テスト。"""

import json

import pytest
from backend.application.indexing.attachment_projection import (
    project_active_attachment,
    project_attachment,
)
from backend.domain.attachment.value_objects import AttachmentTableBlock
from backend.domain.medicine.identifiers import YjCode
from backend.domain.retrieval.value_objects import SearchParagraph, SearchTableBlock
from backend.infrastructure.index_payloads import (
    build_index_document,
    encode_registered_units,
    registered_unit_text,
)
from backend.infrastructure.pmda_xml.artifact_mapping import PmdaArtifactEncoder
from backend.infrastructure.pmda_xml.decoder import PmdaXmlDecoder, SourceInformation
from backend.tests.support.attachment_import_fixtures import (
    encoded,
    json_artifact,
    xml_source,
)


@pytest.mark.parametrize("active", [False, True])
def test_major_projection_preserves_interleaved_parent_and_child_order(active):
    source = xml_source(
        "<Interactions><Detail><Lang>PARENT_BEFORE</Lang></Detail>"
        '<ContraIndicatedCombinations id="s101"><Detail><Lang>CHILD_FIRST</Lang>'
        "</Detail></ContraIndicatedCombinations>"
        "<Detail><Lang>PARENT_BETWEEN</Lang></Detail>"
        '<PrecautionsForCombinations id="s102"><Detail><Lang>CHILD_SECOND</Lang>'
        "</Detail></PrecautionsForCombinations>"
        '<Detail><Lang>PARENT_AFTER</Lang><HeaderRef ref="s101"/></Detail></Interactions>'
    )
    decoded = PmdaXmlDecoder().decode(source)
    units = (
        project_active_attachment(decoded.document, frozenset({YjCode("111111111111")}))
        if active
        else project_attachment(decoded.document)
    )
    (unit,) = units
    expected = [
        "PARENT_BEFORE",
        "CHILD_FIRST",
        "PARENT_BETWEEN",
        "CHILD_SECOND",
        "PARENT_AFTER",
    ]
    paragraphs = [block for block in unit.blocks if isinstance(block, SearchParagraph)]
    assert len(paragraphs) == len(unit.blocks)
    assert [block.text.value for block in paragraphs] == expected
    assert [
        block.context.section_code.value if block.context.section_code else None
        for block in unit.blocks
    ] == [
        "10",
        "10.1",
        "10",
        "10.2",
        "10",
    ]
    positions = [unit.text.value.index(text) for text in expected]
    assert positions == sorted(positions)
    bundle = PmdaArtifactEncoder().encode(decoded.document, units, decoded.source_info)
    saved = json.loads(
        next(file.content for file in bundle.files if file.name == "search_units.jsonl")
        .decode()
        .splitlines()[0]
    )
    positions = [saved["text"].index(text) for text in expected]
    assert positions == sorted(positions)
    assert [block["context"]["section"]["code"] for block in saved["blocks"]] == [
        "10",
        "10.1",
        "10",
        "10.2",
        "10",
    ]
    assert saved["blocks"][-1]["references"][0]["target_section_code"] == "10.1"


def test_parent_table_rows_separated_by_child_are_not_merged():
    def drug(text):
        return (
            f"<Drug><DrugName><Lang>{text}</Lang></DrugName>"
            "<ClinSymptomsAndMeasures><Lang>SYMPTOM</Lang></ClinSymptomsAndMeasures></Drug>"
        )

    source = xml_source(
        "<Interactions>"
        + drug("BEFORE")
        + '<ContraIndicatedCombinations id="s101"><Detail><Lang>CHILD</Lang></Detail>'
        "</ContraIndicatedCombinations>" + drug("AFTER") + "</Interactions>"
    )
    (unit,) = project_attachment(PmdaXmlDecoder().decode(source).document)
    assert [type(block) for block in unit.blocks] == [
        SearchTableBlock,
        SearchParagraph,
        SearchTableBlock,
    ]
    tables = [block for block in unit.blocks if isinstance(block, SearchTableBlock)]
    assert [len(block.table.rows) for block in tables] == [1, 1]
    assert [block.table.rows[0][0].text.value for block in tables] == [
        "BEFORE",
        "AFTER",
    ]


def test_major_section_is_one_saved_record_with_original_children():
    source = xml_source(
        '<Interactions id="s10"><Detail><Lang>相互作用の本文</Lang></Detail>'
        '<ContraIndicatedCombinations id="s101"><Detail><Lang>禁忌の本文</Lang>'
        '<HeaderRef ref="s102"/></Detail></ContraIndicatedCombinations>'
        '<PrecautionsForCombinations id="s102"><Detail><Lang>注意の本文</Lang>'
        "</Detail></PrecautionsForCombinations></Interactions>"
    )
    decoded = PmdaXmlDecoder().decode(source)
    assert [section.code.value for section in decoded.document.sections] == ["10"]
    (major,) = decoded.document.sections
    assert [child.code.value for child in major.children] == ["10.1", "10.2"]
    assert major.header is None
    assert all(child.header is None for child in major.children)
    bundle = encoded(source)
    saved = json_artifact(bundle, "document.json")
    assert [section["code"] for section in saved["sections"]] == ["10"]
    assert [child["code"] for child in saved["sections"][0]["children"]] == [
        "10.1",
        "10.2",
    ]
    (unit,) = project_attachment(decoded.document)
    assert unit.section_code.value == "10"
    assert all(
        text in unit.text.value
        for text in ("相互作用の本文", "禁忌の本文", "注意の本文")
    )
    assert [
        block.context.section_code.value
        if block.context.section_code is not None
        else None
        for block in unit.blocks
    ] == [
        "10",
        "10.1",
        "10.2",
    ]
    (active,) = project_active_attachment(
        decoded.document, frozenset({YjCode("111111111111")})
    )
    (payload,) = [
        json.loads(line)
        for line in encode_registered_units(decoded.document, (active,)).splitlines()
    ]
    assert payload["section"]["code"] == "10"
    assert [block["context"]["section"]["code"] for block in payload["blocks"]] == [
        "10",
        "10.1",
        "10.2",
    ]
    rendered = registered_unit_text(payload)
    assert all(
        text in rendered for text in ("10.1", "10.2", "禁忌の本文", "注意の本文")
    )
    assert payload["references"][0]["target_section_code"] == "10.2"


@pytest.mark.parametrize("previous_first", [False, True])
def test_revision_marked_current_is_used_without_reordering_source(previous_first):
    source = xml_source()
    previous = b'<PreparationOrRevision id="previous"><YearMonth>2026-09</YearMonth><Version>0</Version></PreparationOrRevision>'
    if previous_first:
        source = source.replace(
            b"<DateOfPreparationOrRevision>",
            b"<DateOfPreparationOrRevision>" + previous,
        )
    else:
        source = source.replace(
            b"</DateOfPreparationOrRevision>",
            previous + b"</DateOfPreparationOrRevision>",
        )
    decoded = PmdaXmlDecoder().decode(source)
    assert isinstance(decoded.source_info, SourceInformation)
    _, products = build_index_document(decoded.source_info.document)
    assert products[0].revision["source_label"] == "今回"
    assert products[0].revision["year_month"] == "2026-10"
    assert [revision.source_label.value for revision in decoded.document.revisions] == (
        ["previous", "今回"] if previous_first else ["今回", "previous"]
    )


def test_short_detail_stays_body_without_a_header_and_keeps_source_order():
    source = xml_source(
        "<Warnings><SimpleList><Item><Detail><Lang>短い本文</Lang></Detail>"
        "<SimpleList><Item><Detail><Lang>内側の本文</Lang></Detail></Item></SimpleList>"
        "<Detail><Lang>末尾の本文</Lang></Detail></Item></SimpleList></Warnings>"
    )
    (unit,) = project_attachment(PmdaXmlDecoder().decode(source).document)
    paragraphs = [block for block in unit.blocks if isinstance(block, SearchParagraph)]
    assert len(paragraphs) == len(unit.blocks)
    assert [block.text.value for block in paragraphs] == [
        "短い本文",
        "内側の本文",
        "末尾の本文",
    ]
    assert all(not block.context.labels for block in unit.blocks)
    assert all(not block.is_heading for block in paragraphs)


def test_explicit_header_is_distinct_from_body():
    source = xml_source(
        "<Warnings><SimpleList><Item><Header><Lang>原文見出し</Lang></Header>"
        "<Detail><Lang>原文本文</Lang></Detail></Item></SimpleList></Warnings>"
    )
    (unit,) = project_attachment(PmdaXmlDecoder().decode(source).document)
    paragraphs = [block for block in unit.blocks if isinstance(block, SearchParagraph)]
    assert len(paragraphs) == len(unit.blocks)
    assert [(block.text.value, block.is_heading) for block in paragraphs] == [
        ("原文見出し", True),
        ("原文本文", False),
    ]


def test_generic_table_first_row_is_not_promoted_to_column_headings():
    source = xml_source(
        "<Warnings><TblBlock><TblCaption><Lang>表題</Lang></TblCaption>"
        "<SimpTblHead><Detail><Lang>表の前置き</Lang></Detail></SimpTblHead>"
        '<SimpleTable><SimpTblRow><SimpTblCell rspan="2"><Detail><Lang>データA</Lang>'
        "</Detail></SimpTblCell><SimpTblCell><Detail><Lang>データB</Lang></Detail>"
        "</SimpTblCell></SimpTblRow><SimpTblRow><SimpTblCell><Detail><Lang>データC</Lang>"
        "</Detail></SimpTblCell></SimpTblRow></SimpleTable>"
        "<SimpTblFoot><Detail><Lang>表の脚注</Lang></Detail></SimpTblFoot></TblBlock></Warnings>"
    )
    decoded = PmdaXmlDecoder().decode(source)
    (section,) = decoded.document.sections
    assert section.body is not None
    table = next(
        block.table
        for block in section.body.blocks
        if isinstance(block, AttachmentTableBlock)
    )
    assert table.columns == ()
    assert [[cell.text.value for cell in row] for row in table.rows] == [
        ["データA", "データB"],
        ["データC"],
    ]
    assert table.rows[0][0].rowspan.value == 2
    assert table.rows[1][0].column.value == 1
    (unit,) = project_active_attachment(
        decoded.document, frozenset({YjCode("111111111111")})
    )
    payload = json.loads(encode_registered_units(decoded.document, (unit,)))
    table_payload = next(
        block for block in payload["blocks"] if block["kind"] == "table"
    )
    assert table_payload["columns"] == []
    text = registered_unit_text(payload)
    assert "<th" not in text
    assert (
        text.index("表題")
        < text.index("表の前置き")
        < text.index("データA")
        < text.index("表の脚注")
    )
