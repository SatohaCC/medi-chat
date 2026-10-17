import hashlib
import json
from dataclasses import replace

from backend.application.indexing.attachment_projection import project_active_attachment
from backend.domain.attachment.primitives import (
    AttachmentProductCode,
    AttachmentSha256,
    AttachmentText,
)
from backend.domain.attachment.value_objects import (
    AttachmentBody,
    AttachmentContext,
    AttachmentParagraph,
)
from backend.domain.medicine.identifiers import YjCode
from backend.domain.retrieval.value_objects import SearchTableBlock
from backend.infrastructure.pmda_xml.decoder import PmdaXmlDecoder
from backend.infrastructure.pmda_xml.registration_artifacts import (
    encode_registered_units,
)
from backend.tests.domain.attachment.test_attachment_domain import _document
from backend.tests.domain.attachment.test_attachment_registration_domain import A, B
from backend.tests.support.attachment_import_fixtures import xml_source


def mixed_source():
    body = '<Warnings><Detail><Lang>同じ本文</Lang></Detail><Item brandRef="A"><Header><Lang>A専用</Lang></Header><Detail><Lang>同じ本文</Lang></Detail></Item><SimpTbl><SimpTblRow><SimpTblCell brandRef="A"><Lang>A列</Lang></SimpTblCell><SimpTblCell brandRef="B"><Lang>B列</Lang></SimpTblCell><SimpTblCell cspan="2"><Lang>共通列</Lang></SimpTblCell></SimpTblRow><SimpTblRow><SimpTblCell brandRef="A"><Lang>A値</Lang></SimpTblCell><SimpTblCell brandRef="B"><Lang>B値</Lang></SimpTblCell><SimpTblCell cspan="2" rspan="2"><Lang>共通値</Lang></SimpTblCell></SimpTblRow><SimpTblRow><SimpTblCell brandRef="A"><Lang>A次</Lang></SimpTblCell><SimpTblCell brandRef="B"><Lang>B次</Lang></SimpTblCell></SimpTblRow></SimpTbl></Warnings>'
    return xml_source(body).replace(
        b"</ApprovalEtc>",
        '<DetailBrandName id="B"><ApprovalBrandName><Lang>製品B</Lang></ApprovalBrandName><BrandCode><YJCode>222222222222</YJCode></BrandCode></DetailBrandName></ApprovalEtc>'.encode(),
    )


def test_tc092_xml_mixed_row_does_not_apply_first_child_scope_to_b_and_common():
    source = mixed_source()
    document = PmdaXmlDecoder().decode(source).document
    original = document.sections
    (unit,) = project_active_attachment(document, frozenset({YjCode("222222222222")}))
    assert "A値" not in unit.text.value and "A次" not in unit.text.value
    assert (
        "B値" in unit.text.value
        and "B次" in unit.text.value
        and "共通値" in unit.text.value
    )
    assert unit.text.value.count("同じ本文") == 1
    (table,) = [
        block.table for block in unit.blocks if isinstance(block, SearchTableBlock)
    ]
    assert [c.value for c in table.columns] == ["B列", "共通列"]
    assert [
        [(c.text.value, c.column, c.rowspan, c.colspan) for c in row]
        for row in table.rows
    ] == [
        [("B列", 0, 1, 1), ("共通列", 1, 1, 2)],
        [("B値", 0, 1, 1), ("共通値", 1, 2, 2)],
        [("B次", 0, 1, 1)],
    ]
    assert document.sections == original


def test_tc093_v3_rows_qualify_original_sha_and_preserve_original_document_id():
    o = mixed_source()
    n = o.replace("B値".encode(), "新版B値".encode(), 1)
    rows = []
    for source in (o, n):
        document = PmdaXmlDecoder().decode(source).document
        units = project_active_attachment(document, frozenset({YjCode("222222222222")}))
        rows.append(json.loads(encode_registered_units(document, units)))
    for source, row in zip((o, n), rows, strict=True):
        sha = hashlib.sha256(source).hexdigest()
        assert row["schema_version"] == "medi-chat.pmda-sections.v3"
        assert row["document_key"] == "000001_test"
        assert row["source_sha256"] == sha
        assert row["version_id"] == f"000001_test:{sha}"
        assert row["unit_id"] == f"000001_test:{sha}:1"
        assert row["product_yj_codes"] == ["222222222222"]
        assert row["section"] == {"code": "1", "title": "警告"}
        assert row["kind"] == "section"
        assert (
            "A値" not in row["text"]
            and "B値" in row["text"]
            and "共通値" in row["text"]
        )
        assert 'rowspan="2"' in row["text"] and 'colspan="2"' in row["text"]
    assert rows[0]["unit_id"] != rows[1]["unit_id"]


def test_tc092_internal_references_keep_b_common_targets_and_drop_a_cell_references():
    source = (
        mixed_source()
        .replace("B値".encode(), b'B<HeaderRef ref="targetB"/>')
        .replace("A値".encode(), b'A<HeaderRef ref="targetA"/>')
    )
    source = source.replace(
        b"</Warnings>",
        b'<Item brandRef="A"><Detail id="targetA"><Lang>A target</Lang></Detail></Item><Item brandRef="B"><Detail id="targetB"><Lang>B target</Lang></Detail></Item></Warnings>',
    )
    document = PmdaXmlDecoder().decode(source).document
    unit = project_active_attachment(document, frozenset({YjCode("222222222222")}))[0]
    row = json.loads(encode_registered_units(document, (unit,)))
    assert [reference["target_xml_id"] for reference in row["references"]] == [
        "targetB"
    ]
    assert row["references"][0]["target_section_code"] == "1"
    tables = [block for block in row["blocks"] if block["kind"] == "table"]
    assert tables[0]["rows"][1][0]["references"][0]["target_xml_id"] == "targetB"
    assert "A target" not in row["text"] and "B target" in row["text"]


def test_tc092_scope_intersection_retains_identical_common_literal_and_original():
    document = _document()
    common = AttachmentParagraph(text=AttachmentText("同じ本文"))
    a = AttachmentParagraph(
        text=AttachmentText("同じ本文"),
        context=AttachmentContext(
            product_codes=(AttachmentProductCode(A.value),),
            labels=(AttachmentText("A専用"),),
        ),
    )
    b = AttachmentParagraph(
        text=AttachmentText("B固有"),
        context=AttachmentContext(
            product_codes=(AttachmentProductCode(B.value),),
            labels=(AttachmentText("B専用"),),
        ),
    )
    source = b"fixed O original"
    document = replace(
        document,
        source=replace(
            document.source, sha256=AttachmentSha256(hashlib.sha256(source).hexdigest())
        ),
        sections=(
            replace(
                document.sections[0],
                body=AttachmentBody(
                    blocks=(common, a, b),
                    text=AttachmentText("同じ本文\n\n同じ本文\n\nB固有"),
                ),
            ),
        ),
    )
    original = document.sections
    (unit,) = project_active_attachment(document, frozenset({B}))
    assert unit.text.value == "同じ本文\n\nB固有"
    assert [block.context.labels for block in unit.blocks] == [
        (),
        (unit.blocks[1].context.labels[0],),
    ]
    assert unit.blocks[1].context.labels[0].value == "B専用"
    assert tuple(code.value for code in unit.product_codes) == (B.value,)
    assert unit.unit_id.value == f"doc-001:{hashlib.sha256(source).hexdigest()}:1"
    assert document.sections == original
