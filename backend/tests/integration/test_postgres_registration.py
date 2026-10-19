"""Real PostgreSQL publication and byte preservation, not fake storage."""

import base64
import hashlib
import json
import os
import re
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace

import httpx
import pytest
import pytest_asyncio
from backend.application.attachment_import.import_document import (
    AttachmentImportService,
)
from backend.application.attachment_import.import_errors import (
    ImportCancelled,
    ImportConflict,
    ImportGone,
    ImportStorageError,
    InvalidAttachment,
)
from backend.domain.attachment.primitives import AttachmentSha256
from backend.domain.attachment.value_objects import AttachmentFigure
from backend.infrastructure.persistence import postgres_schema as s
from backend.infrastructure.persistence.attachment_document_mapping import (
    document_from_payload,
    document_to_payload,
)
from backend.infrastructure.persistence.postgres_registration import (
    FigureInput,
    PostgresRegistrationInput,
    PostgresRegistrationPublisher,
)
from backend.infrastructure.pmda_xml.artifact_mapping import PmdaArtifactEncoder
from backend.infrastructure.pmda_xml.decoder import PmdaXmlDecoder
from backend.presentation.attachment_import_routes import router
from backend.tests.infrastructure.persistence.test_attachment_document_mapping import (
    complete_document,
    observe,
)
from backend.tests.support.paths import PROJECT_ROOT
from backend.tests.support.postgres_fixtures import pg_engines as pg_engines
from backend.tests.support.registration_oracles import expected, source
from fastapi import FastAPI
from sqlalchemy import event, select, text
from sqlalchemy.exc import DBAPIError


def publish(publisher, raw, filename="テスト.xml"):
    return publisher.publish(
        PmdaXmlDecoder().decode(raw, original_filename=filename), raw
    )


@pytest.fixture
def pg_publisher(pg_engines):
    return PostgresRegistrationPublisher(pg_engines[1], encoder=PmdaArtifactEncoder())


@pytest_asyncio.fixture
async def pg_client(pg_publisher):
    service = AttachmentImportService(
        decoder=PmdaXmlDecoder(),
        publisher=pg_publisher,
    )
    app = FastAPI()
    app.include_router(router)
    app.state.attachment_import_service = service
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            yield client
    finally:
        await service.aclose()


def test_pg003_005_real_migration_and_runtime_permissions(pg_engines):
    owner, runtime, schema = pg_engines
    with runtime.connect() as connection:
        assert (
            connection.execute(
                text("SELECT current_setting('server_version_num')::int")
            ).scalar_one()
            >= 180000
        )
        assert connection.execute(select(s.state.c.sequence)).scalar_one() == 0
        assert not connection.execute(
            text(
                "SELECT has_schema_privilege(current_user, current_schema(), 'CREATE')"
            )
        ).scalar_one()
        assert not connection.execute(
            text(
                "SELECT rolsuper OR rolcreatedb OR rolcreaterole FROM pg_roles WHERE rolname=current_user"
            )
        ).scalar_one()
    assert schema.startswith("medi_chat_test_")
    with pytest.raises(DBAPIError), runtime.begin() as connection:
        connection.execute(text("CREATE TABLE runtime_ddl_must_fail (id integer)"))
    with runtime.connect() as connection:
        assert connection.execute(text("SHOW search_path")).scalar_one() == schema


