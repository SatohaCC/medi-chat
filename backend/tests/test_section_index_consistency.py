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
from backend.infrastructure.sources.registration_source import read_registered_snapshot
from backend.tests.registration_runtime_fixtures import (
    register_synthetic_prepared_index,
)
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
    register_synthetic_prepared_index(source, index)
    verify_index_readiness(source, index)
    with sqlite3.connect(index) as connection:
        files = json.loads(
            connection.execute(
                "SELECT files_json FROM registration_generations WHERE generation_id="
                "(SELECT generation_id FROM registration_state WHERE singleton=1)"
            ).fetchone()[0]
        )
    units = Path(files[0]["path"])
    stat = units.stat()
    saved_bytes = units.read_bytes()
    content = units.read_text(encoding="utf-8")
    expected = {row["unit_id"]: row for row in map(json.loads, content.splitlines())}
    assert "頭痛" in content
    units.write_text(content.replace("頭痛", "腹痛"), encoding="utf-8")
    os.utime(units, ns=(stat.st_atime_ns, stat.st_mtime_ns))
    assert manifest.read_text(encoding="utf-8") == '{"document_count": 1}'
    with pytest.raises(RuntimeError, match="Published artifact content differs"):
        verify_index_readiness(source, index)
    units.write_bytes(saved_bytes)
    assert units.read_bytes() == saved_bytes
    snapshot = read_registered_snapshot(index)
    assert snapshot is not None
    writer.replace(snapshot)
    # Unregistered input must not silently become public during an active rebuild.
    unpublished = source / "unregistered"
    unpublished.mkdir()
    (unpublished / "search_units.jsonl").write_text("unregistered", encoding="utf-8")
    verify_index_readiness(source, index)
    with sqlite3.connect(index) as connection:
        actual = {
            row[0]: json.loads(row[1])
            for row in connection.execute("SELECT unit_id, payload_json FROM units")
        }
    assert actual == expected


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
