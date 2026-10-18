"""Search JSONL has one record per numbered section and no repeated metadata."""

import hashlib
import json

import pytest
from backend.infrastructure.pmda_xml.transform import transform
from backend.tests.support.paths import PROJECT_ROOT
from backend.tests.support.section_records import assert_original_records_preserved


def test_numbered_sections_own_their_body_without_duplicating_children(tmp_path):
    source = tmp_path / "sections.xml"
    source.write_text(
        '<PackIns drugType="Medicine"><PackageInsertNo>test</PackageInsertNo>'
        "<CompanyIdentifier>000001</CompanyIdentifier>"
        "<Warnings><Item><Detail><Lang>警告A</Lang></Detail></Item>"
        "<Item><Detail><Lang>警告B</Lang></Detail></Item></Warnings>"
        "<Pharmacokinetics><Lang>親項目本文</Lang>"
        "<Absorption><Lang>子項目本文</Lang></Absorption></Pharmacokinetics>"
        "</PackIns>",
        encoding="utf-8",
    )
    output = tmp_path / "result"
    validation = transform(source, output)
    rows = [
        json.loads(line)
        for line in (output / "search_units.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    by_code = {row["section"]["code"]: row for row in rows}
    assert len(rows) == len(by_code) == 2
    assert "警告A" in by_code["1"]["text"] and "警告B" in by_code["1"]["text"]
    assert "子項目本文" in by_code["16"]["text"]
    assert {
        block["context"]["section"]["code"] for block in by_code["16"]["blocks"]
    } == {"16", "16.2"}
    assert all(
        row["schema_version"] == "medi-chat.pmda-sections.v4"
        and isinstance(row["blocks"], list)
        for row in rows
    )
    assert all(row["kind"] == "section" for row in rows)
    assert validation["status"] == "pass"
    assert validation["search_schema_version"] == "medi-chat.pmda-sections.v4"
    before = (output / "search_units.jsonl").read_bytes()
    transform(source, output)
    assert (output / "search_units.jsonl").read_bytes() == before


@pytest.mark.parametrize(
    "source",
    sorted((PROJECT_ROOT / "data/pmda/originals").rglob("*.xml")),
    ids=lambda path: path.stem,
)
def test_real_documents_keep_adverse_table_and_all_section_bodies(source, tmp_path):
    output = tmp_path / source.stem
    validation = transform(source, output)
    rows = [
        json.loads(line)
        for line in (output / "search_units.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert len({row["unit_id"] for row in rows}) == len(rows)
    assert len({row["section"]["code"] for row in rows}) == len(rows)
    assert validation["unrepresented_nonempty_lang_paths"] == []
    assert validation["unresolved_references"] == []
    assert validation["duplicate_section_codes"] == []
    assert validation["duplicate_unit_ids"] == []
    adverse = next(row for row in rows if row["section"]["code"] == "11")
    assert "頻度不明" in adverse["text"]
    assert "消化器" in adverse["text"]
    assert adverse["text"].count("<table>") == 1
    original = source.parents[2] / "structured" / source.stem / "document.json"
    expected = json.loads(original.read_text(encoding="utf-8"))
    expected["source"]["sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
    # Only historical location fields change on regeneration; copied bytes stay unchanged.
    expected["source"]["file"] = expected["source"]["file"].replace(
        "data_tools/data/", "data/pmda/originals/", 1
    )
    for figure in expected["source"]["figures"]:
        figure["file"] = figure["file"].replace(
            "data_tools/data/", "data/pmda/originals/", 1
        )
    assert_original_records_preserved(
        json.loads((output / "document.json").read_text(encoding="utf-8")), expected
    )
