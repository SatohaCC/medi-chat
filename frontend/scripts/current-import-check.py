"""Independent raw XML and PostgreSQL checks for the current browser fixture."""

import hashlib
import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from sqlalchemy import select, text
from backend.infrastructure.persistence import postgres_schema as schema
from backend.infrastructure.persistence.postgres_readiness import verify_postgres_readiness
from backend.infrastructure.pmda_xml.transform import transform
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


def check(source: Path, engine, version_id: str):
    original = source.read_bytes()
    digest = hashlib.sha256(original).hexdigest()
    try:
        verify_postgres_readiness(engine)
    except RuntimeError as error:
        raise AssertionError("Stored PostgreSQL integrity failed") from error
    with engine.connect().execution_options(isolation_level="REPEATABLE READ") as connection:
        connection.execute(text("SET TRANSACTION READ ONLY"))
        stored = connection.execute(select(schema.versions.c.source).where(schema.versions.c.version_id == version_id)).scalar_one()
        indexed = connection.execute(select(schema.units.c.payload).where(schema.units.c.version_id == version_id).order_by(schema.units.c.position)).scalars().all()
    assert bytes(stored) == original
    assert version_id == f"{source.stem}:{digest}"
    # Explicit test-only offline conversion preserves the independent raw-tree
    # oracle. Application startup/requests never read these resources or output.
    with TemporaryDirectory(prefix="medi-chat-oracle-") as temporary:
        directory = Path(temporary)
        transform(source, directory)
        document = json.loads((directory / "document.json").read_bytes())
        assert document["schema_version"] == "medi-chat.pmda-prescription-xml.v2"
        assert [section["code"] for section in document["sections"]] == list(SECTION_TAGS)
        parser = ET.XMLParser(target=ET.TreeBuilder(insert_comments=True, insert_pis=True))
        raw = {name(node.tag): node for node in ET.fromstring(original, parser=parser)}
        for section in document["sections"]:
            assert section["tree"] == tree(raw[SECTION_TAGS[section["code"]]])
        units = [json.loads(line) for line in (directory / "search_units.jsonl").read_bytes().splitlines()]
    assert [unit["section"]["code"] for unit in units] == list(SECTION_TAGS)
    for unit in units:
        assert unit["schema_version"] == "medi-chat.pmda-sections.v4"
        assert unit["source_sha256"] == digest
        assert unit["unit_id"] == f"{source.stem}:{unit['section']['code']}"
        assert unit["version_id"] is None
    for unit in indexed:
        assert unit["version_id"] == version_id
        assert unit["unit_id"] == f"{version_id}:{unit['section']['code']}"
        unit["unit_id"] = f"{source.stem}:{unit['section']['code']}"
        unit["version_id"] = None
    assert sorted(indexed, key=lambda item: item["unit_id"]) == sorted(units, key=lambda item: item["unit_id"])
    return {"sections": len(units), "source_tree": "passed", "stored_index": "passed"}


if __name__ == "__main__":
    from backend.infrastructure.persistence.postgres_engine import create_postgres_engine
    from backend.tests.support.postgres_browser_fixture import fixture_schema, selected_url
    source, root, version_id = sys.argv[1:]
    engine = create_postgres_engine(selected_url(), schema=fixture_schema(Path(root)))
    try:
        print(json.dumps(check(Path(source), engine, version_id)))
    finally:
        engine.dispose()