@pytest.mark.parametrize("encoding", ["utf8_bom", "utf16", "shift_jis"])
def test_pg006_007_009_original_and_figures_export_in_new_process(
    pg_engines, pg_publisher, encoding
):
    original_text = source("テスト本文<!--保持-->\r\n").decode("utf-8")
    if encoding == "utf8_bom":
        raw = b"\xef\xbb\xbf" + original_text.encode("utf-8")
    elif encoding == "utf16":
        raw = ('<?xml version="1.0" encoding="UTF-16"?>' + original_text).encode(
            "utf-16"
        )
    else:
        raw = ('<?xml version="1.0" encoding="Shift_JIS"?>' + original_text).encode(
            "shift_jis"
        )
    decoded = PmdaXmlDecoder().decode(raw, original_filename="テスト原本.xml")
    figures = (FigureInput("fig.png", "image/png", b"\x89PNG\r\n\x00\xff"),)
    (result,) = pg_publisher.publish_inputs(
        (PostgresRegistrationInput(decoded, raw, figures),)
    )
    environment = {
        **os.environ,
        "PYTHONUTF8": "1",
        "PG_EXPORT_SCHEMA": pg_engines[2],
        "PG_EXPORT_VERSION": f"{result.document_id}:{result.source_sha256}",
    }
    script = """
import hashlib,json,os
from sqlalchemy import select
from backend.infrastructure.persistence.postgres_engine import create_postgres_engine
from backend.infrastructure.persistence import postgres_schema as s
from backend.infrastructure.persistence.attachment_document_mapping import document_from_payload
engine=create_postgres_engine(os.environ['TEST_RUNTIME_DATABASE_URL'],schema=os.environ['PG_EXPORT_SCHEMA'])
with engine.connect() as c:
 row=c.execute(select(s.versions).where(s.versions.c.version_id==os.environ['PG_EXPORT_VERSION'])).mappings().one()
 asset=c.execute(select(s.assets)).mappings().one()
 document=document_from_payload(row['structure'])
 print(json.dumps({'source':bytes(row['source']).hex(),'size':row['byte_size'],'filename':row['filename'],'sha256':hashlib.sha256(row['source']).hexdigest(),'figure':bytes(asset['content']).hex(),'figure_hash':asset['source_sha256'],'media_type':asset['media_type'],'logical_name':asset['logical_name'],'document_id':document.document_id.value}))
engine.dispose()
"""
    output = subprocess.run(
        [sys.executable, "-c", script],
        cwd=PROJECT_ROOT,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=20,
    )
    actual = json.loads(output.stdout)
    assert actual == {
        "source": raw.hex(),
        "size": len(raw),
        "filename": "テスト原本.xml",
        "sha256": hashlib.sha256(raw).hexdigest(),
        "figure": figures[0].content.hex(),
        "figure_hash": hashlib.sha256(figures[0].content).hexdigest(),
        "media_type": "image/png",
        "logical_name": "fig.png",
        "document_id": "000001_test",
    }


@pytest.mark.parametrize("deleted", [False, True])
def test_pg011_resend_does_not_reencode_or_revive_a_known_receipt(
    pg_engines, pg_publisher, monkeypatch, deleted
):
    raw = source("テスト既知登録")
    first = publish(pg_publisher, raw)
    if deleted:
        publish(pg_publisher, source("テスト更新済み", revised_at="2026-11"))
    before = (
        pg_publisher.read_result(first.document_id, first.source_sha256)
        if not deleted
        else None
    )

    def refuse(*args, **kwargs):
        raise AssertionError("Known receipt must reuse original conversion result")

    monkeypatch.setattr(pg_publisher.encoder, "encode", refuse)
    repeated = publish(pg_publisher, raw, filename="テスト別名.xml")
    assert repeated.reused
    assert repeated.registration_sequence == first.registration_sequence
    assert repeated.transformer_version == first.transformer_version
    assert repeated.artifacts_deleted is deleted
    if before is not None:
        assert repeated.generation_id == before.generation_id
    with pg_engines[0].connect() as connection:
        retained = connection.execute(
            select(s.versions.c.version_id).where(
                s.versions.c.version_id == f"{first.document_id}:{first.source_sha256}"
            )
        ).first()
        assert (retained is None) is deleted


def test_pg011_receipt_reuse_and_real_input_hash(pg_engines, pg_publisher):
    raw = source("テスト初回")
    first = publish(pg_publisher, raw)
    reused = publish(pg_publisher, raw)
    assert first.source_sha256 == hashlib.sha256(raw).hexdigest()
    assert not first.reused and reused.reused
    assert first.registration_sequence == reused.registration_sequence == 1
    assert first.generation_id == reused.generation_id
    assert first.active_yj_codes == ("111111111111",)
    assert (
        pg_publisher.read_result(
            first.document_id, first.source_sha256
        ).registration_sequence
        == 1
    )
    with pg_engines[1].connect() as connection:
        assert len(connection.execute(select(s.receipts)).all()) == 1


@pytest.mark.parametrize("order", ["old_new", "new_old"])
def test_pg012_revision_priority_and_no_regression(pg_publisher, order):
    old = source("テスト旧版", revised_at="2026-10")
    new = source("テスト新版", revised_at="2026-11")
    values = (old, new) if order == "old_new" else (new, old)
    results = [publish(pg_publisher, value) for value in values]
    newest = next(
        result
        for result in results
        if result.source_sha256 == hashlib.sha256(new).hexdigest()
    )
    assert pg_publisher.read_result(
        newest.document_id, newest.source_sha256
    ).active_yj_codes == ("111111111111",)
    with pg_publisher.engine.connect() as connection:
        assert (
            connection.execute(select(s.active.c.version_id)).scalar_one()
            == f"{newest.document_id}:{newest.source_sha256}"
        )
    assert [result.registration_sequence for result in results] == [1, 2]


