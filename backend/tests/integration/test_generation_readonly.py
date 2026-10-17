import socket
import subprocess

import pytest
from backend.application.attachment_import.import_errors import ImportCancelled
from backend.config.database_settings import resolve_database_settings
from backend.infrastructure.cli.configured_e2e_gate import run_gate
from backend.infrastructure.pmda_xml.decoder import PmdaXmlDecoder
from backend.tests.integration.test_registration_publisher import publish, source
from backend.tests.integration.test_registration_publisher import publisher as publisher
from backend.tests.support.generation_os_server import main_server


def test_tc118_healthy_os_health_does_not_write_database_or_registered_files(publisher):
    publish(publisher, source("health不変本文"))
    structured = publisher.store.root.parent / "structured"
    structured.mkdir()
    with main_server(publisher.index_path, publisher.store.root, structured) as (
        client,
        process,
        _,
    ):
        assert process.poll() is None
        before = publisher.index_path.read_bytes()
        wal = publisher.index_path.with_name(publisher.index_path.name + "-wal")
        wal_before = wal.read_bytes() if wal.exists() else None
        files = {
            path: path.read_bytes()
            for path in publisher.store.root.rglob("*")
            if path.is_file() and ".locks" not in path.parts
        }
        for _ in range(3):
            assert client.get("/health").status_code == 200
        assert publisher.index_path.read_bytes() == before
        assert (wal.read_bytes() if wal.exists() else None) == wal_before
        assert {path: path.read_bytes() for path in files} == files


def test_tc118_configured_gate_rejects_cleanup_before_starting_main(
    publisher, monkeypatch
):
    publish(publisher, source("旧本文cleanup待ち"))
    cancelled = False

    def fault(phase):
        nonlocal cancelled
        if phase == "after_commit":
            cancelled = True

    def check():
        if cancelled:
            raise ImportCancelled()

    publisher.fault = fault
    value = source("新公開本文", revised_at="2026-11")
    result = publisher.publish(
        PmdaXmlDecoder().decode(value), value, check_cancel=check
    )
    assert result.status == "registered_cleanup_pending"
    structured = publisher.store.root.parent / "structured"
    structured.mkdir()
    before = publisher.index_path.read_bytes()
    files = {
        path: path.read_bytes()
        for path in publisher.store.root.rglob("*")
        if path.is_file()
    }

    def forbidden_spawn(*args, **kwargs):
        raise AssertionError("configured gate started main before recovery rejection")

    monkeypatch.setattr(subprocess, "Popen", forbidden_spawn)
    with pytest.raises(RuntimeError, match="explicit.*recovery"):
        run_gate(
            resolve_database_settings(
                index_path=publisher.index_path, structured_dir=structured
            )
        )
    assert publisher.index_path.read_bytes() == before
    assert {path: path.read_bytes() for path in files} == files


def test_tc118_configured_uv_smoke_preserves_healthy_prepared_copy(
    publisher, monkeypatch
):
    published = publish(publisher, source("configured health本文"))
    structured = publisher.store.root.parent / "structured"
    structured.mkdir()
    monkeypatch.setenv("MEDI_CHAT_IMPORT_DIR", str(publisher.store.root))
    before = publisher.index_path.read_bytes()
    files = {
        path: path.read_bytes()
        for path in publisher.store.root.rglob("*")
        if path.is_file()
    }
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]
    observed = run_gate(
        resolve_database_settings(
            index_path=publisher.index_path, structured_dir=structured
        ),
        port=port,
    )
    assert observed["os_health"] == {
        "status": "ok",
        "document_count": 1,
        "unit_count": 1,
        "generation_id": published.generation_id,
    }
    assert publisher.index_path.read_bytes() == before
    assert {path: path.read_bytes() for path in files} == files


def test_tc118_startup_race_refuses_recovery_without_changing_originals(
    publisher, monkeypatch
):
    publish(publisher, source("競合前本文"))
    structured = publisher.store.root.parent / "structured"
    structured.mkdir()
    monkeypatch.setenv("MEDI_CHAT_IMPORT_DIR", str(publisher.store.root))
    original_spawn = subprocess.Popen
    observed = {}

    def racing_spawn(*args, **kwargs):
        cancelled = False

        def fault(phase):
            nonlocal cancelled
            if phase == "after_commit":
                cancelled = True

        def check():
            if cancelled:
                raise ImportCancelled()

        publisher.fault = fault
        value = source("競合後公開本文", revised_at="2026-11")
        result = publisher.publish(
            PmdaXmlDecoder().decode(value), value, check_cancel=check
        )
        assert result.status == "registered_cleanup_pending"
        observed["database"] = publisher.index_path.read_bytes()
        observed["files"] = {
            path: path.read_bytes()
            for path in publisher.store.root.rglob("*")
            if path.is_file()
        }
        return original_spawn(*args, **kwargs)

    monkeypatch.setattr(subprocess, "Popen", racing_spawn)
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]
    with pytest.raises(RuntimeError, match="explicit.*recovery"):
        run_gate(
            resolve_database_settings(
                index_path=publisher.index_path, structured_dir=structured
            ),
            port=port,
        )
    assert publisher.index_path.read_bytes() == observed["database"]
    assert {path: path.read_bytes() for path in observed["files"]} == observed["files"]


def test_tc102_startup_retries_io_pending_without_changing_receipt(
    publisher, monkeypatch
):
    from pathlib import Path

    from backend.domain.attachment.identifiers import DocumentId

    first = publish(publisher, source("startup cleanup旧本文"))
    old_path = (
        publisher.store._target(DocumentId(first.document_id), first.source_sha256)
        / "source.xml"
    )
    original_unlink = Path.unlink

    def fail_one(path, *args, **kwargs):
        if path == old_path:
            raise PermissionError("controlled startup cleanup failure")
        return original_unlink(path, *args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(Path, "unlink", fail_one)
        final = publish(publisher, source("startup現在本文", revised_at="2026-11"))
        assert final.status == "registered_cleanup_pending"
    assert old_path.is_file()
    structured = publisher.store.root.parent / "structured"
    structured.mkdir()
    with main_server(publisher.index_path, publisher.store.root, structured) as (
        client,
        _,
        _,
    ):
        assert client.get("/health").json()["generation_id"] == final.generation_id
        assert not old_path.exists()
        result = publisher.read_result(final.document_id, final.source_sha256)
        assert result.status == "registered"
        assert result.registration_sequence == final.registration_sequence
        assert result.generation_id == final.generation_id
