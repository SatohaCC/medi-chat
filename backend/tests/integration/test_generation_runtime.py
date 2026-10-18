"""Independent generation/YJ/lease runtime oracles, using real copy SQLite."""

import asyncio
import hashlib
import os
import sqlite3
import subprocess
import sys
import threading
import time

import pytest
from backend.application.medicine.product_models import ResolvedMedicine
from backend.domain.medicine.value_objects import MedicineMatch as DomainMedicineMatch
from backend.domain.retrieval.primitives import DetectionSource, SearchSectionCode
from backend.domain.retrieval.value_objects import SearchCriteria
from backend.infrastructure.persistence.evidence_reader import SqlAlchemyEvidenceReader
from backend.infrastructure.persistence.generation_runtime import GenerationRuntime
from backend.infrastructure.persistence.read_workers import ReadWorkers
from backend.infrastructure.persistence.readonly_engine import create_readonly_engine
from backend.tests.application.indexing.test_active_attachment_projection import (
    mixed_source,
)
from backend.tests.integration.test_registration_publisher import publish, source
from backend.tests.integration.test_registration_publisher import publisher as publisher
from backend.tests.support.paths import PROJECT_ROOT


def test_tc094_doc_id_only_does_not_leak_old_b_into_requested_new_a(publisher):
    old = source("旧B原文", ("111111111111", "222222222222"))
    publish(publisher, old)
    new = source("新A原文", revised_at="2026-11")
    publish(publisher, new)
    engine = create_readonly_engine(publisher.index_path)
    try:
        target = ResolvedMedicine(
            medicine=DomainMedicineMatch("", (), ("111111111111",), ()),
            document_ids=("000001_test",),
        )
        rows = SqlAlchemyEvidenceReader(engine)._search(
            SearchCriteria(
                source=DetectionSource.LOGIC, section_codes=(SearchSectionCode("1"),)
            ),
            (target,),
        )
        assert [row.unit_id.value for row in rows] == [
            f"000001_test:{hashlib.sha256(new).hexdigest()}:1"
        ]
        assert "旧B原文" not in "".join(row.excerpt for row in rows)
    finally:
        engine.dispose()


@pytest.mark.asyncio
async def test_tc095_096_104_live_lease_pins_old_products_and_body_until_exit(
    publisher,
):
    old = source("旧共通本文", ("111111111111", "222222222222"))
    first = publish(publisher, old)
    old_path = (
        publisher.store._target(first_document_id(first), first.source_sha256)
        / "source.xml"
    )
    workers = ReadWorkers()
    runtime = GenerationRuntime(publisher, workers=workers)
    try:
        async with runtime.acquire() as snap:
            assert snap.generation_id.value == first.generation_id
            publish(publisher, source("新A原文", revised_at="2026-11"))
            final = publish(
                publisher, source("新B原文", ("222222222222",), revised_at="2026-11")
            )
            assert old_path.read_bytes() == old
            assert final.status == "registered_cleanup_pending"
            assert final.cleanup_pending == (
                (f"000001_test:{hashlib.sha256(old).hexdigest()}", "lease_active"),
            )
            medicines = await snap.medicine_reader.read_medicines()
            assert {item.yj_code.value for item in medicines if item.yj_code} == {
                "111111111111",
                "222222222222",
            }
            target = ResolvedMedicine(
                medicine=DomainMedicineMatch("", (), ("111111111111",), ()),
                document_ids=("000001_test",),
            )
            rows = await snap.evidence_reader.search(
                SearchCriteria(
                    source=DetectionSource.LOGIC,
                    section_codes=(SearchSectionCode("1"),),
                ),
                (target,),
            )
            assert len(rows) == 1
            assert (
                rows[0].unit_id.value
                == f"000001_test:{hashlib.sha256(old).hexdigest()}:1"
            )
            assert "旧共通本文" in rows[0].excerpt and "新A原文" not in rows[0].excerpt
            async with runtime.acquire() as latest:
                assert latest.generation_id.value == final.generation_id
                current = await latest.evidence_reader.search(
                    SearchCriteria(
                        source=DetectionSource.LOGIC,
                        section_codes=(SearchSectionCode("1"),),
                    ),
                    (target,),
                )
                assert len(current) == 1 and "新A原文" in current[0].excerpt
        assert not old_path.exists()
        with sqlite3.connect(publisher.index_path) as connection:
            assert connection.execute(
                "SELECT count(*) FROM generation_leases"
            ).fetchone() == (0,)
            assert connection.execute(
                "SELECT count(*) FROM registration_generations"
            ).fetchone() == (1,)
    finally:
        await workers.aclose()


