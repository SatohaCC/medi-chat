"""Produce an UNVERIFIED review candidate, never a test oracle automatically."""

import hashlib
import json
import runpy
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class SemanticHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.events = []

    def handle_starttag(self, tag, attrs):
        self.events.append(["start", tag, sorted(attrs)])

    def handle_endtag(self, tag):
        self.events.append(["end", tag])

    def handle_data(self, data):
        if data:
            self.events.append(["text", data])


def candidate(index):
    index = index.resolve()
    snapshot = runpy.run_path(str(ROOT / "frontend/scripts/sqlite-fixture.py"))[
        "snapshot"
    ](index)
    table = snapshot["tables"]["units"]
    document = "630004_3339003F5020_1_08"
    units = [
        json.loads(row[table["columns"].index("payload_json")])
        for row in table["rows"]
        if row[table["columns"].index("document_key")] == document
    ]
    units.sort(key=lambda unit: tuple(map(int, unit["section"]["code"].split("."))))
    source = next((ROOT / "data/pmda/originals").glob(f"*/{document}.xml"))
    artifact = ROOT / f"data/pmda/structured/{document}/search_units.jsonl"
    v2 = {
        unit["section"]["code"]: unit
        for unit in map(json.loads, artifact.read_text(encoding="utf8").splitlines())
    }
    observed = []
    for unit in units:
        parser = SemanticHTML()
        parser.feed(unit["text"])
        observed.append(
            {
                "code": unit["section"]["code"],
                "payload": unit,
                "html_events": parser.events,
                "v2_artifact": v2[unit["section"]["code"]],
            }
        )
    return {
        "status": "UNVERIFIED_CANDIDATE_NOT_A_TEST_ORACLE",
        "source": source.relative_to(ROOT).as_posix(),
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "v2_artifact": artifact.relative_to(ROOT).as_posix(),
        "v2_artifact_sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
        "database": index.relative_to(ROOT).as_posix(),
        "database_file_sha256": hashlib.sha256(index.read_bytes()).hexdigest(),
        "database_logical_sha256": snapshot["logical_sha256"],
        "sections": observed,
    }


if __name__ == "__main__":
    index, output = map(Path, sys.argv[1:])
    output.write_text(
        json.dumps(candidate(index), ensure_ascii=False, indent=2), encoding="utf8"
    )
