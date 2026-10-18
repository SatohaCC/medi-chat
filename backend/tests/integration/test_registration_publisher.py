import hashlib
import json
import os
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

import pytest
from backend.application.attachment_import.import_errors import (
    ImportCancelled,
    ImportNotFound,
    ImportStorageError,
)
from backend.application.indexing.index_errors import IndexSourceError
from backend.infrastructure.persistence.attachment_import_store import (
    FileAttachmentImportStore,
)
from backend.infrastructure.persistence.registration_publisher import (
    RegistrationInput,
    SqliteRegistrationPublisher,
)
from backend.infrastructure.persistence.registration_reader import (
    read_registered_snapshot,
)
from backend.infrastructure.pmda_xml.decoder import PmdaXmlDecoder
from backend.tests.application.indexing.test_active_attachment_projection import (
    mixed_source,
)
from backend.tests.infrastructure.persistence.test_alembic_migrations import (
    _migrate_database,
)
from backend.tests.support.paths import PROJECT_ROOT


def source(body, codes=("111111111111",), *, doc="test", revised_at="2026-10"):
    from backend.tests.support.attachment_import_fixtures import xml_source

    value = xml_source(
        f"<Warnings><Detail><Lang>{body}</Lang></Detail></Warnings>"
    ).replace(
        b"<PackageInsertNo>test</PackageInsertNo>",
        f"<PackageInsertNo>{doc}</PackageInsertNo>".encode(),
    )
    value = value.replace(b"111111111111", codes[0].encode())
    if len(codes) > 1:
        value = value.replace(
            b"</ApprovalEtc>",
            f'<DetailBrandName id="B"><ApprovalBrandName><Lang>B薬</Lang></ApprovalBrandName><BrandCode><YJCode>{codes[1]}</YJCode></BrandCode></DetailBrandName></ApprovalEtc>'.encode(),
        )
    return value.replace(b"2026-10", revised_at.encode())


@pytest.fixture
def publisher(tmp_path):
    index = tmp_path / "index.sqlite3"
    _migrate_database(index, tmp_path)
    return SqliteRegistrationPublisher(
        index, FileAttachmentImportStore(tmp_path / "imports")
    )


def publish(publisher, value):
    return publisher.publish(PmdaXmlDecoder().decode(value), value)


def rows(publisher, sql):
    with sqlite3.connect(publisher.index_path) as connection:
        return connection.execute(sql).fetchall()


def snapshot(publisher):
    with sqlite3.connect(publisher.index_path) as connection:
        return "\n".join(connection.iterdump())


def test_tc091_deleted_receipt_retains_no_document_body(publisher):
    old = source("原文をreceiptに残さない")
    publish(publisher, old)
    old_id = f"000001_test:{hashlib.sha256(old).hexdigest()}"
    publish(publisher, source("更新した原文", revised_at="2026-11"))
    with sqlite3.connect(publisher.index_path) as connection:
        row = connection.execute(
            "SELECT * FROM registration_receipts WHERE version_id=?", (old_id,)
        ).fetchone()
        assert "原文をreceiptに残さない" not in repr(row)
        columns = connection.execute(
            "PRAGMA table_info(registration_receipts)"
        ).fetchall()
        assert "document_payload_json" not in {column[1] for column in columns}
        assert connection.execute(
            "SELECT count(*) FROM registration_version_artifacts WHERE version_id=?",
            (old_id,),
        ).fetchone() == (0,)


def test_tc093_same_document_versions_read_their_own_original_metadata(publisher):
    from backend.domain.retrieval.primitives import DetectionSource
    from backend.infrastructure.package_insert_definitions.loader import (
        get_package_insert_definitions,
    )
    from backend.infrastructure.persistence import schema
    from backend.infrastructure.persistence.evidence_reader import (
        _read_evidence,
        _unit_document_select,
    )
    from sqlalchemy import create_engine

    old = source("旧版B本文", ("111111111111", "222222222222"))
    publish(publisher, old)
    new = (
        source("新版A本文")
        .replace("製品A".encode(), "新版製品A".encode())
        .replace(b"2026-10", b"2027-01")
    )
    publish(publisher, new)
    engine = create_engine(f"sqlite:///{publisher.index_path.as_posix()}")
    try:
        with engine.connect() as connection:
            evidence = _read_evidence(
                connection,
                _unit_document_select(schema.units),
                DetectionSource.LOGIC,
                get_package_insert_definitions().text_search_policy,
            )
        by_yj = {
            tuple(code.value for code in item.product_yj_codes): item
            for item in evidence
        }
        assert by_yj[("111111111111",)].product_name == "新版製品A"
        assert by_yj[("222222222222",)].product_name == "B薬"
        assert "2027" in repr(by_yj[("111111111111",)].document_revision)
        assert "2026" in repr(by_yj[("222222222222",)].document_revision)
    finally:
        engine.dispose()


