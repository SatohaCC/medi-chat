import hashlib
import os
import shutil
import sqlite3
import subprocess
import sys

import pytest
from backend.tests.infrastructure.persistence.test_alembic_migrations import (
    _migrate_database,
)
from backend.tests.integration.test_registration_publisher import source
from backend.tests.support.generation_os_server import main_server
from backend.tests.support.paths import PROJECT_ROOT

ROOT = PROJECT_ROOT


def hashes(root):
    return {
        str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in root.rglob("*")
        if path.is_file()
    }


def command(root, module, *args):
    environment = os.environ.copy()
    environment["PYTHON_DOTENV_DISABLED"] = "1"
    for name in (
        "OPENAI_API_KEY",
        "GEMINI_API_KEY",
        "GOOGLE_API_KEY",
        "ANTHROPIC_API_KEY",
        "TYPESAFE_API_KEY",
    ):
        environment[name] = ""
    return subprocess.run(
        [sys.executable, "-m", module, *map(str, args)],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=90,
    )


def test_tc111_real_seven_documents_initialize_from_current_sources(tmp_path):
    originals = tmp_path / "originals"
    structured = tmp_path / "structured"
    imports = tmp_path / "imports"
    shutil.copytree(ROOT / "data/pmda/originals", originals)
    from backend.infrastructure.pmda_xml.transform import transform
    from backend.tests.support.storage_fixtures import build_document_store

    structured.mkdir()
    for original in sorted(originals.rglob("*.xml")):
        transform(original, structured / original.stem)
    expected_units = sum(
        len((path / "search_units.jsonl").read_bytes().splitlines())
        for path in structured.iterdir()
    )
    index = tmp_path / "index.sqlite3"
    build_document_store(structured, index)
    before = hashes(originals), hashes(structured)
    _migrate_database(index, structured)
    from backend.infrastructure.composition.index_verifier import verify_index_readiness

    with pytest.raises(RuntimeError, match="initial_registration_required"):
        verify_index_readiness(structured, index)
    completed = command(
        tmp_path,
        "backend.infrastructure.cli.initialize_registrations",
        "--originals-dir",
        originals,
        "--structured-dir",
        structured,
        "--index-path",
        index,
        "--import-dir",
        imports,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    with sqlite3.connect(index) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM registration_receipts"
        ).fetchone() == (7,)
        assert connection.execute("SELECT COUNT(*) FROM units").fetchone() == (
            expected_units,
        )
        assert connection.execute("SELECT COUNT(*) FROM medicines").fetchone() == (15,)
        assert connection.execute(
            "SELECT COUNT(*) FROM active_registrations"
        ).fetchone() == (15,)
        assert connection.execute(
            "SELECT COUNT(*) FROM registration_generations"
        ).fetchone() == (1,)
        for _doc, sha in connection.execute(
            "SELECT document_id,source_sha256 FROM registration_receipts"
        ):
            assert sha in before[0].values()
    assert before == (hashes(originals), hashes(structured))

    with main_server(index, imports, structured) as (client, process, _):
        assert process.poll() is None
        health = client.get("/health").json()
        assert health["document_count"] == 7 and health["unit_count"] == expected_units
        assert len(client.get("/api/medicines/autocomplete").json()["items"]) == 15
        assert (
            client.get("/api/medicines").json()["generation_id"]
            == health["generation_id"]
        )
    assert before == (hashes(originals), hashes(structured))


def test_tc112_initial_conflict_is_rejected_before_files_or_database_change(tmp_path):
    originals = tmp_path / "originals"
    originals.mkdir()
    structured = tmp_path / "structured"
    structured.mkdir()
    index = tmp_path / "copy.sqlite3"
    _migrate_database(index, structured)
    for doc in ("O", "Q"):
        (originals / f"{doc}.xml").write_bytes(source("衝突", doc=doc))
    before = (
        hashlib.sha256(index.read_bytes()).hexdigest(),
        hashes(originals),
        hashes(structured),
    )
    completed = command(
        tmp_path,
        "backend.infrastructure.cli.initialize_registrations",
        "--originals-dir",
        originals,
        "--structured-dir",
        structured,
        "--index-path",
        index,
        "--import-dir",
        tmp_path / "imports",
    )
    assert completed.returncode != 0
    assert "same_revision_conflict" in completed.stderr
    assert (
        "111111111111" in completed.stderr
        and "000001_O:" in completed.stderr
        and "000001_Q:" in completed.stderr
    )
    assert before == (
        hashlib.sha256(index.read_bytes()).hexdigest(),
        hashes(originals),
        hashes(structured),
    )