def first_document_id(result):
    from backend.domain.attachment.identifiers import DocumentId

    return DocumentId(result.document_id)


@pytest.mark.parametrize("release_mode", ["normal", "terminated"])
def test_tc099_115_real_live_owner_survives_recovery_dead_owner_reaped(
    publisher, tmp_path, monkeypatch, release_mode
):
    old = source("生存owner旧本文")
    first = publish(publisher, old)
    old_path = (
        publisher.store._target(first_document_id(first), first.source_sha256)
        / "source.xml"
    )
    ready, release = tmp_path / "ready", tmp_path / "release"
    env = os.environ.copy()
    env["PYTHON_DOTENV_DISABLED"] = "1"
    for key in (
        "OPENAI_API_KEY",
        "GEMINI_API_KEY",
        "GOOGLE_API_KEY",
        "ANTHROPIC_API_KEY",
        "TYPESAFE_API_KEY",
    ):
        env[key] = ""
    child = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "backend.tests.support.generation_process_worker",
            "--index",
            str(publisher.index_path),
            "--imports",
            str(publisher.store.root),
            "--ready",
            str(ready),
            "--release",
            str(release),
        ],
        env=env,
        cwd=PROJECT_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        deadline = time.monotonic() + 30
        while not ready.exists():
            assert child.poll() is None
            assert time.monotonic() < deadline
            time.sleep(0.01)
        latest = publish(publisher, source("新しいactive本文", revised_at="2026-11"))
        assert latest.status == "registered_cleanup_pending"
        with monkeypatch.context() as clock:
            clock.setattr(time, "time", lambda: 50_000_000_000.0)
            publisher.recover()
        assert old_path.read_bytes() == old
        with sqlite3.connect(publisher.index_path) as connection:
            assert connection.execute(
                "SELECT count(*) FROM generation_leases"
            ).fetchone() == (1,)
        if release_mode == "normal":
            release.write_bytes(b"release after materialization")
        else:
            child.terminate()
        child.wait(timeout=10)
        publisher.recover()
        assert not old_path.exists()
        with sqlite3.connect(publisher.index_path) as connection:
            assert connection.execute(
                "SELECT count(*) FROM generation_leases"
            ).fetchone() == (0,)
            assert connection.execute(
                "SELECT count(*) FROM registration_generations"
            ).fetchone() == (1,)
        result = publisher.read_result(
            "000001_test",
            hashlib.sha256(
                source("新しいactive本文", revised_at="2026-11")
            ).hexdigest(),
        )
        assert (
            result.status == "registered"
            and result.generation_id == latest.generation_id
        )
    finally:
        if child.poll() is None:
            child.kill()
        child.communicate(timeout=10)