def test_tc085_086_093_real_publish_partial_b_keeps_distinct_sha_and_projection(
    publisher,
):
    o = mixed_source()
    first = publish(publisher, o)
    n = source("新版A", doc="test", revised_at="2026-11")
    result = publish(publisher, n)
    assert first.status == result.status == "registered"
    assert result.search_index_updated is True
    assert result.registration_sequence == 2
    assert result.active_yj_codes == ("111111111111",)
    assert result.replaced_yj_codes == ("111111111111",)
    assert rows(
        publisher,
        "SELECT yj_code,version_id FROM active_registrations ORDER BY yj_code",
    ) == [
        ("111111111111", f"000001_test:{hashlib.sha256(n).hexdigest()}"),
        ("222222222222", f"000001_test:{hashlib.sha256(o).hexdigest()}"),
    ]
    units = [
        json.loads(row[0])
        for row in rows(publisher, "SELECT payload_json FROM units ORDER BY unit_id")
    ]
    assert len(units) == 2
    by_yj = {tuple(unit["product_yj_codes"]): unit for unit in units}
    assert "A値" not in by_yj[("222222222222",)]["text"]
    assert "B値" in by_yj[("222222222222",)]["text"]
    assert (
        by_yj[("111111111111",)]["unit_id"]
        == f"000001_test:{hashlib.sha256(n).hexdigest()}:1"
    )
    assert publisher.read_result(
        "000001_test", hashlib.sha256(o).hexdigest()
    ).active_yj_codes == ("222222222222",)


@pytest.mark.parametrize(
    "phase", ["artifacts", "index", "candidates", "transaction", "commit"]
)
def test_tc097_prepublication_failure_preserves_all_tables_and_old_files(
    publisher, phase
):
    o = source("旧本文", ("111111111111", "222222222222"))
    publish(publisher, o)
    before = snapshot(publisher)
    original = {
        path: path.read_bytes()
        for path in publisher.store.root.rglob("*")
        if path.is_file() and ".locks" not in path.parts
    }

    def fail(current):
        if current == phase:
            raise OSError("fixed fault")

    publisher.fault = fail
    n = source("新版失敗", ("111111111111", "222222222222"), revised_at="2026-11")
    with pytest.raises(ImportStorageError):
        publish(publisher, n)
    assert snapshot(publisher) == before
    assert all(path.read_bytes() == content for path, content in original.items())
    with pytest.raises(ImportNotFound):
        publisher.read_result("000001_test", hashlib.sha256(n).hexdigest())


@pytest.mark.parametrize("phase", ["commit", "after_commit"])
def test_tc098_cancel_before_and_after_publication(publisher, phase):
    publish(publisher, source("取消前の旧本文"))
    before = snapshot(publisher)
    cancelled = False
    observed = []

    def fault(current):
        nonlocal cancelled
        if current == phase:
            observed.append(current)
            cancelled = True

    def check_cancel():
        if cancelled:
            raise ImportCancelled()

    publisher.fault = fault
    new = source("取消時の新版本文", revised_at="2026-11")
    if phase == "commit":
        with pytest.raises(ImportCancelled):
            publisher.publish(
                PmdaXmlDecoder().decode(new), new, check_cancel=check_cancel
            )
        assert snapshot(publisher) == before
        with pytest.raises(ImportNotFound):
            publisher.read_result("000001_test", hashlib.sha256(new).hexdigest())
    else:
        result = publisher.publish(
            PmdaXmlDecoder().decode(new), new, check_cancel=check_cancel
        )
        assert result.status == "registered_cleanup_pending"
        assert result.cleanup_pending[0][1] == "cleanup_required"
        assert result.search_index_updated and result.registration_sequence == 2
        assert (
            publisher.read_result(
                "000001_test", hashlib.sha256(new).hexdigest()
            ).generation_id
            == result.generation_id
        )
        publisher.fault = lambda phase: None
        retry = publish(publisher, new)
        assert retry.reused and retry.status == "registered"
        assert retry.generation_id == result.generation_id
        assert retry.registration_sequence == 2
    assert observed == [phase]


