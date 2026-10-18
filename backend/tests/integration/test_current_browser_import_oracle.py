"""The browser's independent oracle must reject original-tree/storage damage."""

import json
import runpy
import sqlite3

import pytest
from backend.domain.attachment.identifiers import DocumentId
from backend.infrastructure.pmda_xml.decoder import PmdaXmlDecoder
from backend.tests.integration.test_registration_publisher import publisher as publisher
from backend.tests.support.paths import PROJECT_ROOT


@pytest.mark.parametrize("damage", [None, "source", "tree", "file", "index"])
def test_current_browser_oracle_detects_corruption(publisher, damage):
    source = next(
        (PROJECT_ROOT / "data/pmda/originals").rglob("630004_3339003F5020_1_08.xml")
    )
    original = source.read_bytes()
    result = publisher.publish(PmdaXmlDecoder().decode(original), original)
    directory = publisher.store._target(
        DocumentId(result.document_id), result.source_sha256
    )
    check = runpy.run_path(
        str(PROJECT_ROOT / "frontend/scripts/current-import-check.py")
    )["check"]
    assert check(source, directory, publisher.index_path)["sections"] == 22
    if damage is None:
        return
    if damage == "source":
        (directory / "source.xml").write_bytes(original + b" ")
    elif damage == "tree":
        path = directory / "document.json"
        value = json.loads(path.read_bytes())
        value["sections"][0]["tree"]["attributes"]["id"] = "broken"
        path.write_text(json.dumps(value), encoding="utf-8")
    elif damage == "file":
        path = directory / "search_units.jsonl"
        values = [json.loads(line) for line in path.read_bytes().splitlines()]
        values[0]["text"] += "broken"
        path.write_text(
            "\n".join(json.dumps(value) for value in values), encoding="utf-8"
        )
    else:
        with sqlite3.connect(publisher.index_path) as connection:
            identifier, payload = connection.execute(
                "SELECT unit_id,payload_json FROM units LIMIT 1"
            ).fetchone()
            value = json.loads(payload)
            value["text"] += "broken"
            connection.execute(
                "UPDATE units SET payload_json=? WHERE unit_id=?",
                (json.dumps(value), identifier),
            )
    with pytest.raises(AssertionError):
        check(source, directory, publisher.index_path)
