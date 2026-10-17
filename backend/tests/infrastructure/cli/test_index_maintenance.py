import hashlib
import sqlite3

import pytest
from backend.infrastructure.cli.index_maintenance import (
    checked_backup,
    verify_rebuild_preconditions,
)
from backend.tests.support.attachment_import_e2e_server import prepare_root


def test_consistent_backup_restores_all_logical_content_without_source_change(tmp_path):
    _, index = prepare_root(tmp_path)
    before = hashlib.sha256(index.read_bytes()).hexdigest()
    backup = tmp_path / "backup.sqlite3"
    snapshot = checked_backup(index, backup)
    assert snapshot["integrity"] == "ok"
    assert snapshot["tables"]["documents"] == 1
    assert snapshot["fingerprint"].startswith("content-v1:")
    verify_rebuild_preconditions(index, backup)
    assert hashlib.sha256(index.read_bytes()).hexdigest() == before


@pytest.mark.parametrize("missing", ["target", "backup"])
def test_missing_explicit_target_or_backup_refuses_update(tmp_path, missing):
    _, index = prepare_root(tmp_path)
    before = index.read_bytes()
    with pytest.raises(RuntimeError, match="explicit|backup"):
        verify_rebuild_preconditions(None if missing == "target" else index, None)
    assert index.read_bytes() == before


def test_unmanaged_index_is_not_migrated_or_backed_up(tmp_path):
    index = tmp_path / "unmanaged.sqlite3"
    with sqlite3.connect(index) as connection:
        connection.execute("CREATE TABLE custom(value TEXT)")
    before = index.read_bytes()
    backup = tmp_path / "backup.sqlite3"
    with pytest.raises(RuntimeError, match="unmanaged"):
        checked_backup(index, backup)
    assert not backup.exists()
    assert index.read_bytes() == before


def test_active_writer_is_not_stopped_or_copied(tmp_path):
    _, index = prepare_root(tmp_path)
    with sqlite3.connect(index) as writer:
        writer.execute("BEGIN IMMEDIATE")
        with pytest.raises(RuntimeError, match="open|writer"):
            checked_backup(index, tmp_path / "backup.sqlite3")
        assert writer.in_transaction
        writer.rollback()


def test_existing_but_unverified_backup_refuses_update(tmp_path):
    _, index = prepare_root(tmp_path)
    backup = tmp_path / "backup.sqlite3"
    checked_backup(index, backup)
    with sqlite3.connect(backup) as connection:
        connection.execute(
            "UPDATE index_meta SET value='different' WHERE key='source_fingerprint'"
        )
    before = index.read_bytes()
    with pytest.raises(RuntimeError, match="does not match"):
        verify_rebuild_preconditions(index, backup)
    assert index.read_bytes() == before
