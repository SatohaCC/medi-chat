"""Source updates must invalidate the index even with an unchanged manifest."""

import json
import os
import sqlite3
from pathlib import Path

import pytest
from backend.application.indexing.index_errors import IndexSourceError
from backend.infrastructure.composition.index_verifier import verify_index_readiness
from backend.infrastructure.persistence.index_writer import SqlAlchemyIndexWriter
from backend.infrastructure.sources.file_index_source import FileIndexSourceReader
from backend.tests.test_package_insert_index import migrated_index as migrated_index


def test_jsonl_change_invalidates_manifest_index_and_rebuild_restores_it(
    migrated_index,
):
    source, engine = migrated_index
    manifest = source / "manifest.json"
    manifest.write_text('{"document_count": 1}', encoding="utf-8")
    reader = FileIndexSourceReader(source)
    writer = SqlAlchemyIndexWriter(engine)
    before = reader.read_snapshot()
    writer.replace(before)
    assert engine.url.database is not None
    index = Path(engine.url.database)
    verify_index_readiness(source, index)
    units = next(source.glob("*/search_units.jsonl"))
    stat = units.stat()
    content = units.read_text(encoding="utf-8")
    assert "頭痛" in content
    units.write_text(content.replace("頭痛", "腹痛"), encoding="utf-8")
    os.utime(units, ns=(stat.st_atime_ns, stat.st_mtime_ns))
    assert manifest.read_text(encoding="utf-8") == '{"document_count": 1}'
    after = reader.read_snapshot()
    assert before.fingerprint != after.fingerprint
    with pytest.raises(RuntimeError, match="stale fingerprint"):
        verify_index_readiness(source, index)
    writer.replace(after)
    verify_index_readiness(source, index)
    with sqlite3.connect(index) as connection:
        actual = {
            row[0]: json.loads(row[1])
            for row in connection.execute("SELECT unit_id, payload_json FROM units")
        }
    assert actual == {unit.unit_id: unit.payload for unit in after.units}


@pytest.mark.parametrize("problem", ["duplicate_id", "duplicate_section", "wrong_id"])
def test_invalid_section_records_are_rejected(tmp_path, problem):
    row = {
        "unit_id": "test_001:11.2",
        "document_key": "test_001",
        "kind": "section",
        "section": {"code": "11.2"},
        "text": "副作用",
    }
    rows = [row]
    if problem == "duplicate_id":
        rows.append(dict(row))
    elif problem == "duplicate_section":
        rows.append(dict(row, unit_id="test_001:other"))
    else:
        row["unit_id"] = "test_001:other"
    path = tmp_path / "search_units.jsonl"
    path.write_text("".join(json.dumps(item) + "\n" for item in rows), encoding="utf-8")
    with pytest.raises(IndexSourceError, match="Invalid JSONL"):
        FileIndexSourceReader._read_units(path, "test_001")
