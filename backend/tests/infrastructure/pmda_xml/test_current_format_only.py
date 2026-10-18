"""旧データを修復・移行せず、現在形式だけを受け付ける。"""

import hashlib
import importlib.util
import json
import sqlite3

import pytest
from backend.application.attachment_import.import_errors import ImportConflict
from backend.application.indexing.index_errors import IndexSourceError
from backend.infrastructure.persistence.attachment_import_store import (
    FileAttachmentImportStore,
)
from backend.infrastructure.sources.file_index_source import FileIndexSourceReader
from backend.tests.infrastructure.persistence.test_alembic_migrations import (
    _migrate_database,
    _snapshot_existing_database,
)
from backend.tests.support.attachment_import_fixtures import encoded, xml_source


def test_old_document_json_is_rejected_instead_of_converted(tmp_path):
    document = tmp_path / "sample"
    document.mkdir()
    (document / "document.json").write_text(
        json.dumps(
            {
                "schema_version": "medi-chat.pmda-prescription-xml.v1",
                "document": {},
                "source": {},
                "sections": [],
            }
        ),
        encoding="utf-8",
    )
    (document / "search_units.jsonl").write_text("", encoding="utf-8")
    with pytest.raises(IndexSourceError, match="Unsupported document format"):
        FileIndexSourceReader(tmp_path).read_snapshot()


def test_old_managed_sqlite_revision_is_rejected_without_stamp_or_upgrade(tmp_path):
    index = tmp_path / "old.sqlite3"
    with sqlite3.connect(index) as connection:
        connection.execute(
            "CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL PRIMARY KEY)"
        )
        connection.execute("INSERT INTO alembic_version VALUES ('0001_v3_schema')")
    before = _snapshot_existing_database(index)
    with pytest.raises(ValueError, match="Unsupported database revision"):
        _migrate_database(index, tmp_path)
    assert _snapshot_existing_database(index) == before


@pytest.mark.parametrize(
    "schema_version", [None, "medi-chat.pmda-sections.v2", "medi-chat.pmda-sections.v3"]
)
def test_old_search_jsonl_is_rejected_at_file_boundary(tmp_path, schema_version):
    path = tmp_path / "search_units.jsonl"
    path.write_text(
        json.dumps(
            {
                "schema_version": schema_version,
                "document_key": "test",
                "unit_id": "test:10.1",
                "text": "old",
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(IndexSourceError, match="Unsupported search data format"):
        FileIndexSourceReader._read_units(path, "test")


def test_old_saved_import_is_not_reused_even_with_valid_integrity_manifest(tmp_path):
    store = FileAttachmentImportStore(tmp_path)
    source = xml_source()
    bundle = encoded(source)
    store.commit(bundle, source)
    target = store._target(bundle.document_id, bundle.source_sha256)
    document_path = target / "document.json"
    document = json.loads(document_path.read_bytes())
    document["schema_version"] = "medi-chat.pmda-prescription-xml.v1"
    old = json.dumps(document, ensure_ascii=False).encode("utf-8")
    document_path.write_bytes(old)
    integrity_path = target / "integrity.json"
    integrity = json.loads(integrity_path.read_bytes())
    integrity["document.json"] = hashlib.sha256(old).hexdigest()
    integrity_path.write_text(json.dumps(integrity), encoding="utf-8")
    with pytest.raises(ImportConflict, match="inconsistent"):
        store.read(bundle.document_id, bundle.source_sha256)
    assert (target / "source.xml").read_bytes() == source


@pytest.mark.parametrize(
    "module",
    [
        "backend.infrastructure.cli.migrate_legacy_index",
        "backend.infrastructure.persistence.legacy_content_validator",
        "backend.infrastructure.persistence.legacy_schema_validator",
        "backend.infrastructure.persistence.legacy_index_backup",
        "backend.infrastructure.persistence.legacy_migration_verifier",
        "backend.migrations.legacy_copy_stamp",
    ],
)
def test_old_sqlite_migration_modules_are_removed(module):
    assert importlib.util.find_spec(module) is None