@pytest.mark.asyncio
async def test_tc095_all_detectors_and_search_pin_one_generation_then_release(
    publisher,
):
    from backend.application.retrieval.intent_contracts import IntentResult
    from backend.application.retrieval.retrieve_evidence import retrieve_evidence
    from backend.infrastructure.package_insert_definitions.loader import (
        get_package_insert_definitions,
    )
    from backend.infrastructure.persistence.medicine_reader import (
        SqlAlchemyMedicineReader,
    )

    old = source("旧世代警告本文", ("111111111111", "222222222222"))
    publish(publisher, old)
    workers = ReadWorkers()
    runtime = GenerationRuntime(publisher, workers=workers)
    engine = create_readonly_engine(publisher.index_path)

    class Detector:
        async def classify(self, request):
            with sqlite3.connect(publisher.index_path) as connection:
                assert connection.execute(
                    "SELECT count(*) FROM generation_leases"
                ).fetchone() == (1,)
            await workers.run(
                lambda: publish(publisher, source("新A警告本文", revised_at="2026-11"))
            )
            await workers.run(
                lambda: publish(
                    publisher,
                    source("新B警告本文", ("222222222222",), revised_at="2026-11"),
                )
            )
            return IntentResult(is_available=False)

    class Keywords:
        def extract_keywords(self, text):
            return ()

    try:
        result = await retrieve_evidence(
            "警告",
            ["111111111111"],
            medicine_reader=SqlAlchemyMedicineReader(engine, workers=workers),
            evidence_reader=SqlAlchemyEvidenceReader(engine, workers=workers),
            intent_classifier=Detector(),
            keyword_extractor=Keywords(),
            intent_policy=get_package_insert_definitions().intent_policy,
            snapshot_provider=runtime,
        )
        assert result.sources and all(
            "旧世代警告本文" in item.excerpt for item in result.sources
        )
        assert all(
            item.unit_id.value == f"000001_test:{hashlib.sha256(old).hexdigest()}:1"
            for item in result.sources
        )
        with sqlite3.connect(publisher.index_path) as connection:
            assert connection.execute(
                "SELECT count(*) FROM generation_leases"
            ).fetchone() == (0,)
    finally:
        await workers.aclose()
        engine.dispose()


@pytest.mark.asyncio
async def test_tc096_chat_materializes_before_stream_and_retains_inline_old_snapshot(
    publisher,
):
    from backend.application.retrieval.intent_contracts import IntentResult
    from backend.infrastructure.package_insert_definitions.loader import (
        get_package_insert_definitions,
    )
    from backend.infrastructure.persistence.medicine_reader import (
        SqlAlchemyMedicineReader,
    )
    from backend.presentation.chat_models import ChatMessage
    from backend.presentation.chat_service import AppChatService

    old = source("過去inline原文")
    publish(publisher, old)
    workers = ReadWorkers()
    runtime = GenerationRuntime(publisher, workers=workers)
    engine = create_readonly_engine(publisher.index_path)

    class Detector:
        async def classify(self, request):
            with sqlite3.connect(publisher.index_path) as connection:
                assert connection.execute(
                    "SELECT count(*) FROM generation_leases"
                ).fetchone() == (1,)
            return IntentResult(is_available=False)

    class Keywords:
        def extract_keywords(self, text):
            return ()

    class Provider:
        async def stream_response(self, messages, model=None):
            with sqlite3.connect(publisher.index_path) as connection:
                assert connection.execute(
                    "SELECT count(*) FROM generation_leases"
                ).fetchone() == (0,)
            await workers.run(
                lambda: publish(publisher, source("次の版本文", revised_at="2026-11"))
            )
            assert any("過去inline原文" in message["content"] for message in messages)
            yield "固定回答"

    service = AppChatService(
        medicine_reader=SqlAlchemyMedicineReader(engine, workers=workers),
        evidence_reader=SqlAlchemyEvidenceReader(engine, workers=workers),
        intent_classifier=Detector(),
        keyword_extractor=Keywords(),
        intent_policy=get_package_insert_definitions().intent_policy,
        answer_prompt_policy=get_package_insert_definitions().answer_prompt_policy,
        provider_factory=lambda _: Provider(),
        snapshot_provider=runtime,
    )
    try:
        reply = await service.answer_question(
            [ChatMessage(role="user", content="警告")], ["111111111111"]
        )
        assert reply.answer == "固定回答"
        assert reply.sources and all(
            "過去inline原文" in item.excerpt for item in reply.sources
        )
        assert (
            reply.sources[0].unit_id
            == f"000001_test:{hashlib.sha256(old).hexdigest()}:1"
        )
    finally:
        await workers.aclose()
        engine.dispose()