def test_tc104_cleanup_preserves_shared_figure_and_unowned_files(publisher):
    root = publisher.store.root
    root.mkdir(parents=True, exist_ok=True)
    shared = root / "shared.svg"
    shared.write_bytes(b"<svg>shared</svg>")
    exclusive = root / "exclusive.svg"
    exclusive.write_bytes(b"<svg>old only</svg>")
    sentinels = [
        root / name
        for name in ("backup.sqlite3", "evidence.txt", "dictionary.dat", ".ignored")
    ]
    for path in sentinels:
        path.write_bytes(b"unowned preserve")
    old = source("共用図を持つ旧版", ("111111111111", "222222222222"))
    other = source("共用図を持つ他製品", ("333333333333",), doc="other")
    old_path, other_path = root / "old.xml", root / "other.xml"
    old_path.write_bytes(old)
    other_path.write_bytes(other)
    publisher.publish_inputs(
        (
            RegistrationInput(
                PmdaXmlDecoder().decode(old),
                old,
                (old_path, shared, exclusive),
                old_path,
            ),
            RegistrationInput(
                PmdaXmlDecoder().decode(other), other, (other_path, shared), other_path
            ),
        ),
        initial=True,
    )
    publish(publisher, source("Aのみ更新", revised_at="2026-11"))
    assert old_path.exists() and exclusive.exists()
    publish(publisher, source("Bも更新", ("222222222222",), revised_at="2026-11"))
    assert not old_path.exists() and not exclusive.exists()
    assert shared.read_bytes() == b"<svg>shared</svg>"
    assert other_path.read_bytes() == other
    assert all(path.read_bytes() == b"unowned preserve" for path in sentinels)


def test_tc090_102_cleanup_failure_retry_does_not_republish_or_restore_receipt(
    publisher, monkeypatch
):
    o = source("旧本文")
    first = publish(publisher, o)
    before = publisher.store.read(first_document_id(first), first.source_sha256)
    assert before.status == "stored" and not before.search_index_updated
    n = source("新版本文", revised_at="2026-11")
    original = Path.unlink

    def fail(path, *args, **kwargs):
        if (
            path.name == "source.xml"
            and hashlib.sha256(path.read_bytes()).hexdigest()
            == hashlib.sha256(o).hexdigest()
        ):
            raise PermissionError("fixed cleanup fault")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", fail)
    second = publish(publisher, n)
    assert second.status == "registered_cleanup_pending"
    assert second.cleanup_pending
    assert second.search_index_updated
    generation = second.generation_id
    monkeypatch.setattr(Path, "unlink", original)
    retry = publish(publisher, n)
    assert retry.reused and retry.status == "registered"
    assert retry.generation_id == generation and retry.registration_sequence == 2
    old = publish(publisher, o)
    assert old.reused and old.status == "superseded" and old.artifacts_deleted
    assert old.registration_sequence == 1 and old.active_yj_codes == ()
    assert (
        not publisher.store._target(first_document_id(first), first.source_sha256)
        .joinpath("source.xml")
        .exists()
    )


def first_document_id(result):
    from backend.domain.attachment.identifiers import DocumentId

    return DocumentId(result.document_id)


def test_tc116_active_fingerprint_reloads_actual_inputs_and_ignores_inactive_cleanup(
    publisher,
):
    old = source("旧版")
    new = source("新版", revised_at="2026-11")
    publish(publisher, old)
    published = publish(publisher, new)
    first = read_registered_snapshot(publisher.index_path)
    second = read_registered_snapshot(publisher.index_path)
    assert first is not None and second is not None
    assert first.fingerprint == second.fingerprint
    assert first.fingerprint.startswith("content-v1:")
    assert len(first.units) == 1 and "新版" in str(first.units[0].payload["text"])
    assert (
        not publisher.store._target(
            first_document_id(published), hashlib.sha256(old).hexdigest()
        )
        .joinpath("source.xml")
        .exists()
    )
    original = (
        publisher.store._target(first_document_id(published), published.source_sha256)
        / "document.json"
    )
    original.write_bytes(original.read_bytes() + b" ")
    with pytest.raises(IndexSourceError, match="artifact"):
        read_registered_snapshot(publisher.index_path)


