"""TC-027/028/032〜038/040〜043: real local filesystem version storage."""

import hashlib
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace

import pytest
from backend.application.attachment_import.import_errors import (
    ImportConflict,
    ImportLimitExceeded,
    ImportNotFound,
    ImportStorageError,
)
from backend.infrastructure.pmda_xml.artifact_mapping import MAX_ARTIFACT_BYTES
from backend.infrastructure.sources.attachment_import_store import (
    FileAttachmentImportStore,
)
from backend.tests.attachment_import_fixtures import encoded, xml_source


def hashes(root):
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in root.rglob("*")
        if path.is_file() and "versions" in path.parts
    }


def test_complete_original_and_artifacts_survive_new_store_instance(tmp_path):
    source = xml_source()
    bundle = encoded(source)
    store = FileAttachmentImportStore(tmp_path)
    result = store.commit(bundle, source)
    assert not result.reused and result.search_index_updated is False
    assert result.source_sha256 == hashlib.sha256(source).hexdigest()
    assert result.products[0].brand_name == "製品A"
    assert result.revisions[0].year_month == "2026-10"
    assert result.section_count == result.search_unit_count == 1
    (source_path,) = tmp_path.rglob("source.xml")
    assert source_path.read_bytes() == source
    assert {path.name for path in source_path.parent.iterdir()} >= {
        "source.xml",
        "document.json",
        "search_units.jsonl",
        "validation.json",
        "source_metadata.json",
        "result.json",
    }
    assert (
        FileAttachmentImportStore(tmp_path).read(
            bundle.document_id, bundle.source_sha256
        )
        == result
    )


def test_distinct_original_hashes_are_immutable_versions_even_with_same_revision(
    tmp_path,
):
    source_a = xml_source()
    source_b = xml_source("<Warnings><Lang>別の本文</Lang></Warnings>")
    store = FileAttachmentImportStore(tmp_path)
    a = encoded(source_a)
    b = encoded(source_b)
    store.commit(a, source_a)
    before = hashes(tmp_path)
    store.commit(b, source_b)
    assert all(hashes(tmp_path)[name] == value for name, value in before.items())
    assert len(list(tmp_path.rglob("source.xml"))) == 2
    assert (
        store.read(a.document_id, a.source_sha256).source_sha256
        != store.read(b.document_id, b.source_sha256).source_sha256
    )


@pytest.mark.parametrize("same", [True, True, True, False, False, False])
def test_concurrent_staged_imports_converge_or_keep_separate_versions(
    tmp_path, monkeypatch, same
):
    source_a = xml_source()
    source_b = (
        source_a
        if same
        else xml_source("<Warnings><Lang>並行の別本文</Lang></Warnings>")
    )
    bundle_a = encoded(source_a)
    bundle_b = encoded(source_b)
    barrier = threading.Barrier(2)
    stores = [FileAttachmentImportStore(tmp_path), FileAttachmentImportStore(tmp_path)]
    for store in stores:
        original = store._publish

        def publish(stage, target, check_cancel, original=original):
            barrier.wait(timeout=10)
            return original(stage, target, check_cancel)

        monkeypatch.setattr(store, "_publish", publish)
    with ThreadPoolExecutor(2) as pool:
        a = pool.submit(stores[0].commit, bundle_a, source_a)
        b = pool.submit(stores[1].commit, bundle_b, source_b)
        results = [a.result(timeout=15), b.result(timeout=15)]
    if same:
        assert sorted(result.reused for result in results) == [False, True]
        assert results[0].source_sha256 == results[1].source_sha256
    else:
        assert all(not result.reused for result in results)
    assert len(list(tmp_path.rglob("source.xml"))) == (1 if same else 2)
    assert not list(tmp_path.glob(".stage-*"))


@pytest.mark.parametrize(
    "filename",
    [
        "source.xml",
        "document.json",
        "search_units.jsonl",
        "validation.json",
        "source_metadata.json",
        "result.json",
    ],
)
def test_existing_key_conflict_never_repairs_or_overwrites(tmp_path, filename):
    source = xml_source()
    bundle = encoded(source)
    store = FileAttachmentImportStore(tmp_path)
    store.commit(bundle, source)
    (path,) = tmp_path.rglob(filename)
    path.write_bytes(b"corrupted")
    before = hashes(tmp_path)
    with pytest.raises(ImportConflict):
        store.commit(bundle, source)
    assert hashes(tmp_path) == before