@pytest.mark.asyncio
async def test_tc096_cancel_during_acquisition_waits_owned_worker_and_releases(
    publisher, monkeypatch
):
    publish(publisher, source("取消取得本文"))
    workers = ReadWorkers()
    runtime = GenerationRuntime(publisher, workers=workers)
    entered, release = threading.Event(), threading.Event()
    acquire = runtime._acquire

    def blocked():
        result = acquire()
        entered.set()
        assert release.wait(10)
        return result

    monkeypatch.setattr(runtime, "_acquire", blocked)

    async def request():
        async with runtime.acquire():
            raise AssertionError("cancelled request must not enter acquired scope")

    task = asyncio.create_task(request())
    try:
        while not entered.is_set():
            await asyncio.sleep(0.01)
        task.cancel()
        await asyncio.sleep(0)
        assert not task.done()
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await task
        with sqlite3.connect(publisher.index_path) as connection:
            assert connection.execute(
                "SELECT count(*) FROM generation_leases"
            ).fetchone() == (0,)
    finally:
        release.set()
        await workers.aclose()


@pytest.mark.asyncio
async def test_tc094_requested_product_filters_mixed_table_without_removing_common(
    publisher,
):
    publish(publisher, mixed_source())
    workers = ReadWorkers()
    runtime = GenerationRuntime(publisher, workers=workers)
    try:
        async with runtime.acquire() as snapshot:
            criteria = SearchCriteria(
                source=DetectionSource.LOGIC, section_codes=(SearchSectionCode("1"),)
            )
            a = await snapshot.evidence_reader.search(
                criteria,
                (
                    ResolvedMedicine(
                        medicine=DomainMedicineMatch("", (), ("111111111111",), ()),
                        document_ids=("000001_test",),
                    ),
                ),
            )
            b = await snapshot.evidence_reader.search(
                criteria,
                (
                    ResolvedMedicine(
                        medicine=DomainMedicineMatch("", (), ("222222222222",), ()),
                        document_ids=("000001_test",),
                    ),
                ),
            )
            assert len(a) == len(b) == 1
            assert "A値" in a[0].excerpt and "B値" not in a[0].excerpt
            assert "B値" in b[0].excerpt and "A値" not in b[0].excerpt
            assert "共通値" in a[0].excerpt and "共通値" in b[0].excerpt
    finally:
        await workers.aclose()


@pytest.mark.asyncio
async def test_tc096_released_snapshot_cannot_be_reused_and_old_cache_discarded(
    publisher,
):
    publish(publisher, source("旧cached本文"))
    workers = ReadWorkers()
    runtime = GenerationRuntime(publisher, workers=workers)
    try:
        async with runtime.acquire() as snapshot:
            old_generation = snapshot.generation_id
            publish(publisher, source("新cached本文", revised_at="2026-11"))
        with pytest.raises(RuntimeError, match="released"):
            await snapshot.medicine_reader.read_medicines()
        assert runtime.cached_generation_id != old_generation
    finally:
        await workers.aclose()


def test_tc108_main_group_autocomplete_health_share_current_generation(
    publisher, monkeypatch
):
    from backend.main import create_app
    from fastapi.testclient import TestClient

    monkeypatch.setenv("PYTHON_DOTENV_DISABLED", "1")
    for key in (
        "OPENAI_API_KEY",
        "GEMINI_API_KEY",
        "GOOGLE_API_KEY",
        "ANTHROPIC_API_KEY",
        "TYPESAFE_API_KEY",
    ):
        monkeypatch.setenv(key, "")
    first = publish(publisher, source("旧候補本文", ("111111111111", "222222222222")))
    app = create_app(
        publisher.index_path.parent,
        publisher.index_path,
        import_directory=publisher.store.root,
    )
    with TestClient(app) as client:
        group = client.get("/api/medicines").json()
        assert set(group) == {"generation_id", "items"}
        assert group["generation_id"] == first.generation_id
        autocomplete = client.get("/api/medicines/autocomplete")
        assert autocomplete.status_code == 200
        assert autocomplete.json() == {
            "generation_id": first.generation_id,
            "items": [
                {
                    "n": "製品A",
                    "k": "",
                    "h": "",
                    "y": "111111111111",
                    "g": "",
                    "c": "他",
                },
                {"n": "B薬", "k": "", "h": "", "y": "222222222222", "g": "", "c": "他"},
            ],
        }
        new = source("新候補本文", revised_at="2026-11").replace(
            "製品A".encode(), "新版A".encode()
        )
        final = publish(publisher, new)
        group = client.get("/api/medicines").json()
        assert group["generation_id"] == final.generation_id
        assert {name for item in group["items"] for name in item["brand_names"]} == {
            "新版A",
            "B薬",
        }
        compact = client.get("/api/medicines/autocomplete").json()
        assert compact["generation_id"] == final.generation_id
        assert {item["n"] for item in compact["items"]} == {"新版A", "B薬"}
        assert (
            client.get("/api/medicines", params={"query": "製品A"}).json()["items"]
            == []
        )
        assert client.get("/health").json() == {
            "status": "ok",
            "document_count": 1,
            "unit_count": 2,
            "generation_id": final.generation_id,
        }