@pytest.mark.parametrize("kind", ["outside", "traversal", "unowned", "symlink"])
def test_tc103_cleanup_refuses_untrusted_manifest_entries_and_preserves_sentinels(
    publisher, kind
):
    old = source("旧版")
    publish(publisher, old)
    sentinel = (
        publisher.store.root.parent / "protected.txt"
        if kind == "outside"
        else publisher.store.root / "protected.txt"
    )
    sentinel.write_bytes(b"fixed protected bytes")
    path = sentinel
    if kind == "traversal":
        path = publisher.store.root / "versions" / ".." / "protected.txt"
    if kind == "symlink":
        path = publisher.store.root / "protected-link.txt"
        os.symlink(sentinel, path)
        assert path.is_symlink()

    with sqlite3.connect(publisher.index_path) as connection:
        files = json.loads(
            connection.execute(
                "SELECT files_json FROM registration_receipts WHERE sequence=1"
            ).fetchone()[0]
        )
        files.append(
            {
                "path": str(path),
                "root": str(publisher.store.root),
                "sha256": hashlib.sha256(b"fixed protected bytes").hexdigest(),
            }
        )
        connection.execute(
            "UPDATE registration_receipts SET files_json=? WHERE sequence=1",
            (json.dumps(files),),
        )
    new = publish(publisher, source("新版", revised_at="2026-11"))
    assert new.status == "registered_cleanup_pending"
    assert new.cleanup_pending == (
        (f"000001_test:{hashlib.sha256(old).hexdigest()}", "unowned_file"),
    )
    assert sentinel.read_bytes() == b"fixed protected bytes"
    if kind == "symlink":
        assert path.is_symlink()


@pytest.mark.parametrize("separate_yj", [False, True])
@pytest.mark.parametrize("entrypoints", ["publisher", "cli_api"])
def test_tc100_101_real_process_publish_uses_revision_dates_and_keeps_other_yj(
    publisher, tmp_path, separate_yj, entrypoints
):
    old = source("旧A+B", ("111111111111", "222222222222"))
    publish(publisher, old)
    n = source("先parse後commit", ("111111111111",), revised_at="2026-12")
    p = source(
        "後parse先commit",
        ("222222222222" if separate_yj else "111111111111",),
        revised_at="2026-11",
    )
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
    processes = []
    try:
        for name, value in (("N", n), ("P", p)):
            original = tmp_path / (name + ".xml")
            original.write_bytes(value)
            parsed = tmp_path / (name + ".parsed")
            release = tmp_path / (name + ".release")
            process = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "backend.tests.support.registration_process_worker",
                    "--source",
                    str(original),
                    "--index",
                    str(publisher.index_path),
                    "--imports",
                    str(publisher.store.root),
                    "--parsed",
                    str(parsed),
                    "--release",
                    str(release),
                    "--mode",
                    ("cli" if name == "N" else "api")
                    if entrypoints == "cli_api"
                    else "publisher",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                cwd=PROJECT_ROOT,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            processes.append(process)
            deadline = time.monotonic() + 30
            while not parsed.exists():
                assert process.poll() is None
                assert time.monotonic() < deadline
                time.sleep(0.01)
            assert parsed.read_text().isdigit()
        # Explicit barriers, not elapsed time, establish the reversed commit order.
        (tmp_path / "P.release").write_text("commit", encoding="ascii")
        output, error = processes[1].communicate(timeout=30)
        assert processes[1].returncode == 0, error
        assert output.strip() == "2"
        (tmp_path / "N.release").write_text("commit", encoding="ascii")
        output, error = processes[0].communicate(timeout=30)
        assert processes[0].returncode == 0, error
        assert output.strip() == "3"
    finally:
        for process in processes:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=10)
    active = rows(
        publisher,
        "SELECT yj_code,version_id FROM active_registrations ORDER BY yj_code",
    )
    assert active[0] == ("111111111111", f"000001_test:{hashlib.sha256(n).hexdigest()}")
    assert active[1] == (
        "222222222222",
        f"000001_test:{hashlib.sha256(p).hexdigest()}"
        if separate_yj
        else f"000001_test:{hashlib.sha256(old).hexdigest()}",
    )
    assert rows(
        publisher, "SELECT sequence FROM registration_receipts ORDER BY sequence"
    ) == [(1,), (2,), (3,)]