def test_tc114_existing_build_cli_never_rescans_superseded_or_ignored_sources(tmp_path):
    from backend.infrastructure.persistence.attachment_import_store import (
        FileAttachmentImportStore,
    )
    from backend.infrastructure.persistence.registration_publisher import (
        SqliteRegistrationPublisher,
    )
    from backend.tests.integration.test_registration_publisher import publish

    structured = tmp_path / "structured"
    structured.mkdir()
    index = tmp_path / "copy.sqlite3"
    _migrate_database(index, structured)
    publisher = SqliteRegistrationPublisher(
        index, FileAttachmentImportStore(tmp_path / "imports")
    )
    publish(publisher, source("旧版"))
    current = publish(publisher, source("新版", revised_at="2026-11"))
    ignored = structured / "ignored"
    ignored.mkdir()
    (ignored / "document.json").write_bytes(b"not a valid input")
    before = hashes(structured)
    completed = command(
        tmp_path,
        "backend.infrastructure.cli.build_search_index",
        "--structured-dir",
        structured,
        "--index-path",
        index,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    with sqlite3.connect(index) as connection:
        assert connection.execute(
            "SELECT generation_id FROM registration_state"
        ).fetchone() == (current.generation_id,)
        assert connection.execute(
            "SELECT COUNT(*) FROM registration_receipts"
        ).fetchone() == (2,)
        assert connection.execute("SELECT COUNT(*) FROM units").fetchone() == (1,)
        assert (
            "新版" in connection.execute("SELECT payload_json FROM units").fetchone()[0]
        )
    assert before == hashes(structured)


def test_tc114_registration_conversion_cli_receipt_precedes_old_artifact_regeneration(
    tmp_path,
):
    from backend.infrastructure.persistence.attachment_import_store import (
        FileAttachmentImportStore,
    )
    from backend.infrastructure.persistence.registration_publisher import (
        SqliteRegistrationPublisher,
    )
    from backend.tests.integration.test_registration_publisher import publish

    structured = tmp_path / "structured"
    structured.mkdir()
    index = tmp_path / "copy.sqlite3"
    _migrate_database(index, structured)
    store = FileAttachmentImportStore(tmp_path / "imports")
    publisher = SqliteRegistrationPublisher(index, store)
    old = source("旧版")
    publish(publisher, old)
    current = publish(publisher, source("新版", revised_at="2026-11"))
    ignored = tmp_path / "ignored-old.xml"
    ignored.write_bytes(old)
    target = store._target(
        __import__(
            "backend.domain.attachment.identifiers", fromlist=["DocumentId"]
        ).DocumentId("000001_test"),
        hashlib.sha256(old).hexdigest(),
    )
    before = hashes(store.root)
    completed = command(
        tmp_path,
        "backend.infrastructure.cli.structure_pmda_xml",
        ignored,
        "--register",
        "--index-path",
        index,
        "--import-dir",
        store.root,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "superseded" in completed.stdout
    assert not (target / "source.xml").exists()
    assert before == hashes(store.root)
    with sqlite3.connect(index) as connection:
        assert connection.execute(
            "SELECT generation_id FROM registration_state"
        ).fetchone() == (current.generation_id,)
        assert connection.execute(
            "SELECT COUNT(*) FROM registration_receipts"
        ).fetchone() == (2,)


def test_tc114_pure_conversion_cannot_overwrite_managed_artifacts(tmp_path):
    from backend.infrastructure.persistence.attachment_import_store import (
        FileAttachmentImportStore,
    )
    from backend.infrastructure.persistence.registration_publisher import (
        SqliteRegistrationPublisher,
    )
    from backend.tests.integration.test_registration_publisher import (
        first_document_id,
        publish,
    )

    index = tmp_path / "copy.sqlite3"
    _migrate_database(index, tmp_path)
    store = FileAttachmentImportStore(tmp_path / "imports")
    publisher = SqliteRegistrationPublisher(index, store)
    result = publish(publisher, source("公開本文"))
    target = store._target(first_document_id(result), result.source_sha256)
    original = tmp_path / "offline.xml"
    original.write_bytes(source("上書きは禁止"))
    before = hashes(store.root)
    completed = command(
        tmp_path,
        "backend.infrastructure.cli.structure_pmda_xml",
        original,
        "--output-dir",
        target,
        "--index-path",
        index,
        "--import-dir",
        store.root,
    )
    assert completed.returncode != 0
    assert "managed" in completed.stderr
    assert before == hashes(store.root)