def test_pg013_same_month_conflict_does_not_change_publication(pg_publisher):
    first = publish(pg_publisher, source("テスト同月A"))
    with pytest.raises(ImportConflict) as failure:
        publish(pg_publisher, source("テスト同月B"))
    assert failure.value.code == "same_revision_conflict"
    assert failure.value.conflicts[0][0] == "111111111111"
    with pg_publisher.engine.connect() as connection:
        assert (
            connection.execute(select(s.state.c.generation_id)).scalar_one()
            == first.generation_id
        )
        assert len(connection.execute(select(s.receipts)).all()) == 1


def test_pg014_missing_revision_refused(pg_publisher):
    raw = re.sub(
        b"<DateOfPreparationOrRevision>.*?</DateOfPreparationOrRevision>",
        b"",
        source("テスト年月なし"),
    )
    with pytest.raises(InvalidAttachment) as failure:
        publish(pg_publisher, raw)
    assert failure.value.code == "missing_revision"
    with pg_publisher.engine.connect() as connection:
        assert len(connection.execute(select(s.receipts)).all()) == 0


def test_pg015_partial_old_yj_remains_active(pg_publisher):
    old = publish(
        pg_publisher, source("テスト旧共通", ("111111111111", "222222222222"))
    )
    new = publish(pg_publisher, source("テストA新版", revised_at="2026-11"))
    assert pg_publisher.read_result(
        old.document_id, old.source_sha256
    ).active_yj_codes == ("222222222222",)
    assert new.active_yj_codes == ("111111111111",)
    assert new.replaced_yj_codes == ("111111111111",)
    with pg_publisher.engine.connect() as connection:
        assert len(connection.execute(select(s.versions)).all()) == 2
        assert set(
            connection.execute(
                select(s.memberships.c.yj_code).where(
                    s.memberships.c.generation_id == new.generation_id
                )
            ).scalars()
        ) == {"111111111111", "222222222222"}
    publish(
        pg_publisher, source("テストB新版", ("222222222222",), revised_at="2026-11")
    )
    with pg_publisher.engine.connect() as connection:
        assert len(connection.execute(select(s.versions)).all()) == 2
        assert connection.execute(
            select(s.receipts.c.artifacts_deleted).where(
                s.receipts.c.version_id == f"{old.document_id}:{old.source_sha256}"
            )
        ).scalar_one()


@pytest.mark.parametrize(
    "phase",
    ["receipt", "source", "assets", "units", "active", "generation", "before_commit"],
)
def test_pg017_each_write_failure_rolls_back_every_table(
    pg_engines, pg_publisher, phase
):
    old = publish(pg_publisher, source("テスト旧公開"))
    tables = (
        s.receipts,
        s.versions,
        s.assets,
        s.units,
        s.active,
        s.generations,
        s.memberships,
    )
    with pg_engines[0].connect() as connection:
        before = {
            table.name: connection.execute(select(table)).all() for table in tables
        }

    def fault(actual):
        if actual == phase:
            raise OSError("test write failure")

    publisher = PostgresRegistrationPublisher(
        pg_engines[1], encoder=PmdaArtifactEncoder(), fault=fault
    )
    raw = source("テストrollback", revised_at="2026-11")
    with pytest.raises(ImportStorageError):
        publisher.publish_inputs(
            (
                PostgresRegistrationInput(
                    PmdaXmlDecoder().decode(raw),
                    raw,
                    (FigureInput("test.gif", "image/gif", b"GIF89a\x00"),),
                ),
            )
        )
    with pg_engines[0].connect() as connection:
        assert connection.execute(select(s.state.c.sequence)).scalar_one() == 1
        assert (
            connection.execute(select(s.state.c.generation_id)).scalar_one()
            == old.generation_id
        )
        for table in tables:
            assert connection.execute(select(table)).all() == before[table.name], (
                table.name
            )


def test_pg018_response_loss_after_commit_reuses_durable_receipt(pg_engines):
    def fault(phase):
        if phase == "after_commit":
            raise OSError("test lost response")

    publisher = PostgresRegistrationPublisher(
        pg_engines[1], encoder=PmdaArtifactEncoder(), fault=fault
    )
    raw = source("テストcommit済み")
    with pytest.raises(ImportStorageError):
        publish(publisher, raw)
    publisher.fault = lambda phase: None
    result = publish(publisher, raw)
    assert result.reused and result.registration_sequence == 1
    with pg_engines[1].connect() as connection:
        assert len(connection.execute(select(s.receipts)).all()) == 1
        assert len(connection.execute(select(s.generations)).all()) == 1


