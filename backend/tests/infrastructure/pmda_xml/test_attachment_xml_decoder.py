"""TC-011/013〜022/025/026/028〜031: real byte parser and encoder."""

import hashlib
import json
import socket
from pathlib import Path

import pytest
from backend.application.attachment_import.import_errors import InvalidAttachment
from backend.infrastructure.package_insert_definitions.loader import (
    get_package_insert_definitions,
)
from backend.infrastructure.pmda_xml.decoder import PmdaXmlDecoder
from backend.project_paths import PROJECT_ROOT
from backend.tests.support.attachment_import_fixtures import (
    encoded,
    json_artifact,
    xml_source,
)
from backend.tests.support.section_records import assert_original_records_preserved


@pytest.mark.parametrize(
    "encoding", ["utf-8", "utf-8-sig", "utf-16", "utf-16-le", "utf-16-be", "cp932"]
)
def test_declared_encodings_keep_original_byte_hash_and_meaning(encoding):
    declaration_encoding = (
        "UTF-16"
        if encoding.startswith("utf-16")
        else "CP932"
        if encoding == "cp932"
        else "UTF-8"
    )
    source = xml_source(
        prefix=f'<?xml version="1.0" encoding="{declaration_encoding}"?>',
        encoding=encoding,
    )
    bundle = encoded(source)
    assert bundle.source_sha256 == hashlib.sha256(source).hexdigest()
    assert (
        "警告 Ａ①"
        in json_artifact(bundle, "document.json")["sections"][0]["tree"]["children"][0][
            "children"
        ][0]["text"]
    )
    assert bundle.result.products[0].brand_name == "製品A"


@pytest.mark.parametrize(
    "source",
    [
        b"<PackIns",
        xml_source()[:-4],
        b'<?xml version="1.0" encoding="UTF-8"?><PackIns>\xff</PackIns>',
        xml_source(prefix='<?xml version="1.0" encoding="UTF-16"?>'),
        xml_source(prefix='<?xml version="1.0" encoding="UTF-8"?>', encoding="utf-16"),
    ],
)
def test_bad_bytes_and_declaration_mismatch_are_parse_errors(source):
    with pytest.raises(InvalidAttachment) as caught:
        encoded(source)
    assert caught.value.code == "xml_parse_error"


@pytest.mark.parametrize("namespace", ["prefix", "default"])
def test_namespace_pi_comments_and_mixed_text_are_preserved_without_stylesheet_fetch(
    monkeypatch,
    namespace,
):
    source = (
        xml_source(
            '<Warnings xmlns:p="urn:outer" p:attr=" Ａ① "><Detail> 前\n<Lang p:attr="原文"> Ａ① <p:em xmlns:p="urn:inner">半角A</p:em> 後\n </Lang> tail\n<?enter newline?><!-- inside --></Detail></Warnings>',
            prefix='<?xml-stylesheet href="http://127.0.0.1/never"?> <!--before-->',
        )
        + b"<?after end?><!--after-->"
    )
    if namespace == "prefix":
        source = source.replace(
            b"<PackIns ", b'<q:PackIns xmlns:q="urn:document" '
        ).replace(b"</PackIns>", b"</q:PackIns>")
    else:
        source = source.replace(b"<PackIns ", b'<PackIns xmlns="urn:document" ')
    get_package_insert_definitions()

    def forbidden(*args, **kwargs):
        pytest.fail("external resource was fetched")

    monkeypatch.setattr(socket, "create_connection", forbidden)
    bundle = encoded(source)
    sidecar = json_artifact(bundle, "source_metadata.json")
    events = sidecar["events"]
    assert events[0]["kind"] == "pi" and "http://127.0.0.1/never" in events[0]["data"]
    assert events[-1]["kind"] == "comment" and events[-1]["data"] == "after"
    assert any(
        event.get("attributes", {}).get("xmlns:p") == "urn:inner" for event in events
    )
    assert any(event.get("attributes", {}).get("p:attr") == " Ａ① " for event in events)
    assert any(
        "urn:document" in event.get("attributes", {}).values() for event in events
    )
    document = json_artifact(bundle, "document.json")
    detail = document["sections"][0]["tree"]["children"][0]
    assert detail["text"] == " 前\n"
    assert detail["children"][0]["text"] == " Ａ① "
    assert detail["children"][0]["children"][0]["tail"] == " 後\n "
    assert detail["children"][0]["tail"] == " tail\n"
    assert [child["tag"] for child in detail["children"]][-2:] == [
        "#processing_instruction",
        "#comment",
    ]


