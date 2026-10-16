"""明示migration/build済み索引だけを読取りで起動する契約。"""

from __future__ import annotations

import hashlib
import json
import socket
import sqlite3
import subprocess
from pathlib import Path

import httpx
import pytest
from backend.config.database_settings import resolve_database_settings
from backend.infrastructure.cli.configured_e2e_gate import run_gate
from backend.infrastructure.persistence.index_writer import SqlAlchemyIndexWriter
from backend.infrastructure.persistence.registration_reader import (
    read_registered_snapshot,
)
from backend.infrastructure.sources.file_index_source import FileIndexSourceReader
from backend.main import create_app
from backend.project_paths import PROJECT_ROOT
from backend.tests.registration_runtime_fixtures import (
    register_synthetic_prepared_index,
)
from backend.tests.startup_recovery_fixture import create_legacy_copy
from backend.tests.test_alembic_migrations import (
    _migrate_database,
    _snapshot_existing_database,
)
from backend.tests.test_package_insert_index import migrated_index as migrated_index
from sqlalchemy.engine import Engine


def test_real_legacy_copy_refuses_os_start_then_cli_recovers_same_copy(
    tmp_path, monkeypatch
):
    from argparse import Namespace

    from alembic import command as alembic_command
    from alembic.config import Config
    from backend.infrastructure.persistence.legacy_content_validator import (
        validate_legacy_content,
    )
    from backend.migrations.legacy_copy_stamp import (
        STAMP_COPY_ATTRIBUTE,
        LegacyCopyStamp,
        validate_stamp_copy,
    )
    from backend.tests.startup_recovery_fixture import restore_manifest_v3_fixture

    old = tmp_path / "historical-manifest.sqlite3"
    restore_manifest_v3_fixture(old)
    validate_legacy_content(old)
    stamp_config = Config(str(PROJECT_ROOT / "backend/alembic.ini"))
    stamp_config.cmd_opts = Namespace(x=[f"index_path={old.resolve()}"])
    approval = LegacyCopyStamp(old.resolve())
    validate_stamp_copy(approval, old)
    stamp_config.attributes[STAMP_COPY_ATTRIBUTE] = approval
    alembic_command.stamp(stamp_config, "0001_v3_schema")
    original = hashlib.sha256(old.read_bytes()).hexdigest()
    source, index = create_legacy_copy(tmp_path, old)
    copy_before = hashlib.sha256(index.read_bytes()).hexdigest()
    for name in [
        "OPENAI_API_KEY",
        "GEMINI_API_KEY",
        "GOOGLE_API_KEY",
        "JEV_API_KEY",
        "TYPESAFE_API_KEY",
    ]:
        monkeypatch.setenv(name, "")
    monkeypatch.setenv("PYTHON_DOTENV_DISABLED", "1")
    monkeypatch.setenv("MEDI_CHAT_STRUCTURED_DIR", str(source))
    monkeypatch.setenv("MEDI_CHAT_INDEX_PATH", str(index))
    monkeypatch.setenv("MEDI_CHAT_IMPORT_DIR", str(tmp_path / "imports"))
    failed = subprocess.run(
        [
            "uv",
            "run",
            "--project",
            str(PROJECT_ROOT / "backend"),
            "--locked",
            "uvicorn",
            "--app-dir",
            str(PROJECT_ROOT),
            "backend.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "3213",
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=40,
    )
    assert failed.returncode != 0
    assert "revision" in failed.stderr
    assert "Application startup complete" not in failed.stderr
    assert hashlib.sha256(index.read_bytes()).hexdigest() == copy_before
    import shutil

    from backend.tests.test_registration_initialization import command

    shutil.copytree(PROJECT_ROOT / "data/pmda/originals", tmp_path / "originals")
    _migrate_database(index, source)
    initialized = command(
        tmp_path,
        "backend.infrastructure.cli.initialize_registrations",
        "--originals-dir",
        tmp_path / "originals",
        "--structured-dir",
        source,
        "--index-path",
        index,
        "--import-dir",
        tmp_path / "imports",
    )
    assert initialized.returncode == 0, initialized.stdout + initialized.stderr
    rebuilt = subprocess.run(
        [
            "uv",
            "run",
            "--project",
            str(PROJECT_ROOT / "backend"),
            "--locked",
            "python",
            "-m",
            "backend.infrastructure.cli.build_search_index",
            "--structured-dir",
            str(source),
            "--index-path",
            str(index),
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert rebuilt.returncode == 0, rebuilt.stderr
    assert "'document_count': 7, 'unit_count': 267" in rebuilt.stdout
    assert "15 medicines loaded" in rebuilt.stdout
    with sqlite3.connect(index) as connection:
        assert [
            connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in ["documents", "units", "medicines"]
        ] == [7, 267, 15]
        assert (
            connection.execute(
                "SELECT value FROM index_meta WHERE key='source_fingerprint'"
            )
            .fetchone()[0]
            .startswith("content-v1:")
        )
    result = run_gate(
        resolve_database_settings(structured_dir=source, index_path=index), port=3213
    )
    assert {
        k: result["os_health"][k] for k in ("status", "document_count", "unit_count")
    } == {
        "status": "ok",
        "document_count": 7,
        "unit_count": 267,
    }
    with sqlite3.connect(index) as connection:
        assert (
            result["os_health"]["generation_id"]
            == connection.execute(
                "SELECT generation_id FROM registration_state WHERE singleton=1"
            ).fetchone()[0]
        )
    with socket.socket() as stopped:
        assert stopped.connect_ex(("127.0.0.1", 3213)) != 0
    print(
        json.dumps(
            {
                "legacy_failure_exit": failed.returncode,
                "legacy_failure": failed.stderr,
                "cli_exit": rebuilt.returncode,
                "cli_output": rebuilt.stdout,
                "health": result,
            },
            ensure_ascii=False,
        )
    )
    assert hashlib.sha256(old.read_bytes()).hexdigest() == original


@pytest.mark.asyncio
async def test_prepared_index_starts_without_mutation(
    migrated_index: tuple[Path, Engine],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source, engine = migrated_index
    SqlAlchemyIndexWriter(engine).replace(FileIndexSourceReader(source).read_snapshot())
    assert engine.url.database is not None
    index_path = Path(engine.url.database)
    register_synthetic_prepared_index(source, index_path)
    before = _snapshot_existing_database(index_path)
    statements: list[str] = []
    original = sqlite3.connect

    def trace_connect(*args, **kwargs):
        connection = original(*args, **kwargs)
        connection.set_trace_callback(statements.append)
        return connection

    monkeypatch.setattr(sqlite3, "connect", trace_connect)
    dbapi2 = getattr(sqlite3, "dbapi2", None)
    if dbapi2 is not None:
        monkeypatch.setattr(dbapi2, "connect", trace_connect)
    app = create_app(source, index_path)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api")
        assert response.status_code == 200 and response.json() == {"status": "ok"}
    assert _snapshot_existing_database(index_path) == before
    mutation = [
        statement
        for statement in statements
        if statement.lstrip().split()[0].upper()
        in {
            "CREATE",
            "DROP",
            "ALTER",
            "INSERT",
            "UPDATE",
            "DELETE",
            "REPLACE",
        }
    ]
    assert mutation == [], f"startup executed mutating SQL: {mutation}"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("condition", "setup_mode"),
    [
        ("missing_db", "missing_db"),
        ("unmanaged", "unmanaged"),
        ("old_revision", "old_revision"),
        ("missing_table", "missing_table"),
        ("unbuilt_empty", "unbuilt_empty"),
    ],
)
async def test_unprepared_index_is_rejected(
    condition: str,
    setup_mode: str,
    tmp_path: Path,
    migrated_index: tuple[Path, Engine],
) -> None:
    source, engine = migrated_index
    index_path = tmp_path / f"{condition}.sqlite3"

    expected_msg_parts: list[str] = []
    if setup_mode == "missing_db":
        assert not index_path.exists()
        expected_msg_parts = ["alembic upgrade head"]
    elif setup_mode == "unmanaged":
        with sqlite3.connect(index_path) as conn:
            conn.execute("CREATE TABLE legacy_sample (id INTEGER PRIMARY KEY)")
        expected_msg_parts = ["unmanaged", "alembic upgrade head"]
    elif setup_mode == "old_revision":
        with sqlite3.connect(index_path) as conn:
            conn.execute(
                "CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)"
            )
            conn.execute("INSERT INTO alembic_version VALUES ('0000_old_revision')")
        expected_msg_parts = ["revision", "alembic upgrade head"]
    elif setup_mode == "missing_table":
        _migrate_database(index_path, source)
        with sqlite3.connect(index_path) as conn:
            conn.execute("DROP TABLE registration_state")
        expected_msg_parts = ["missing required tables", "alembic upgrade head"]
    elif setup_mode == "unbuilt_empty":
        assert engine.url.database is not None
        index_path = Path(engine.url.database)
        expected_msg_parts = ["unbuilt", "build_search_index"]
    else:
        pytest.fail(f"Unknown setup_mode: {setup_mode}")

    before_exists = index_path.exists()
    before_snapshot = _snapshot_existing_database(index_path) if before_exists else None

    app = create_app(source, index_path)
    with pytest.raises(RuntimeError) as exc_info:
        async with app.router.lifespan_context(app):
            pass

    for part in expected_msg_parts:
        assert part in str(exc_info.value), (
            f"Expected {part!r} in error message: {exc_info.value}"
        )

    if before_exists:
        assert _snapshot_existing_database(index_path) == before_snapshot
    else:
        assert not index_path.exists()


@pytest.mark.asyncio
async def test_stale_index_requires_explicit_rebuild(
    migrated_index: tuple[Path, Engine],
) -> None:
    source, engine = migrated_index
    writer = SqlAlchemyIndexWriter(engine)
    writer.replace(FileIndexSourceReader(source).read_snapshot())
    assert engine.url.database is not None
    index_path = Path(engine.url.database)
    register_synthetic_prepared_index(source, index_path)
    before_snapshot = _snapshot_existing_database(index_path)

    # Modify source by adding a new structured document
    second_doc = source / "test_doc_002"
    second_doc.mkdir()
    (second_doc / "document.json").write_text(
        json.dumps(
            {
                "document": {
                    "company_identifier": "test2",
                    "package_insert_no": "002",
                    "generic_name": "テスト成分2",
                    "products": [
                        {"yj_code": "9876543A0000", "brand_name": "テスト薬2"}
                    ],
                },
                "source": {"pmda_url": "https://example.test/package-insert-2"},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (second_doc / "search_units.jsonl").write_text(
        json.dumps(
            {
                "unit_id": "test_002:000",
                "document_key": "test2_002",
                "section_code": "1",
                "kind": "heading",
                "query_text": "テスト薬2",
                "drug_name": "テスト薬2",
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    # Unregistered files do not change the published generation.
    unpublished_snapshot = read_registered_snapshot(index_path)
    assert unpublished_snapshot is not None
    assert len(unpublished_snapshot.documents) == 1
    with sqlite3.connect(index_path) as connection:
        files = json.loads(
            connection.execute(
                "SELECT files_json FROM registration_generations WHERE generation_id="
                "(SELECT generation_id FROM registration_state WHERE singleton=1)"
            ).fetchone()[0]
        )
    active_path = Path(files[0]["path"])
    original_bytes = active_path.read_bytes()
    active_path.write_bytes(original_bytes.replace("頭痛".encode(), "腹痛".encode()))
    # Published content corruption must be rejected without mutating DB.
    app = create_app(source, index_path)
    with pytest.raises(RuntimeError) as exc_info:
        async with app.router.lifespan_context(app):
            pass

    assert (
        "stale" in str(exc_info.value).lower()
        or "fingerprint" in str(exc_info.value).lower()
    )
    assert "build_search_index" in str(exc_info.value)
    assert _snapshot_existing_database(index_path) == before_snapshot

    # Restore the independently saved bytes, then rebuild only active inputs.
    active_path.write_bytes(original_bytes)
    snapshot = read_registered_snapshot(index_path)
    assert snapshot is not None
    build_result = writer.replace(snapshot)
    assert build_result.document_count == 1

    # Now startup succeeds
    restarted_app = create_app(source, index_path)
    async with restarted_app.router.lifespan_context(restarted_app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=restarted_app),
            base_url="http://test",
        ) as client:
            response = await client.get("/api")
        assert response.status_code == 200 and response.json() == {"status": "ok"}