def test_pg016_same_source_concurrent_publish_has_one_receipt(pg_engines):
    barrier = threading.Barrier(2)

    def fault(phase):
        if phase == "prepared":
            barrier.wait(timeout=10)

    publisher = PostgresRegistrationPublisher(
        pg_engines[1], encoder=PmdaArtifactEncoder(), fault=fault
    )
    raw = source("テスト同時再送")
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: publish(publisher, raw), range(2)))
    assert sorted(result.reused for result in results) == [False, True]
    assert {result.registration_sequence for result in results} == {1}
    assert len({result.generation_id for result in results}) == 1


@pytest.mark.parametrize(
    ("cancel_phase", "expected_count"), [("before_commit", 0), ("after_commit", 1)]
)
def test_pg021_cancel_before_commit_rolls_back_and_after_commit_keeps_receipt(
    pg_engines, cancel_phase, expected_count
):
    cancelled = False

    def fault(phase):
        nonlocal cancelled
        cancelled = phase == cancel_phase

    def check_cancel():
        if cancelled:
            raise ImportCancelled()

    publisher = PostgresRegistrationPublisher(
        pg_engines[1], encoder=PmdaArtifactEncoder(), fault=fault
    )
    raw = source("テスト取消" + cancel_phase)
    decoded = PmdaXmlDecoder().decode(raw)
    if cancel_phase == "before_commit":
        with pytest.raises(ImportCancelled):
            publisher.publish(decoded, raw, check_cancel=check_cancel)
    else:
        assert (
            publisher.publish(
                decoded, raw, check_cancel=check_cancel
            ).registration_sequence
            == 1
        )
    with pg_engines[1].connect() as connection:
        assert len(connection.execute(select(s.receipts)).all()) == expected_count


def test_pg020_022_cleanup_deletes_payload_and_replay_never_revives(
    pg_engines, pg_publisher
):
    old_raw = source("テスト削除原文")
    old = publish(pg_publisher, old_raw)
    new = publish(pg_publisher, source("テスト置換", revised_at="2026-11"))
    old_id = f"{old.document_id}:{old.source_sha256}"
    assert new.deleted_version_ids == (old_id,)
    with pytest.raises(ImportGone) as failure:
        pg_publisher.read_result(old.document_id, old.source_sha256)
    assert (
        failure.value.code == "version_deleted" and failure.value.phase == "publication"
    )
    replay = publish(pg_publisher, old_raw)
    assert replay.reused and replay.artifacts_deleted and not replay.active_yj_codes
    assert (
        replay.registration_sequence == 1 and replay.generation_id == new.generation_id
    )
    with pg_engines[1].connect() as connection:
        assert connection.execute(select(s.versions.c.version_id)).scalars().all() == [
            f"{new.document_id}:{new.source_sha256}"
        ]
        assert not connection.execute(
            select(s.units).where(s.units.c.version_id == old_id)
        ).first()
        receipt = (
            connection.execute(
                select(s.receipts).where(s.receipts.c.version_id == old_id)
            )
            .mappings()
            .one()
        )
        assert "テスト削除原文" not in repr(dict(receipt))
        assert len(connection.execute(select(s.generations)).all()) == 1


@pytest.mark.parametrize("phase", ["cleanup", "cleanup_before_commit"])
def test_pg021_cleanup_failure_is_pending_and_retries_atomically(
    pg_engines, pg_publisher, phase
):
    old = publish(pg_publisher, source("テスト保留旧版"))
    old_id = f"{old.document_id}:{old.source_sha256}"

    def fault(actual):
        if actual == phase:
            raise OSError("test cleanup failure")

    pg_publisher.fault = fault
    new = publish(pg_publisher, source("テスト保留新版", revised_at="2026-11"))
    assert new.status == "registered_cleanup_pending"
    assert new.cleanup_pending == ((old_id, "database_cleanup_failed"),)
    with pg_engines[1].connect() as connection:
        assert connection.execute(
            select(s.versions).where(s.versions.c.version_id == old_id)
        ).first()
        assert not connection.execute(
            select(s.receipts.c.artifacts_deleted).where(
                s.receipts.c.version_id == old_id
            )
        ).scalar_one()
    pg_publisher.fault = lambda phase: None
    pg_publisher.cleanup()
    result = pg_publisher.read_result(new.document_id, new.source_sha256)
    assert result.deleted_version_ids == (old_id,) and result.cleanup_pending == ()


def test_pg052_transform_does_not_hold_publication_lock(pg_engines, pg_publisher):
    entered = threading.Event()
    release = threading.Event()

    class PausedEncoder:
        def encode(self, document, search_units, source_info):
            entered.set()
            assert release.wait(10)
            return PmdaArtifactEncoder().encode(document, search_units, source_info)

    paused = PostgresRegistrationPublisher(pg_engines[1], encoder=PausedEncoder())
    with ThreadPoolExecutor(max_workers=2) as executor:
        pending = executor.submit(
            publish, paused, source("テスト変換待機", ("222222222222",), doc="paused")
        )
        assert entered.wait(10)
        try:
            independent = executor.submit(
                publish, pg_publisher, source("テスト独立writer")
            )
            assert independent.result(timeout=5).registration_sequence == 1
        finally:
            release.set()
        assert pending.result(timeout=10).registration_sequence == 2