@pytest.mark.parametrize("encoding", ["utf-8", "utf-16", "utf-16-le", "utf-16-be"])
@pytest.mark.parametrize(
    "declaration",
    [
        "<!DOCTYPE PackIns>",
        '<!DOCTYPE PackIns [<!ENTITY injected "expansion">]>',
        '<!DOCTYPE PackIns SYSTEM "http://127.0.0.1/never">',
        '<!DOCTYPE PackIns [<!ENTITY injected SYSTEM "file:///never">]>',
    ],
)
def test_dtd_and_entities_are_rejected_before_external_io(
    encoding, declaration, monkeypatch, tmp_path
):
    sentinel = tmp_path / "sentinel.txt"
    sentinel.write_bytes(b"untouched")
    declaration = declaration.replace("file:///never", sentinel.as_uri())
    source = xml_source(
        prefix=f'<?xml version="1.0" encoding="{"UTF-16" if encoding.startswith("utf-16") else "UTF-8"}"?>{declaration}',
        encoding=encoding,
    )
    get_package_insert_definitions()
    monkeypatch.setattr(
        socket, "create_connection", lambda *a, **k: pytest.fail("external connection")
    )
    monkeypatch.setattr(
        socket.socket, "connect", lambda *a, **k: pytest.fail("external connection")
    )
    original_read = Path.read_bytes

    def read(path):
        if path == sentinel:
            pytest.fail("external entity sentinel was read")
        return original_read(path)

    monkeypatch.setattr(Path, "read_bytes", read)
    with pytest.raises(InvalidAttachment) as caught:
        encoded(source)
    assert caught.value.code == "xml_forbidden_declaration"
    assert original_read(sentinel) == b"untouched"


def test_xinclude_is_rejected_and_unsafe_figure_name_is_only_a_reference(tmp_path):
    sentinel = tmp_path / "sentinel.xml"
    sentinel.write_text("private", encoding="utf-8")
    source = xml_source(
        f'<Warnings xmlns:xi="http://www.w3.org/2001/XInclude"><xi:include href="{sentinel.as_uri()}"/></Warnings>'
    )
    with pytest.raises(InvalidAttachment) as caught:
        encoded(source)
    assert caught.value.code == "xml_unsupported_structure"
    figure = xml_source(
        '<Warnings><Graphic><GraphicBody gfname="../../sentinel.xml"/><GraphicCaption><Lang> 図の説明 </Lang></GraphicCaption></Graphic></Warnings>'
    )
    bundle = encoded(figure, filename="C:\\outside\\evil.xml")
    assert bundle.result.validation_status == "warning"
    assert bundle.result.warnings[0].reference == "../../sentinel.xml"
    assert "図の説明" in next(
        file.content.decode()
        for file in bundle.files
        if file.name == "search_units.jsonl"
    )
    assert sentinel.read_text(encoding="utf-8") == "private"


@pytest.mark.parametrize("depth,accepted", [(256, True), (257, False)])
def test_depth_counts_root_as_one_and_accepts_exact_limit(depth, accepted):
    source = xml_source(
        "<Warnings>"
        + "<Detail>" * (depth - 3)
        + "<Lang>本文</Lang>"
        + "</Detail>" * (depth - 3)
        + "</Warnings>"
    )
    if accepted:
        assert encoded(source).result.search_unit_count == 1
    else:
        with pytest.raises(InvalidAttachment) as caught:
            encoded(source)
        assert caught.value.code == "xml_depth_limit"


@pytest.mark.parametrize("count,accepted", [(200000, True), (200001, False)])
def test_element_count_limit_ignores_pi_and_comments(count, accepted):
    # Hand-count 15 header elements plus root; Warnings/Detail/Lang add three.
    base = xml_source("<Warnings><Detail><Lang>本文</Lang></Detail></Warnings>")
    import xml.etree.ElementTree as ET

    header_count = sum(1 for _ in ET.fromstring(base).iter())
    extra = b"<Empty/>" * (count - header_count)
    source = base.replace(
        b"</Warnings>", extra + b"<?test pi?><!--comment--></Warnings>"
    )
    if accepted:
        validation = json_artifact(encoded(source), "validation.json")
        assert validation["xml_element_count"] == count
    else:
        with pytest.raises(InvalidAttachment) as caught:
            encoded(source)
        assert caught.value.code == "xml_element_limit"


@pytest.mark.parametrize(
    "body,code",
    [
        (
            "<Warnings><Lang>A</Lang></Warnings><Warnings><Lang>B</Lang></Warnings>",
            "duplicate_section",
        ),
        ("<Unknown><Lang>未知</Lang></Unknown>", "unmapped_root_section"),
        (
            '<Warnings><Detail><Lang>本文<HeaderRef ref="missing"/></Lang></Detail></Warnings>',
            "unresolved_reference",
        ),
        (
            '<Warnings><Graphic><GraphicBody gfname="fig.gif"/><Other><Lang>未収録本文</Lang></Other></Graphic></Warnings>',
            "unrepresented_body",
        ),
    ],
)
def test_fatal_validation_is_never_downgraded_to_figure_warning(body, code):
    with pytest.raises(InvalidAttachment) as caught:
        encoded(xml_source(body))
    assert caught.value.code == code