def test_tc097_113_recovery_removes_only_failed_registration_owned_artifacts(publisher):
    from backend.application.attachment_import.import_errors import ImportStorageError
    from backend.application.indexing.attachment_projection import project_attachment
    from backend.infrastructure.pmda_xml.artifact_mapping import PmdaArtifactEncoder
    from backend.infrastructure.pmda_xml.decoder import PmdaXmlDecoder

    publish(publisher, source("公開済み本文"))
    legacy = source("未登録旧保存物", ("333333333333",), doc="legacy")
    decoded = PmdaXmlDecoder().decode(legacy)
    bundle = PmdaArtifactEncoder().encode(
        decoded.document, project_attachment(decoded.document), decoded.source_info
    )
    publisher.store.commit(bundle, legacy)
    legacy_target = publisher.store._target(bundle.document_id, bundle.source_sha256)
    preserved = {path: path.read_bytes() for path in legacy_target.iterdir()}
    failed = source("未公開の登録attempt", revised_at="2026-11")

    def fault(phase):
        if phase == "artifacts":
            raise OSError("injected artifact publication failure")

    publisher.fault = fault
    with pytest.raises(ImportStorageError):
        publish(publisher, failed)
    publisher.fault = lambda phase: None
    publisher.recover()
    target = publisher.store._target(
        decoded.document.document_id.__class__("000001_test"),
        hashlib.sha256(failed).hexdigest(),
    )
    assert not (target / "source.xml").exists()
    assert {path: path.read_bytes() for path in legacy_target.iterdir()} == preserved
    assert not target.exists()
    retried = publish(publisher, failed)
    assert retried.status == "registered"
    assert not retried.reused


def test_tc102_114_existing_build_cli_retries_cleanup_without_new_generation(
    publisher, monkeypatch, capsys
):
    from pathlib import Path

    from backend.infrastructure.cli.build_search_index import main

    first = publish(publisher, source("cleanup対象"))
    old_path = (
        publisher.store._target(first_document_id(first), first.source_sha256)
        / "source.xml"
    )
    original_unlink = Path.unlink

    def fail_one(path, *args, **kwargs):
        if path == old_path:
            raise PermissionError("controlled cleanup failure")
        return original_unlink(path, *args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(Path, "unlink", fail_one)
        final = publish(publisher, source("現在本文", revised_at="2026-11"))
        assert final.status == "registered_cleanup_pending"
    monkeypatch.setenv("MEDI_CHAT_IMPORT_DIR", str(publisher.store.root))
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "build_search_index",
            "--index-path",
            str(publisher.index_path),
            "--structured-dir",
            str(publisher.store.root.parent / "structured"),
        ],
    )
    assert main() == 0, capsys.readouterr()
    assert not old_path.exists()
    result = publisher.read_result(final.document_id, final.source_sha256)
    assert result.generation_id == final.generation_id
    assert result.registration_sequence == final.registration_sequence
    assert result.status == "registered"