@pytest.mark.parametrize("committed", [False, True])
def test_pg019_actual_commit_connection_loss_converges_on_retry(
    pg_engines, pg_publisher, committed
):
    old = publish(pg_publisher, source("テスト切断前"))
    raw = source("テスト切断新版", revised_at="2026-11")
    armed = True

    def cut_commit(connection):
        nonlocal armed
        if not armed:
            return
        armed = False
        driver = connection.connection.driver_connection
        if committed:
            driver.commit()
        driver.close()

    event.listen(pg_engines[1], "commit", cut_commit)
    try:
        with pytest.raises(ImportStorageError):
            publish(pg_publisher, raw)
    finally:
        event.remove(pg_engines[1], "commit", cut_commit)
    with pg_engines[0].connect() as connection:
        pointer = connection.execute(select(s.state.c.generation_id)).scalar_one()
        assert (pointer != old.generation_id) is committed
        assert len(connection.execute(select(s.receipts)).all()) == (
            2 if committed else 1
        )
    result = publish(pg_publisher, raw)
    assert result.reused is committed
    assert result.registration_sequence == 2
    assert result.active_yj_codes == ("111111111111",)


def test_pg017_existing_publication_is_unchanged_on_failed_replacement(
    pg_engines, pg_publisher
):
    old = publish(pg_publisher, source("テスト旧公開"))

    def fault(phase):
        if phase == "before_commit":
            raise OSError("test replacement rollback")

    pg_publisher.fault = fault
    with pytest.raises(ImportStorageError):
        publish(pg_publisher, source("テスト失敗新版", revised_at="2026-11"))
    with pg_engines[0].connect() as connection:
        assert (
            connection.execute(select(s.state.c.generation_id)).scalar_one()
            == old.generation_id
        )
        assert (
            connection.execute(select(s.active.c.version_id)).scalar_one()
            == f"{old.document_id}:{old.source_sha256}"
        )
        assert len(connection.execute(select(s.receipts)).all()) == 1


def test_pg052_cleanup_rechecks_pointer_after_competing_writer(
    pg_engines, pg_publisher
):
    entered = threading.Event()
    release = threading.Event()
    publish(pg_publisher, source("テストGC旧版"))

    def pause(phase):
        if phase == "before_cleanup_lock":
            entered.set()
            assert release.wait(10)

    cleaner = PostgresRegistrationPublisher(
        pg_engines[1], encoder=PmdaArtifactEncoder(), fault=pause
    )
    with ThreadPoolExecutor(max_workers=2) as executor:
        pending = executor.submit(cleaner.cleanup)
        assert entered.wait(10)
        try:
            current = publish(
                pg_publisher, source("テストGC新公開", revised_at="2026-11")
            )
        finally:
            release.set()
        pending.result(timeout=10)
    with pg_engines[0].connect() as connection:
        current_id = f"{current.document_id}:{current.source_sha256}"
        assert connection.execute(select(s.versions.c.version_id)).scalars().all() == [
            current_id
        ]
        assert connection.execute(
            select(s.memberships.c.version_id)
        ).scalars().all() == [current_id]


def test_pg007_same_logical_figure_names_are_owned_by_version(pg_engines, pg_publisher):
    first_raw = source("テスト図版A", ("111111111111", "222222222222"))
    second_raw = source("テスト図版B", revised_at="2026-11")
    (first,) = pg_publisher.publish_inputs(
        (
            PostgresRegistrationInput(
                PmdaXmlDecoder().decode(first_raw),
                first_raw,
                (FigureInput("same.gif", "image/gif", b"GIF-first\x00"),),
            ),
        )
    )
    (second,) = pg_publisher.publish_inputs(
        (
            PostgresRegistrationInput(
                PmdaXmlDecoder().decode(second_raw),
                second_raw,
                (FigureInput("same.gif", "image/gif", b"GIF-second\xff"),),
            ),
        )
    )
    with pg_engines[1].connect() as connection:
        assets = {
            row.version_id: bytes(row.content)
            for row in connection.execute(select(s.assets))
        }
    assert assets == {
        f"{first.document_id}:{first.source_sha256}": b"GIF-first\x00",
        f"{second.document_id}:{second.source_sha256}": b"GIF-second\xff",
    }


