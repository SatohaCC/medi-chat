"""旧v3索引移行CLIのコピー先保護を検証する。"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import sqlite3
import subprocess
import sys
from contextlib import closing
from dataclasses import replace
from pathlib import Path

import pytest
import sqlalchemy
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from backend.application.medicine.product_models import (
    RegisteredMedicine,
    ResolvedMedicine,
)
from backend.domain.attachment.identifiers import DocumentId
from backend.domain.attachment.primitives import PmdaUrl
from backend.domain.attachment.value_objects import (
    AttachmentProductRevision,
    MedicineDocumentReference,
)
from backend.domain.medicine.entities import MedicineProduct
from backend.domain.medicine.identifiers import YjCode
from backend.domain.medicine.value_objects import MedicineMatch as DomainMedicineMatch
from backend.domain.retrieval.primitives import (
    DetectionSource,
    SearchKeyword,
    SearchSectionCode,
)
from backend.domain.retrieval.value_objects import SearchCriteria
from backend.infrastructure.cli import migrate_legacy_index
from backend.infrastructure.persistence import legacy_migration_verifier
from backend.infrastructure.persistence.evidence_reader import SqlAlchemyEvidenceReader
from backend.infrastructure.persistence.index_reader import SqlAlchemyIndexReader
from backend.infrastructure.persistence.legacy_content_validator import (
    validate_legacy_content,
)
from backend.infrastructure.persistence.legacy_index_backup import backup_legacy_index
from backend.infrastructure.persistence.legacy_schema_validator import (
    validate_legacy_schema,
)
from backend.infrastructure.persistence.medicine_reader import SqlAlchemyMedicineReader
from backend.infrastructure.persistence.sqlite_engine import create_sqlite_engine
from backend.migrations.legacy_copy_stamp import STAMP_COPY_ATTRIBUTE
from backend.tests.infrastructure.persistence.test_alembic_migrations import (
    _snapshot_existing_database,
)
from backend.tests.support.legacy_v3.package_insert_index import (
    PackageInsertIndexBuilder,
)
from backend.tests.support.legacy_v3.sqlite_database import SQLiteDatabase
from backend.tests.support.paths import BACKEND_ROOT, PROJECT_ROOT
from backend.tests.support.storage_fixtures import write_structured_document
from sqlalchemy.engine import URL


@pytest.mark.parametrize(
    "destination", ["same_absolute", "same_relative_absolute", "existing_output"]
)
def test_unsafe_migration_destinations_are_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    destination: str,
) -> None:
    structured = write_structured_document(tmp_path, unit_count=3)
    source = tmp_path / "legacy.sqlite3"
    PackageInsertIndexBuilder(structured, SQLiteDatabase(source)).build_if_needed()
    source_before = _snapshot_existing_database(source)
    assert source_before.revision is None
    assert ("schema_version", "3") in source_before.rows["index_meta"]
    assert len(source_before.rows["units"]) == 3
    output = tmp_path / "existing.sqlite3"
    if destination == "existing_output":
        with closing(sqlite3.connect(output)) as connection:
            connection.execute("CREATE TABLE sentinel (value TEXT NOT NULL)")
            connection.execute(
                "INSERT INTO sentinel VALUES ('preserve existing output')"
            )
            connection.commit()
        output_before = _snapshot_existing_database(output)
        source_argument, output_argument = str(source), str(output)
        reason_terms = ("exist", "存在")
    else:
        output = source
        output_before = source_before
        source_argument = (
            source.name if destination == "same_relative_absolute" else str(source)
        )
        output_argument = str(source)
        reason_terms = ("same", "同一")
    source_bytes, output_bytes = source.read_bytes(), output.read_bytes()
    arguments = ["--source-index", source_argument, "--output-index", output_argument]
    repo_root = PROJECT_ROOT
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(repo_root)
    process = subprocess.run(
        [
            sys.executable,
            "-m",
            "backend.infrastructure.cli.migrate_legacy_index",
            *arguments,
        ],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
        check=False,
    )
    operations: list[str] = []

    def forbidden_operation(*args: object, **kwargs: object) -> None:
        operations.append("connection or copy")
        raise AssertionError(
            "unsafe destination must be rejected before connection/copy"
        )

    error: Exception | SystemExit | None = None
    capsys.readouterr()
    with monkeypatch.context() as guard:
        guard.chdir(tmp_path)
        guard.setattr(sys, "argv", ["migrate_legacy_index", *arguments])
        guard.setattr(sqlite3, "connect", forbidden_operation)
        guard.setattr(sqlalchemy, "create_engine", forbidden_operation)
        for operation in ("copy", "copy2", "copyfile"):
            guard.setattr(shutil, operation, forbidden_operation)
        try:
            result = migrate_legacy_index.main()
        except (Exception, SystemExit) as caught:
            error = caught
            result = None
    captured = capsys.readouterr()
    # 未実装でも保持の観測を先に完了し、正しいRed原因をそのまま返す。
    assert source.read_bytes() == source_bytes
    assert output.read_bytes() == output_bytes
    assert _snapshot_existing_database(source) == source_before
    assert _snapshot_existing_database(output) == output_before
    assert operations == []
    if isinstance(error, NotImplementedError):
        raise error
    if isinstance(error, (ImportError, TypeError)):
        raise error
    assert process.returncode != 0
    subprocess_reason = (process.stdout + process.stderr).lower()
    assert any(term in subprocess_reason for term in reason_terms), subprocess_reason
    if isinstance(error, SystemExit):
        assert error.code not in (None, 0)
    else:
        assert error is not None or result not in (None, 0)
    direct_reason = (captured.out + captured.err + str(error or "")).lower()
    assert any(term in direct_reason for term in reason_terms), direct_reason


def _change_legacy_schema(index_path: Path, mismatch: str) -> None:
    with closing(sqlite3.connect(index_path)) as connection:
        if mismatch == "schema_version":
            connection.execute(
                "UPDATE index_meta SET value='2' WHERE key='schema_version'"
            )
        elif mismatch == "column":
            connection.execute(
                "ALTER TABLE medicines RENAME COLUMN english_name TO unexpected_name"
            )
        elif mismatch == "primary_key":
            connection.execute("ALTER TABLE documents RENAME TO old_documents")
            connection.execute(
                "CREATE TABLE documents (document_key TEXT, payload_json TEXT NOT NULL)"
            )
            connection.execute("INSERT INTO documents SELECT * FROM old_documents")
            connection.execute("DROP TABLE old_documents")
        elif mismatch == "index":
            connection.execute("DROP INDEX idx_medicines_yj")
            connection.execute("CREATE INDEX idx_medicines_yj ON medicines(brand_name)")
        elif mismatch == "fts":
            rows = connection.execute("SELECT * FROM unit_fts").fetchall()
            connection.execute("DROP TABLE unit_fts")
            connection.execute(
                "CREATE VIRTUAL TABLE unit_fts USING fts5("
                "unit_id UNINDEXED, document_key UNINDEXED, section_code UNINDEXED, "
                "kind UNINDEXED, query_text, drug_name, tokenize='unicode61')"
            )
            connection.executemany(
                "INSERT INTO unit_fts VALUES (?, ?, ?, ?, ?, ?)", rows
            )
        else:
            raise AssertionError(f"unknown schema mismatch: {mismatch}")
        connection.commit()


@pytest.mark.parametrize(
    ("mismatch", "reason_terms"),
    [
        ("schema_version", ("schema_version",)),
        ("column", ("column", "列")),
        ("primary_key", ("primary key", "primary_key", "pk", "主キー")),
        ("index", ("index", "索引")),
        ("fts", ("fts",)),
    ],
    ids=["schema_version", "column", "primary_key", "index", "fts"],
)
def test_legacy_schema_mismatches_prevent_stamp(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    mismatch: str,
    reason_terms: tuple[str, ...],
) -> None:
    structured = write_structured_document(tmp_path, unit_count=3)
    source = tmp_path / "legacy.sqlite3"
    PackageInsertIndexBuilder(structured, SQLiteDatabase(source)).build_if_needed()
    _change_legacy_schema(source, mismatch)
    source_before = _snapshot_existing_database(source)
    source_bytes = source.read_bytes()
    independent_copy = tmp_path / "validator-copy.sqlite3"
    with (
        closing(sqlite3.connect(f"{source.as_uri()}?mode=ro", uri=True)) as origin,
        closing(sqlite3.connect(independent_copy)) as target,
    ):
        origin.backup(target)
    copy_before = _snapshot_existing_database(independent_copy)
    copy_bytes = independent_copy.read_bytes()
    assert copy_before == source_before
    validator_error: Exception | None = None
    try:
        validate_legacy_schema(independent_copy)
    except Exception as caught:
        validator_error = caught

    output = tmp_path / "module-output.sqlite3"
    repo_root = PROJECT_ROOT
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(repo_root)
    process = subprocess.run(
        [
            sys.executable,
            "-m",
            "backend.infrastructure.cli.migrate_legacy_index",
            "--source-index",
            str(source),
            "--output-index",
            str(output),
        ],
        cwd=repo_root,
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
        check=False,
    )
    direct_output = tmp_path / "direct-output.sqlite3"
    stamp_calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

    def record_stamp(*args: object, **kwargs: object) -> None:
        stamp_calls.append((args, kwargs))

    cli_error: Exception | SystemExit | None = None
    capsys.readouterr()
    with monkeypatch.context() as guard:
        guard.setattr(command, "stamp", record_stamp)
        guard.setattr(
            sys,
            "argv",
            [
                "migrate_legacy_index",
                "--source-index",
                str(source),
                "--output-index",
                str(direct_output),
            ],
        )
        try:
            result = migrate_legacy_index.main()
        except (Exception, SystemExit) as caught:
            cli_error = caught
            result = None
    captured = capsys.readouterr()
    assert source.read_bytes() == source_bytes
    assert _snapshot_existing_database(source) == source_before
    assert independent_copy.read_bytes() == copy_bytes
    assert _snapshot_existing_database(independent_copy) == copy_before
    assert stamp_calls == []
    # 両入口を実行し保持を観測した後、明示未実装をRed原因として返す。
    for error in (validator_error, cli_error):
        if isinstance(error, (NotImplementedError, ImportError, TypeError)):
            raise error
    assert isinstance(validator_error, ValueError)
    assert any(term in str(validator_error).lower() for term in reason_terms)
    assert process.returncode != 0
    module_reason = (process.stdout + process.stderr).lower()
    assert any(term in module_reason for term in reason_terms), module_reason
    if isinstance(cli_error, SystemExit):
        assert cli_error.code not in (None, 0)
    else:
        assert cli_error is not None or result not in (None, 0)
    cli_reason = (captured.out + captured.err + str(cli_error or "")).lower()
    assert any(term in cli_reason for term in reason_terms), cli_reason
    for failed_copy in (output, direct_output):
        assert failed_copy.is_file()
        assert _snapshot_existing_database(failed_copy) == source_before


def _change_legacy_content(index_path: Path, corruption: str) -> None:
    page_location: tuple[int, int] | None = None
    with closing(sqlite3.connect(index_path)) as connection:
        if corruption == "invalid_json":
            connection.execute("UPDATE documents SET payload_json='{not valid JSON'")
        elif corruption == "missing_document":
            connection.execute(
                "UPDATE units SET document_key='missing_document' WHERE unit_id='test_001:000'"
            )
        elif corruption == "fts_mismatch":
            connection.execute(
                "UPDATE unit_fts SET unit_id='missing_unit' WHERE unit_id='test_001:000'"
            )
        elif corruption == "integrity":
            assert connection.execute("PRAGMA integrity_check").fetchall() == [("ok",)]
            page_size = connection.execute("PRAGMA page_size").fetchone()[0]
            rootpage = connection.execute(
                "SELECT rootpage FROM sqlite_master WHERE name='documents'"
            ).fetchone()[0]
            assert rootpage > 1
            page_location = (rootpage, page_size)
        else:
            raise AssertionError(f"unknown content corruption: {corruption}")
        connection.commit()
    if corruption == "integrity":
        assert page_location is not None
        rootpage, page_size = page_location
        payload = bytearray(index_path.read_bytes())
        page_offset = (rootpage - 1) * page_size
        assert payload[page_offset] == 13  # 実documentsのtable leaf b-tree page。
        payload[page_offset] = 255
        index_path.write_bytes(payload)
        with closing(
            sqlite3.connect(f"{index_path.as_uri()}?mode=ro", uri=True)
        ) as connection:
            try:
                integrity = connection.execute("PRAGMA integrity_check").fetchall()
            except sqlite3.DatabaseError as error:
                assert "malformed" in str(error).lower()
            else:
                assert integrity != [("ok",)]


@pytest.mark.parametrize(
    ("corruption", "reason_terms"),
    [
        ("invalid_json", ("json",)),
        ("missing_document", ("document", "文書")),
        ("fts_mismatch", ("fts",)),
        ("integrity", ("integrity", "malformed", "corrupt", "破損", "整合")),
    ],
    ids=["invalid_json", "missing_document", "fts_mismatch", "integrity"],
)
def test_corrupt_legacy_content_is_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    corruption: str,
    reason_terms: tuple[str, ...],
) -> None:
    structured = write_structured_document(tmp_path, unit_count=3)
    source = tmp_path / "legacy.sqlite3"
    PackageInsertIndexBuilder(structured, SQLiteDatabase(source)).build_if_needed()
    _change_legacy_content(source, corruption)
    source_bytes = source.read_bytes()
    source_files = {
        path.relative_to(structured): path.read_bytes()
        for path in structured.rglob("*")
        if path.is_file()
    }
    source_before = (
        _snapshot_existing_database(source) if corruption != "integrity" else None
    )
    independent_copy = tmp_path / "content-validator-copy.sqlite3"
    independent_copy.write_bytes(source_bytes)
    validator_error: Exception | None = None
    try:
        validate_legacy_content(independent_copy)
    except Exception as caught:
        validator_error = caught
    repo_root = PROJECT_ROOT
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(repo_root)
    process = subprocess.run(
        [
            sys.executable,
            "-m",
            "backend.infrastructure.cli.migrate_legacy_index",
            "--source-index",
            str(source),
            "--output-index",
            str(tmp_path / "module-output.sqlite3"),
        ],
        cwd=repo_root,
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
        check=False,
    )
    stamp_calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

    def record_stamp(*args: object, **kwargs: object) -> None:
        stamp_calls.append((args, kwargs))

    cli_error: Exception | SystemExit | None = None
    capsys.readouterr()
    with monkeypatch.context() as guard:
        guard.setattr(command, "stamp", record_stamp)
        guard.setattr(
            sys,
            "argv",
            [
                "migrate_legacy_index",
                "--source-index",
                str(source),
                "--output-index",
                str(tmp_path / "direct-output.sqlite3"),
            ],
        )
        try:
            result = migrate_legacy_index.main()
        except (Exception, SystemExit) as caught:
            cli_error = caught
            result = None
    captured = capsys.readouterr()
    assert source.read_bytes() == source_bytes
    assert independent_copy.read_bytes() == source_bytes
    assert {
        path.relative_to(structured): path.read_bytes()
        for path in structured.rglob("*")
        if path.is_file()
    } == source_files
    if source_before is not None:
        assert _snapshot_existing_database(source) == source_before
        assert _snapshot_existing_database(independent_copy) == source_before
    assert stamp_calls == []
    for error in (validator_error, cli_error):
        if isinstance(error, (NotImplementedError, ImportError, TypeError)):
            raise error
    assert isinstance(validator_error, ValueError)
    assert any(term in str(validator_error).lower() for term in reason_terms)
    assert process.returncode != 0
    module_reason = (process.stdout + process.stderr).lower()
    assert any(term in module_reason for term in reason_terms), module_reason
    if isinstance(cli_error, SystemExit):
        assert cli_error.code not in (None, 0)
    else:
        assert cli_error is not None or result not in (None, 0)
    direct_reason = (captured.out + captured.err + str(cli_error or "")).lower()
    assert any(term in direct_reason for term in reason_terms), direct_reason
    for success_text in ("migration complete", "verified output", "移行完了"):
        assert success_text not in process.stdout.lower()
        assert success_text not in captured.out.lower()


def test_backup_copies_committed_wal_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    structured = write_structured_document(tmp_path, unit_count=3)
    source = tmp_path / "wal-legacy.sqlite3"
    PackageInsertIndexBuilder(structured, SQLiteDatabase(source)).build_if_needed()
    with closing(sqlite3.connect(source)) as writer:
        assert writer.execute("PRAGMA journal_mode=WAL").fetchone() == ("wal",)
        writer.execute("PRAGMA wal_autocheckpoint=0")
        writer.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        baseline = _snapshot_existing_database(source)
        main_bytes = source.read_bytes()
        unit_payload = json.loads(
            writer.execute(
                "SELECT payload_json FROM units WHERE unit_id='test_001:000'"
            ).fetchone()[0]
        )
        unit_payload["unit_id"] = "test_001:wal_committed"
        unit_payload["text"] = "新記載のWAL確定データに注意してください。"
        writer.execute(
            "INSERT INTO units VALUES (?, ?, ?, ?, ?)",
            (
                "test_001:wal_committed",
                "test_001",
                "11.1",
                "text",
                json.dumps(unit_payload, ensure_ascii=False),
            ),
        )
        writer.execute(
            "INSERT INTO unit_fts VALUES (?, ?, ?, ?, ?, ?)",
            (
                "test_001:wal_committed",
                "test_001",
                "11.1",
                "text",
                "新記載のwal確定データに注意してください 重大な副作用",
                "",
            ),
        )
        writer.execute(
            "UPDATE index_meta SET value='tc36-committed-wal' WHERE key='source_fingerprint'"
        )
        writer.commit()
        wal_path = Path(str(source) + "-wal")
        assert wal_path.is_file()
        wal_bytes = wal_path.read_bytes()
        assert len(wal_bytes) > 32
        assert source.read_bytes() == main_bytes
        validate_legacy_content(source)
        committed = _snapshot_existing_database(source)
        assert len(committed.rows["units"]) == 4
        assert ("source_fingerprint", "tc36-committed-wal") in committed.rows[
            "index_meta"
        ]
        assert committed.schema == baseline.schema
        ordinary_copy = tmp_path / "ordinary-main-copy.sqlite3"
        ordinary_copy.write_bytes(source.read_bytes())
        assert _snapshot_existing_database(ordinary_copy) == baseline

        real_connect = sqlite3.connect
        connection_calls: list[tuple[str, bool]] = []
        backup_calls: list[tuple[str, str]] = []
        changes_at_close: list[tuple[str, int]] = []

        class BackupConnection:
            def __init__(self, connection: sqlite3.Connection, path: str) -> None:
                self.connection = connection
                self.path = path

            def backup(self, target: BackupConnection) -> None:
                backup_calls.append((self.path, target.path))
                self.connection.backup(target.connection)

            def close(self) -> None:
                changes_at_close.append((self.path, self.connection.total_changes))
                self.connection.close()

        def recording_connect(
            database: str | Path, *, uri: bool = False
        ) -> BackupConnection:
            connection_calls.append((str(database), uri))
            return BackupConnection(real_connect(database, uri=uri), str(database))

        output = tmp_path / "backup-output.sqlite3"
        with monkeypatch.context() as guard:
            guard.setattr(sqlite3, "connect", recording_connect)
            backup_legacy_index(source, output)
        source_uri = f"{source.resolve().as_uri()}?mode=ro"
        assert connection_calls == [(source_uri, True), (str(output), False)]
        assert backup_calls == [(source_uri, str(output))]
        assert changes_at_close == [(str(output), 0), (source_uri, 0)]
        assert source.read_bytes() == main_bytes
        assert wal_path.read_bytes() == wal_bytes
        assert _snapshot_existing_database(source) == committed
        assert _snapshot_existing_database(output) == committed
        validate_legacy_content(output)
        with closing(sqlite3.connect(output)) as copied:
            assert copied.execute("PRAGMA integrity_check").fetchall() == [("ok",)]
            assert copied.execute(
                "SELECT unit_id FROM unit_fts WHERE unit_fts MATCH ? ORDER BY unit_id",
                ("新記載",),
            ).fetchall() == [("test_001:wal_committed",)]
            assert copied.execute(
                "SELECT value FROM index_meta WHERE key='source_fingerprint'"
            ).fetchone() == ("tc36-committed-wal",)


def test_valid_v3_copy_preserves_search_and_source(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    structured = write_structured_document(tmp_path, unit_count=3)
    source = tmp_path / "legacy.sqlite3"
    PackageInsertIndexBuilder(structured, SQLiteDatabase(source)).build_if_needed()
    validate_legacy_schema(source)
    validate_legacy_content(source)
    source_before = _snapshot_existing_database(source)
    source_bytes = source.read_bytes()
    expected_document = json.loads(
        (structured / "test_001" / "document.json").read_text(encoding="utf-8")
    )
    repo_root = PROJECT_ROOT
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(repo_root)
    module_output = tmp_path / "module-output.sqlite3"
    process = subprocess.run(
        [
            sys.executable,
            "-m",
            "backend.infrastructure.cli.migrate_legacy_index",
            "--source-index",
            str(source),
            "--output-index",
            str(module_output),
        ],
        cwd=repo_root,
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
        check=False,
    )
    events: list[str] = []
    real_schema, real_content = validate_legacy_schema, validate_legacy_content
    real_stamp, real_upgrade = command.stamp, command.upgrade
    direct_output = tmp_path / "direct-output.sqlite3"

    def record_schema(path: Path) -> None:
        assert path == direct_output
        real_schema(path)
        events.append("schema_validated")

    def record_content(path: Path) -> None:
        assert path == direct_output
        real_content(path)
        events.append("content_validated")

    def record_stamp(config: Config, revision: str) -> None:
        events.append("stamp")
        real_stamp(config, revision)

    def record_upgrade(config: Config, revision: str) -> None:
        events.append("upgrade")
        real_upgrade(config, revision)

    error: Exception | SystemExit | None = None
    capsys.readouterr()
    with monkeypatch.context() as guard:
        guard.setattr(migrate_legacy_index, "validate_legacy_schema", record_schema)
        guard.setattr(migrate_legacy_index, "validate_legacy_content", record_content)
        guard.setattr(command, "stamp", record_stamp)
        guard.setattr(command, "upgrade", record_upgrade)
        guard.setattr(
            sys,
            "argv",
            [
                "migrate_legacy_index",
                "--source-index",
                str(source),
                "--output-index",
                str(direct_output),
            ],
        )
        try:
            result = migrate_legacy_index.main()
        except (Exception, SystemExit) as caught:
            error = caught
            result = None
    captured = capsys.readouterr()
    assert source.read_bytes() == source_bytes
    assert _snapshot_existing_database(source) == source_before
    assert events[:2] == ["schema_validated", "content_validated"]
    if isinstance(error, (NotImplementedError, ImportError, TypeError)):
        raise error
    assert error is None
    assert result == 0
    assert process.returncode == 0, process.stdout + process.stderr
    assert events.count("stamp") == 1
    assert events.count("upgrade") == 1
    assert events.index("content_validated") < events.index("stamp")
    assert events.index("stamp") < events.index("upgrade")
    ini = BACKEND_ROOT / "alembic.ini"
    head = ScriptDirectory.from_config(Config(str(ini))).get_current_head()
    assert head is not None
    for output, report in (
        (module_output, process.stdout),
        (direct_output, captured.out),
    ):
        migrated = _snapshot_existing_database(output)
        assert migrated.revision == (head,)
        registration_tables = {
            "registration_receipts",
            "registration_version_artifacts",
            "active_registrations",
            "registration_generations",
            "registration_state",
            "generation_leases",
            "registration_owned_files",
        }
        assert set(migrated.rows) - set(source_before.rows) == registration_tables | {
            "alembic_version"
        }
        assert all(migrated.rows[name] == () for name in registration_tables)
        assert {
            key: rows
            for key, rows in migrated.rows.items()
            if key in source_before.rows
        } == source_before.rows
        assert (
            tuple(
                row
                for row in migrated.schema
                if row[2] not in registration_tables | {"alembic_version"}
            )
            == source_before.schema
        )
        assert str(source) in report
        assert str(output) in report
        assert head in report
        assert any(term in report.lower() for term in ("verified", "検証"))
        engine = create_sqlite_engine(
            URL.create("sqlite", database=output.as_posix()).render_as_string(
                hide_password=False
            )
        )
        try:
            index_reader = SqlAlchemyIndexReader(engine)
            assert (
                asyncio.run(index_reader.get_document("test_001")) == expected_document
            )
            assert asyncio.run(index_reader.read_index_stats()) == {
                "document_count": 1,
                "unit_count": 3,
            }
            assert asyncio.run(SqlAlchemyMedicineReader(engine).read_medicines()) == (
                RegisteredMedicine(
                    medicine=MedicineProduct(
                        yj_code=YjCode("1234567A0000"),
                        brand_name="テスト薬",
                        generic_name="テスト成分",
                        english_name="",
                        hiragana_name="",
                    ),
                    reference=MedicineDocumentReference(
                        document_id=DocumentId("test_001"),
                        pmda_url=PmdaUrl("https://example.test/package-insert"),
                        revision=AttachmentProductRevision({}),
                    ),
                ),
            )
            medicines = (
                ResolvedMedicine(
                    medicine=DomainMedicineMatch(
                        generic_name="テスト成分",
                        brand_names=("テスト薬",),
                        yj_codes=("1234567A0000",),
                    ),
                    document_ids=("test_001",),
                ),
            )
            reader = SqlAlchemyEvidenceReader(engine)
            for criteria in (
                SearchCriteria(
                    source=DetectionSource("logic"),
                    section_codes=(SearchSectionCode("11.1"),),
                ),
                SearchCriteria(
                    source=DetectionSource("keyword"), keywords=(SearchKeyword("頭痛"),)
                ),
                SearchCriteria(
                    source=DetectionSource("keyword"),
                    keywords=(SearchKeyword("注意して"),),
                ),
            ):
                evidence = asyncio.run(reader.search(criteria, medicines))
                assert {item.unit_id.value for item in evidence} == {
                    "test_001:000",
                    "test_001:001",
                    "test_001:002",
                }
                assert {item.excerpt for item in evidence} == {
                    "頭痛に注意してください。記載0",
                    "頭痛に注意してください。記載1",
                    "頭痛に注意してください。記載2",
                }
                assert all(
                    item.document_id.value == "test_001"
                    and item.section == {"code": "11.1", "title": "重大な副作用"}
                    for item in evidence
                )
        finally:
            engine.dispose()


@pytest.mark.parametrize(
    "failure", ["stamp", "upgrade", "count", "search", "fingerprint"]
)
def test_failed_migration_never_reports_verified_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    failure: str,
) -> None:
    structured = write_structured_document(tmp_path, unit_count=3)
    source = tmp_path / "legacy.sqlite3"
    output = tmp_path / "failed-output.sqlite3"
    PackageInsertIndexBuilder(structured, SQLiteDatabase(source)).build_if_needed()
    validate_legacy_schema(source)
    validate_legacy_content(source)
    before = _snapshot_existing_database(source)
    source_bytes = source.read_bytes()
    source_files = {
        path.relative_to(structured): path.read_bytes()
        for path in structured.rglob("*")
        if path.is_file()
    }
    real_stamp, real_upgrade = command.stamp, command.upgrade
    real_snapshot = legacy_migration_verifier.read_legacy_migration_snapshot
    configs: list[Config] = []
    events: list[str] = []

    def failing_stamp(config: Config, revision: str) -> None:
        configs.append(config)
        assert STAMP_COPY_ATTRIBUTE in config.attributes
        events.append("stamp")
        if failure == "stamp":
            raise ValueError("injected stamp failure")
        real_stamp(config, revision)
        assert _snapshot_existing_database(output).revision == ("0001_v3_schema",)

    def failing_upgrade(config: Config, revision: str) -> None:
        configs.append(config)
        assert STAMP_COPY_ATTRIBUTE not in config.attributes
        events.append("upgrade")
        if failure == "upgrade":
            raise ValueError("injected upgrade failure")
        real_upgrade(config, revision)
        if failure in ("count", "fingerprint"):
            with closing(sqlite3.connect(output)) as connection:
                if failure == "count":
                    connection.execute("DELETE FROM units WHERE unit_id='test_001:000'")
                    assert connection.execute(
                        "SELECT COUNT(*) FROM units"
                    ).fetchone() == (2,)
                else:
                    connection.execute(
                        "UPDATE index_meta SET value='unexpected-fingerprint' WHERE key='source_fingerprint'"
                    )
                    assert connection.execute(
                        "SELECT value FROM index_meta WHERE key='source_fingerprint'"
                    ).fetchone() == ("unexpected-fingerprint",)
                connection.commit()
            events.append(failure)

    def changed_search_snapshot(
        index_path: Path, *, criteria: tuple[SearchCriteria, ...] | None = None
    ) -> legacy_migration_verifier.LegacyMigrationSnapshot:
        snapshot = real_snapshot(index_path, criteria=criteria)
        if failure == "search" and criteria is not None:
            assert len(snapshot.searches) == 3
            assert len(snapshot.searches[-1]) == 3
            events.append("search")
            return replace(
                snapshot, searches=(*snapshot.searches[:-1], snapshot.searches[-1][:-1])
            )
        return snapshot

    error: Exception | SystemExit | None = None
    capsys.readouterr()
    environment_before = dict(os.environ)
    with monkeypatch.context() as guard:
        guard.setattr(command, "stamp", failing_stamp)
        guard.setattr(command, "upgrade", failing_upgrade)
        guard.setattr(
            legacy_migration_verifier,
            "read_legacy_migration_snapshot",
            changed_search_snapshot,
        )
        guard.setattr(
            sys,
            "argv",
            [
                "migrate_legacy_index",
                "--source-index",
                str(source),
                "--output-index",
                str(output),
            ],
        )
        try:
            result = migrate_legacy_index.main()
        except (Exception, SystemExit) as caught:
            error = caught
            result = None
    captured = capsys.readouterr()
    assert source.read_bytes() == source_bytes
    assert _snapshot_existing_database(source) == before
    assert {
        path.relative_to(structured): path.read_bytes()
        for path in structured.rglob("*")
        if path.is_file()
    } == source_files
    assert dict(os.environ) == environment_before
    assert configs
    assert all(STAMP_COPY_ATTRIBUTE not in config.attributes for config in configs)
    assert output.is_file()
    if isinstance(error, (NotImplementedError, ImportError, TypeError)):
        raise error
    assert isinstance(error, SystemExit)
    assert error.code not in (None, 0)
    assert result is None
    assert events == (
        ["stamp"]
        if failure == "stamp"
        else ["stamp", "upgrade"]
        if failure == "upgrade"
        else ["stamp", "upgrade", failure]
    )
    reason = (captured.out + captured.err).lower()
    assert (failure if failure in ("stamp", "upgrade") else "verification") in reason
    assert captured.out == ""
    assert "verified migration" not in reason
