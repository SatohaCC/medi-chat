"""Produce an UNVERIFIED review candidate, never a test oracle automatically."""

import hashlib
import json
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from backend.application.indexing.queries.services.attachment_projection import (
    project_active_attachment,
)
from backend.domain.medicine.identifiers import YjCode
from backend.infrastructure.index_payloads import encode_registered_units
from backend.infrastructure.persistence.attachment_document_mapping import (
    document_from_payload,
)
from backend.tests.support.postgres_browser_fixture import snapshot as postgres_snapshot


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
    snapshot = postgres_snapshot(index)
    document = "630004_3339003F5020_1_08"
    tables = snapshot["tables"]

    def records(name):
        table = tables[name]
        return [dict(zip(table["columns"], row, strict=True)) for row in table["rows"]]

    pointer = records("registration_state")[0]["generation_id"]
    memberships = {}
    for row in records("generation_memberships"):
        if row["generation_id"] == pointer:
            memberships.setdefault(row["version_id"], set()).add(YjCode(row["yj_code"]))
    units = []
    for row in sorted(
        records("attachment_versions"), key=lambda item: item["version_id"]
    ):
        if row["version_id"] not in memberships:
            continue
        restored = document_from_payload(row["structure"])
        if restored.document_id.value != document:
            continue
        content = encode_registered_units(
            restored,
            project_active_attachment(
                restored, frozenset(memberships[row["version_id"]])
            ),
        )
        units.extend(json.loads(line) for line in content.splitlines())
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
        "fixture_schema": json.loads(
            (index / "postgres-fixture.json").read_text(encoding="utf-8")
        )["schema"],
        "database_logical_sha256": snapshot["logical_sha256"],
        "sections": observed,
    }


if __name__ == "__main__":
    index, output = map(Path, sys.argv[1:])
    output.write_text(
        json.dumps(candidate(index), ensure_ascii=False, indent=2), encoding="utf8"
    )