def test_pg006_007_cli_initialization_and_export_preserve_bytes(pg_engines, tmp_path):
    from backend.tests.infrastructure.persistence.test_postgres_initialization import (
        graphic,
    )

    directory = tmp_path / "originals"
    directory.mkdir()
    raw = b"\xef\xbb\xbf" + graphic("test.gif") + "\r\n<!--テスト原本-->".encode()
    (directory / "テスト.xml").write_bytes(raw)
    (directory / "test.gif").write_bytes(b"GIF89a\x00\xff")
    command = [
        sys.executable,
        "-m",
        "backend.infrastructure.cli.manage_postgres",
        "--database-env",
        "TEST_RUNTIME_DATABASE_URL",
        "--schema",
        pg_engines[2],
    ]
    environment = {**os.environ, "PYTHONUTF8": "1"}
    result = subprocess.run(
        [*command, "initialize", "--originals-dir", str(directory)],
        cwd=PROJECT_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=20,
    )
    assert result.returncode == 0, result.stderr
    summary = json.loads(result.stdout)
    assert summary["registered"] == 1
    version_id = "000001_test:" + hashlib.sha256(raw).hexdigest()
    output = tmp_path / "export"
    exported = subprocess.run(
        [*command, "export", "--version-id", version_id, "--output-dir", str(output)],
        cwd=PROJECT_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=20,
    )
    assert exported.returncode == 0, exported.stderr
    assert (output / "source.xml").read_bytes() == raw
    assert (output / "figures" / "test.gif").read_bytes() == b"GIF89a\x00\xff"
    refused = subprocess.run(
        [*command, "initialize", "--originals-dir", str(directory)],
        cwd=PROJECT_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=20,
    )
    assert refused.returncode != 0


def test_pg006_007_full_original_set_and_all_figure_references(
    pg_engines, pg_publisher
):
    import xml.etree.ElementTree as ET

    from backend.infrastructure.cli.manage_postgres import load_inputs
    from backend.tests.support.paths import PROJECT_ROOT

    original_root = PROJECT_ROOT / "data/pmda/originals"
    expected_sources = {}
    expected_assets = {}
    for path in sorted(original_root.rglob("*.xml")):
        raw = path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        expected_sources[digest] = (raw, path.name)
        for element in ET.fromstring(raw).iter():
            name = element.attrib.get("gfname")
            if name:
                expected_assets[digest, name] = (path.parent / name).read_bytes()
    assert len(expected_sources) == 7 and len(expected_assets) == 60
    results = pg_publisher.publish_inputs(load_inputs(original_root), initial=True)
    assert len(results) == 7
    with pg_engines[0].connect() as connection:
        originals = list(
            connection.execute(
                select(s.versions, s.receipts.c.source_sha256).join(
                    s.receipts, s.receipts.c.version_id == s.versions.c.version_id
                )
            ).mappings()
        )
        assets = list(
            connection.execute(
                select(
                    s.assets, s.receipts.c.source_sha256.label("original_sha256")
                ).join(s.receipts, s.receipts.c.version_id == s.assets.c.version_id)
            ).mappings()
        )
    assert {
        row["source_sha256"]: (bytes(row["source"]), row["filename"])
        for row in originals
    } == expected_sources
    assert {
        (row["original_sha256"], row["logical_name"]): bytes(row["content"])
        for row in assets
    } == expected_assets
    assert all(
        row["source_sha256"] == hashlib.sha256(row["content"]).hexdigest()
        for row in assets
    )


@pytest.mark.asyncio
async def test_pg011_022_http_dtos_match_independent_existing_oracle(
    pg_client, pg_publisher
):
    raw = source("テストHTTP旧版")
    digest = hashlib.sha256(raw).hexdigest()
    response = await pg_client.post(
        "/api/attachment-imports",
        files={"file": ("テスト.xml", raw, "application/xml")},
    )
    assert response.status_code == 201
    generation = response.json()["generation_id"]
    assert response.json() == expected(raw, generation, 1, ("111111111111",))
    location = response.headers["location"]
    assert location == f"/api/attachment-imports/000001_test/{digest}"
    get = await pg_client.get(location)
    assert get.status_code == 200 and get.json() == response.json()
    repeat = await pg_client.post(
        "/api/attachment-imports",
        files={"file": ("テスト.xml", raw, "application/xml")},
    )
    assert repeat.status_code == 200
    assert repeat.json() == expected(raw, generation, 1, ("111111111111",), reused=True)
    new_raw = source("テストHTTP新版", revised_at="2026-11")
    new = await pg_client.post(
        "/api/attachment-imports",
        files={"file": ("テスト.xml", new_raw, "application/xml")},
    )
    assert new.status_code == 201
    assert new.json() == expected(
        new_raw,
        new.json()["generation_id"],
        2,
        ("111111111111",),
        replaced=("111111111111",),
        deleted=(f"000001_test:{digest}",),
        revised_at="2026-11",
    )
    gone = await pg_client.get(location)
    assert gone.status_code == 410 and gone.json()["detail"] == {
        "code": "version_deleted",
        "message": "Registered version artifacts have been deleted",
        "phase": "publication",
    }
    replay = await pg_client.post(
        "/api/attachment-imports",
        files={"file": ("テスト.xml", raw, "application/xml")},
    )
    assert replay.status_code == 200
    assert replay.json() == expected(
        raw,
        new.json()["generation_id"],
        1,
        ("111111111111",),
        active=(),
        status="superseded",
        reused=True,
        artifacts_deleted=True,
    )