@pytest.mark.asyncio
async def test_tc096_exception_releases_generation_lease(publisher):
    publish(publisher, source("例外でも保全本文"))
    workers = ReadWorkers()
    runtime = GenerationRuntime(publisher, workers=workers)
    try:
        with pytest.raises(ValueError, match="controlled retrieval failure"):
            async with runtime.acquire():
                raise ValueError("controlled retrieval failure")
        with sqlite3.connect(publisher.index_path) as connection:
            assert connection.execute(
                "SELECT COUNT(*) FROM generation_leases"
            ).fetchone() == (0,)
    finally:
        await workers.aclose()


def test_tc103_new_active_manifest_injection_cannot_transfer_old_ownership(publisher):
    import json

    from backend.domain.attachment.identifiers import DocumentId

    original = publish(publisher, source("旧所有原文"))
    external = source("新activeQ本文", ("333333333333",), doc="Q")
    q = publish(publisher, external)
    q_path = (
        publisher.store._target(DocumentId(q.document_id), q.source_sha256)
        / "source.xml"
    )
    with sqlite3.connect(publisher.index_path) as connection:
        files = json.loads(
            connection.execute(
                "SELECT files_json FROM registration_receipts WHERE version_id=?",
                (f"{original.document_id}:{original.source_sha256}",),
            ).fetchone()[0]
        )
        files.append(
            {
                "path": str(q_path),
                "root": str(publisher.store.root),
                "sha256": q.source_sha256,
            }
        )
        connection.execute(
            "UPDATE registration_receipts SET files_json=? WHERE version_id=?",
            (json.dumps(files), f"{original.document_id}:{original.source_sha256}"),
        )
    final = publish(publisher, source("A更新", revised_at="2026-11"))
    assert final.status == "registered_cleanup_pending"
    assert final.cleanup_pending == (
        (f"{original.document_id}:{original.source_sha256}", "unowned_file"),
    )
    assert q_path.read_bytes() == external


@pytest.mark.asyncio
async def test_tc093_094_105_revision_and_old_inline_snapshot_are_version_qualified(
    publisher,
):
    old = source("旧AB本文", ("111111111111", "222222222222"))
    first = publish(publisher, old)
    workers = ReadWorkers()
    runtime = GenerationRuntime(publisher, workers=workers)
    criteria = SearchCriteria(
        source=DetectionSource.LOGIC, section_codes=(SearchSectionCode("1"),)
    )
    a = ResolvedMedicine(
        medicine=DomainMedicineMatch("", (), ("111111111111",), ()),
        document_ids=("000001_test",),
    )
    b = ResolvedMedicine(
        medicine=DomainMedicineMatch("", (), ("222222222222",), ()),
        document_ids=("000001_test",),
    )
    try:
        async with runtime.acquire() as previous:
            (inline,) = await previous.evidence_reader.search(criteria, (b,))
            old_snapshot = inline.to_dict()
            new = source("新A本文").replace(b"2026-10", b"2026-11")
            final = publish(publisher, new)
            async with runtime.acquire() as current:
                (new_a,) = await current.evidence_reader.search(criteria, (a,))
                (old_b,) = await current.evidence_reader.search(criteria, (b,))
                assert (
                    new_a.unit_id.value
                    == f"000001_test:{hashlib.sha256(new).hexdigest()}:1"
                )
                assert "2026-11" in repr(new_a.document_revision.to_dict())
                assert (
                    old_b.unit_id.value
                    == f"000001_test:{hashlib.sha256(old).hexdigest()}:1"
                )
                assert "2026-10" in repr(old_b.document_revision.to_dict())
                assert "旧AB本文" in old_b.excerpt and "新A本文" not in old_b.excerpt
                assert current.generation_id.value == final.generation_id
            assert publisher.read_result(
                first.document_id, first.source_sha256
            ).active_yj_codes == ("222222222222",)
        publish(publisher, source("新B本文", ("222222222222",), revised_at="2026-11"))
        assert inline.to_dict() == old_snapshot
        with sqlite3.connect(publisher.index_path) as connection:
            assert connection.execute(
                "SELECT COUNT(*) FROM units WHERE unit_id=?", (inline.unit_id.value,)
            ).fetchone() == (0,)
    finally:
        await workers.aclose()
