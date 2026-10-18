"""Independent raw XML and file/SQLite checks for the current browser fixture."""

import hashlib
import json
import sqlite3
import sys
from contextlib import closing
from pathlib import Path
from xml.etree import ElementTree as ET

SECTION_TAGS = dict(
    zip(
        (
            "1",
            "2",
            "3",
            "4",
            "6",
            "7",
            "8",
            "9",
            "10",
            "11",
            "13",
            "14",
            "15",
            "16",
            "17",
            "18",
            "19",
            "21",
            "22",
            "23",
            "24",
            "26",
        ),
        (
            "Warnings",
            "ContraIndications",
            "CompositionAndProperty",
            "IndicationsOrEfficacy",
            "InfoDoseAdmin",
            "InfoPrecautionsDosage",
            "ImportantPrecautions",
            "UseInSpecificPopulations",
            "Interactions",
            "AdverseEvents",
            "OverDosage",
            "PrecautionsForApplication",
            "OtherPrecautions",
            "Pharmacokinetics",
            "ResultsOfClinicalTrials",
            "EfficacyPharmacology",
            "PhyschemOfActIngredients",
            "ConditionsOfApproval",
            "Package",
            "MainLiterature",
            "AddresseeOfLiteratureRequest",
            "NameAddressManufact",
        ),
        strict=True,
    )
)


def name(value):
    if value is ET.ProcessingInstruction:
        return "#processing_instruction"
    if value is ET.Comment:
        return "#comment"
    if value.startswith("{http://www.w3.org/XML/1998/namespace}"):
        return "xml:" + value.split("}", 1)[1]
    return value.split("}")[-1]


def tree(node):
    result = {"tag": name(node.tag)}
    for key, value in (
        ("attributes", {name(key): value for key, value in node.attrib.items()}),
        ("text", node.text),
        ("tail", node.tail),
        ("children", [tree(child) for child in node]),
    ):
        if value is not None and value != {} and value != []:
            result[key] = value
    return result


def check(source: Path, directory: Path, index: Path):
    original = source.read_bytes()
    digest = hashlib.sha256(original).hexdigest()
    assert (directory / "source.xml").read_bytes() == original
    document = json.loads((directory / "document.json").read_bytes())
    assert document["schema_version"] == "medi-chat.pmda-prescription-xml.v2"
    assert [section["code"] for section in document["sections"]] == list(SECTION_TAGS)
    parser = ET.XMLParser(target=ET.TreeBuilder(insert_comments=True, insert_pis=True))
    raw = {name(node.tag): node for node in ET.fromstring(original, parser=parser)}
    for section in document["sections"]:
        # Equality retains every text/tail, cell grid, attribute and reference,
        # independently of the application's decoder and renderer.
        assert section["tree"] == tree(raw[SECTION_TAGS[section["code"]]])
    units = [
        json.loads(line)
        for line in (directory / "search_units.jsonl").read_bytes().splitlines()
    ]
    assert [unit["section"]["code"] for unit in units] == list(SECTION_TAGS)
    for unit in units:
        assert unit["schema_version"] == "medi-chat.pmda-sections.v4"
        assert unit["source_sha256"] == digest
        assert unit["unit_id"] == f"{source.stem}:{unit['section']['code']}"
        assert unit["version_id"] is None
    with closing(
        sqlite3.connect(index.resolve().as_uri() + "?mode=ro", uri=True)
    ) as connection:
        indexed = [
            json.loads(row[0])
            for row in connection.execute(
                "SELECT payload_json FROM units WHERE document_key=?", (source.stem,)
            )
        ]
    for unit in indexed:
        assert unit["version_id"] == f"{source.stem}:{digest}"
        assert unit["unit_id"] == f"{source.stem}:{digest}:{unit['section']['code']}"
        unit["unit_id"] = f"{source.stem}:{unit['section']['code']}"
        unit["version_id"] = None
    assert sorted(indexed, key=lambda item: item["unit_id"]) == sorted(
        units, key=lambda item: item["unit_id"]
    )
    return {"sections": len(units), "source_tree": "passed", "stored_index": "passed"}


if __name__ == "__main__":
    print(json.dumps(check(*map(Path, sys.argv[1:]))))