@pytest.mark.asyncio
async def test_pg008_web_missing_figure_warns_without_storing_fake_asset(
    pg_client, pg_engines
):
    from backend.tests.infrastructure.persistence.test_postgres_initialization import (
        graphic,
    )

    raw = graphic("missing.gif")
    response = await pg_client.post(
        "/api/attachment-imports",
        files={"file": ("テスト.xml", raw, "application/xml")},
    )
    assert response.status_code == 201
    assert response.json()["warnings"] == [
        {"code": "missing_figure", "reference": "missing.gif"}
    ]
    with pg_engines[0].connect() as connection:
        assert not connection.execute(select(s.assets)).first()
        document = document_from_payload(
            connection.execute(select(s.versions.c.structure)).scalar_one()
        )
    body = document.sections[0].body
    assert body is not None
    figure = body.blocks[0]
    assert isinstance(figure, AttachmentFigure)
    assert figure.reference.value == "missing.gif"


@pytest.mark.parametrize(
    "kind", ["same_hash", "different_month", "same_month", "different_yj"]
)
def test_pg016_independent_process_writers_converge_without_lost_updates(
    pg_engines, kind
):
    first = source("テスト並行A")
    second = (
        first
        if kind == "same_hash"
        else source(
            "テスト並行B",
            ("222222222222",) if kind == "different_yj" else ("111111111111",),
            revised_at="2026-11" if kind == "different_month" else "2026-10",
        )
    )
    processes = []
    try:
        for raw in (first, second):
            environment = {
                **os.environ,
                "PYTHONUTF8": "1",
                "PG_WORKER_SCHEMA": pg_engines[2],
                "PG_WORKER_SOURCE": base64.b64encode(raw).decode("ascii"),
            }
            processes.append(
                subprocess.Popen(
                    [
                        sys.executable,
                        "-m",
                        "backend.tests.support.postgres_registration_worker",
                    ],
                    cwd=PROJECT_ROOT,
                    env=environment,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding="utf-8",
                )
            )
        for process in processes:
            assert process.stdout.readline().strip() == "prepared"
        for process in processes:
            process.stdin.write("go\n")
            process.stdin.flush()
        results = []
        for process in processes:
            output, error = process.communicate(timeout=20)
            assert process.returncode == 0, error
            results.append(json.loads(output))
        assert set(results[0]["pids"]).isdisjoint(results[1]["pids"])
        with pg_engines[0].connect() as connection:
            receipts = connection.execute(select(s.receipts)).all()
            assigned = dict(
                connection.execute(
                    select(s.active.c.yj_code, s.active.c.version_id)
                ).all()
            )
        if kind == "same_hash":
            assert len(receipts) == 1 and sorted(
                result["reused"] for result in results
            ) == [False, True]
            assert {result["sequence"] for result in results} == {1}
        elif kind == "same_month":
            assert len(receipts) == 1 and sorted(
                result["status"] for result in results
            ) == ["conflict", "ok"]
            assert (
                next(result for result in results if result["status"] == "conflict")[
                    "code"
                ]
                == "same_revision_conflict"
            )
        elif kind == "different_month":
            assert len(receipts) == 2
            assert assigned["111111111111"].endswith(hashlib.sha256(second).hexdigest())
        else:
            assert len(receipts) == 2 and set(assigned) == {
                "111111111111",
                "222222222222",
            }
    finally:
        for process in processes:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=5)