@pytest.mark.parametrize(
    "failure",
    [
        "source.xml",
        "document.json",
        "search_units.jsonl",
        "validation.json",
        "source_metadata.json",
        "result.json",
        "integrity.json",
        "publish",
    ],
)
def test_io_failure_leaves_no_partial_version_and_protects_existing(
    tmp_path, monkeypatch, failure
):
    store = FileAttachmentImportStore(tmp_path)
    original_source = xml_source()
    original_bundle = encoded(original_source)
    store.commit(original_bundle, original_source)
    before = hashes(tmp_path)
    source = xml_source("<Warnings><Lang>新しい版</Lang></Warnings>")
    bundle = encoded(source)
    original_write = store._write_file

    def write(path, content):
        if path.name == failure:
            raise OSError("private absolute path capacity/permission error")
        return original_write(path, content)

    monkeypatch.setattr(store, "_write_file", write)
    if failure == "publish":
        monkeypatch.setattr(
            store,
            "_publish",
            lambda *a: (_ for _ in ()).throw(OSError("private absolute path")),
        )
    with pytest.raises(ImportStorageError) as caught:
        store.commit(bundle, source)
    assert "private" not in str(caught.value)
    assert hashes(tmp_path) == before
    assert not list(tmp_path.glob(".stage-*"))
    with pytest.raises(ImportNotFound):
        store.read(bundle.document_id, bundle.source_sha256)


def test_get_is_absent_during_stage_and_complete_after_atomic_publish(
    tmp_path, monkeypatch
):
    source = xml_source()
    bundle = encoded(source)
    store = FileAttachmentImportStore(tmp_path)
    entered = threading.Event()
    release = threading.Event()
    original = store._write_file

    def write(path, content):
        original(path, content)
        if path.name == "document.json":
            entered.set()
            assert release.wait(10)

    monkeypatch.setattr(store, "_write_file", write)
    with ThreadPoolExecutor(1) as pool:
        future = pool.submit(store.commit, bundle, source)
        assert entered.wait(10)
        with pytest.raises(ImportNotFound):
            store.read(bundle.document_id, bundle.source_sha256)
        release.set()
        result = future.result(timeout=10)
    assert store.read(bundle.document_id, bundle.source_sha256) == result


@pytest.mark.parametrize("over", [False, True])
def test_four_artifact_utf8_byte_sum_exact_limit_includes_result_metadata(
    tmp_path, over
):
    source = xml_source()
    bundle = encoded(source)
    store = FileAttachmentImportStore(tmp_path)
    old_source = xml_source("<Warnings><Detail><Lang>既存版</Lang></Detail></Warnings>")
    old_bundle = encoded(old_source)
    old_result = store.commit(old_bundle, old_source)
    old_hashes = hashes(tmp_path)
    files = list(bundle.files)
    measured = sum(
        len(file.content) for file in files if file.name != "source_metadata.json"
    )
    index = next(
        index for index, file in enumerate(files) if file.name == "document.json"
    )
    # Valid JSON whitespace pads actual bytes; Japanese content already differs from char count.
    files[index] = replace(
        files[index],
        content=files[index].content
        + b" " * (MAX_ARTIFACT_BYTES - measured + int(over)),
    )
    adjusted = replace(bundle, files=tuple(files))
    assert len(files[index].content.decode("utf-8")) < len(files[index].content)
    assert sum(
        len(file.content) for file in files if file.name != "source_metadata.json"
    ) == MAX_ARTIFACT_BYTES + int(over)
    if over:
        with pytest.raises(ImportLimitExceeded):
            store.commit(adjusted, source)
        assert hashes(tmp_path) == old_hashes
        assert (
            store.read(old_bundle.document_id, old_bundle.source_sha256) == old_result
        )
    else:
        assert store.commit(adjusted, source).status == "stored"


@pytest.mark.parametrize(
    "filename",
    [
        "../outside.xml",
        "C:\\outside.xml",
        "\\\\host\\share\\outside.xml",
        "/outside.xml",
    ],
)
def test_upload_filename_never_selects_storage_location(tmp_path, filename):
    outside = tmp_path / "outside.xml"
    outside.write_bytes(b"sentinel")
    root = tmp_path / "imports"
    source = xml_source()
    bundle = encoded(source, filename=filename)
    result = FileAttachmentImportStore(root).commit(bundle, source)
    assert result.status == "stored"
    assert outside.read_bytes() == b"sentinel"
    assert len(list(root.rglob("source.xml"))) == 1


def test_startup_cleanup_only_removes_owned_orphan_stage(tmp_path):
    store = FileAttachmentImportStore(tmp_path)
    source = xml_source()
    bundle = encoded(source)
    store.commit(bundle, source)
    before = hashes(tmp_path)
    orphan = tmp_path / ".stage-orphan"
    orphan.mkdir()
    (orphan / ".attachment-stage").write_text("medi-chat.pmda-import-stage.v1")
    (orphan / "partial").write_bytes(b"orphan")
    unrelated = tmp_path / ".stage-unrelated"
    unrelated.mkdir()
    (unrelated / "sentinel").write_bytes(b"untouched")
    FileAttachmentImportStore(tmp_path).cleanup()
    assert not orphan.exists()
    assert (unrelated / "sentinel").read_bytes() == b"untouched"
    assert hashes(tmp_path) == before