@pytest.mark.source_data
@pytest.mark.parametrize(
    "source",
    sorted((PROJECT_ROOT / "data/pmda/originals").rglob("*.xml")),
    ids=lambda path: path.stem,
)
def test_new_decoder_and_encoder_match_all_legacy_document_fields_and_rows(source):
    raw = source.read_bytes()
    # Explicit assets are trusted CLI input bytes; decoder never reads gfname paths.
    assets = {
        path.name: path.read_bytes()
        for path in source.parent.iterdir()
        if path.is_file() and path != source
    }
    filename = source.relative_to(PROJECT_ROOT).as_posix()
    decoder = PmdaXmlDecoder(
        assets=assets, strict_assets=True, source_filename=filename
    )
    bundle = encoded(raw, filename=filename, decoder=decoder)
    expected = json.loads(
        (
            PROJECT_ROOT / "data/pmda/structured" / source.stem / "document.json"
        ).read_text(encoding="utf-8")
    )
    expected["source"]["sha256"] = hashlib.sha256(raw).hexdigest()
    expected["source"]["file"] = expected["source"]["file"].replace(
        "data_tools/data/", "data/pmda/originals/", 1
    )
    for figure in expected["source"]["figures"]:
        figure["file"] = figure["file"].replace(
            "data_tools/data/", "data/pmda/originals/", 1
        )
    assert_original_records_preserved(json_artifact(bundle, "document.json"), expected)
    rows = [
        json.loads(line)
        for line in next(
            file.content for file in bundle.files if file.name == "search_units.jsonl"
        ).splitlines()
    ]
    old_rows = [
        json.loads(line)
        for line in (
            PROJECT_ROOT / "data/pmda/structured" / source.stem / "search_units.jsonl"
        )
        .read_bytes()
        .splitlines()
    ]
    assert {row["section"]["code"] for row in rows} == {
        row["section"]["code"].split(".", 1)[0] for row in old_rows
    }
    assert all("." not in row["section"]["code"] for row in rows)
    assert len(rows) == len({row["section"]["code"] for row in rows})


def test_strict_asset_policy_accepts_complete_assets_and_rejects_missing():
    source = xml_source(
        '<Warnings><Graphic><GraphicBody gfname="figure.gif"/><GraphicCaption><Lang>説明</Lang></GraphicCaption></Graphic></Warnings>'
    )
    assert (
        encoded(
            source,
            decoder=PmdaXmlDecoder(assets={"figure.gif": b"GIF"}, strict_assets=True),
        ).result.validation_status
        == "pass"
    )
    with pytest.raises(InvalidAttachment) as caught:
        encoded(source, decoder=PmdaXmlDecoder(strict_assets=True))
    assert caught.value.code == "missing_figure"


def test_table_encoding_groups_children_and_keeps_typed_column_positions():
    table = '<SimpTbl><SimpTblRow><SimpTblCell rspan="2"><Lang>分類</Lang></SimpTblCell><SimpTblCell cspan="2"><Lang>頻度<?enter newline?>症状</Lang></SimpTblCell></SimpTblRow><SimpTblRow><SimpTblCell><Lang>悪心</Lang></SimpTblCell><SimpTblCell><Lang>嘔吐</Lang></SimpTblCell></SimpTblRow></SimpTbl>'
    source = xml_source(
        "<Interactions><ContraIndicatedCombinations>"
        + table
        + "</ContraIndicatedCombinations><PrecautionsForCombinations>"
        + table
        + "</PrecautionsForCombinations></Interactions><AdverseEvents><OtherAdverseEvents>"
        + table
        + "</OtherAdverseEvents></AdverseEvents>"
    )
    decoded = PmdaXmlDecoder().decode(source)
    bundle = encoded(source)
    rows = [
        json.loads(line)
        for line in next(
            file.content for file in bundle.files if file.name == "search_units.jsonl"
        ).splitlines()
    ]
    assert [row["section"]["code"] for row in rows] == ["10", "11"]
    assert [row["text"].count("<table>") for row in rows] == [2, 1]
    for row in rows:
        assert 'rowspan="2"' in row["text"] and 'colspan="2"' in row["text"]
        assert "頻度<br>症状" in row["text"]
    from backend.domain.attachment.value_objects import AttachmentTableBlock

    body = next(
        section.body
        for root in decoded.document.sections
        for section in root.walk()
        if section.code.value == "11.2"
    )
    assert body is not None
    block = body.blocks[0]
    assert isinstance(block, AttachmentTableBlock)
    assert [cell.column.value for cell in block.table.rows[1]] == [1, 2]