def test_pg009_handwritten_complete_domain_restored_from_jsonb_in_new_process(
    pg_engines,
):
    original = complete_document()
    raw = source("テスト完全構造")
    sha256 = hashlib.sha256(raw).hexdigest()
    original = replace(
        original, source=replace(original.source, sha256=AttachmentSha256(sha256))
    )
    identity = f"{original.document_id.value}:{sha256}"
    with pg_engines[1].begin() as connection:
        connection.execute(
            s.receipts.insert(),
            {
                "version_id": identity,
                "document_id": original.document_id.value,
                "source_sha256": sha256,
                "sequence": 1,
                "revised_at": "2026-10",
                "yj_codes": ["1234567A0000"],
                "replaced": [],
                "cleanup_targets": [],
                "result": {},
                "artifacts_deleted": False,
                "cleanup_reason": "",
            },
        )
        connection.execute(
            s.versions.insert(),
            {
                "version_id": identity,
                "structure": document_to_payload(original),
                "catalogue": {},
                "payload_fingerprint": "mapper-test-only",
                "projection_fingerprint": "mapper-test-only",
                "source": raw,
                "filename": "テスト.xml",
                "byte_size": len(raw),
                "validation": {},
            },
        )
    script = """
import os,json
from sqlalchemy import select
from backend.infrastructure.persistence.postgres_engine import create_postgres_engine
from backend.infrastructure.persistence import postgres_schema as s
from backend.infrastructure.persistence.attachment_document_mapping import document_from_payload
from backend.tests.infrastructure.persistence.test_attachment_document_mapping import observe
engine=create_postgres_engine(os.environ['TEST_RUNTIME_DATABASE_URL'],schema=os.environ['PG_EXPORT_SCHEMA'])
with engine.connect() as connection:
 document=document_from_payload(connection.execute(select(s.versions.c.structure)).scalar_one())
 print(json.dumps(observe(document),ensure_ascii=False))
engine.dispose()
"""
    environment = {**os.environ, "PYTHONUTF8": "1", "PG_EXPORT_SCHEMA": pg_engines[2]}
    process = subprocess.run(
        [sys.executable, "-c", script],
        cwd=PROJECT_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=20,
    )
    assert process.returncode == 0, process.stderr
    assert json.loads(process.stdout) == json.loads(json.dumps(observe(original)))


@pytest.mark.asyncio
@pytest.mark.parametrize("existing_code", ["111111111111", "222222222222"])
async def test_pg013_014_http_partial_conflict_and_missing_month_are_atomic(
    pg_client, pg_engines, existing_code
):
    original = source("テスト既存", (existing_code,))
    assert (
        await pg_client.post(
            "/api/attachment-imports",
            files={"file": ("テスト.xml", original, "application/xml")},
        )
    ).status_code == 201
    incoming = source("テスト一部競合", ("111111111111", "222222222222"))
    conflict = await pg_client.post(
        "/api/attachment-imports",
        files={"file": ("テスト.xml", incoming, "application/xml")},
    )
    assert conflict.status_code == 409
    assert conflict.json()["detail"]["code"] == "same_revision_conflict"
    assert conflict.json()["detail"]["conflicts"][0]["yj_code"] == existing_code
    missing = re.sub(
        b"<DateOfPreparationOrRevision>.*?</DateOfPreparationOrRevision>",
        b"",
        source("テスト改訂なし"),
    )
    rejected = await pg_client.post(
        "/api/attachment-imports",
        files={"file": ("テスト.xml", missing, "application/xml")},
    )
    assert rejected.status_code == 422
    assert rejected.json()["detail"]["code"] == "missing_revision"
    assert rejected.json()["detail"]["phase"] == "validation"
    with pg_engines[0].connect() as connection:
        assert connection.execute(select(s.active.c.yj_code)).scalars().all() == [
            existing_code
        ]
        assert len(connection.execute(select(s.receipts)).all()) == 1


def test_pg021_real_database_error_rolls_back_cleanup_and_two_maintenance_runs_converge(
    pg_engines, pg_publisher
):
    old = publish(pg_publisher, source("テストDB清掃旧版"))
    old_id = f"{old.document_id}:{old.source_sha256}"
    armed = True

    def fail_delete(connection, cursor, statement, parameters, context, executemany):
        nonlocal armed
        if armed and statement.startswith("DELETE FROM attachment_versions"):
            armed = False
            cursor.execute("SELECT 1/0")

    event.listen(pg_engines[1], "before_cursor_execute", fail_delete)
    try:
        new = publish(pg_publisher, source("テストDB清掃新版", revised_at="2026-11"))
        assert new.cleanup_pending == ((old_id, "database_cleanup_failed"),)
        with pg_engines[0].connect() as connection:
            assert connection.execute(
                select(s.versions).where(s.versions.c.version_id == old_id)
            ).first()
            assert not connection.execute(
                select(s.receipts.c.artifacts_deleted).where(
                    s.receipts.c.version_id == old_id
                )
            ).scalar_one()
        pg_publisher.cleanup()
        pg_publisher.cleanup()
        assert pg_publisher.read_result(
            new.document_id, new.source_sha256
        ).deleted_version_ids == (old_id,)
    finally:
        event.remove(pg_engines[1], "before_cursor_execute", fail_delete)
