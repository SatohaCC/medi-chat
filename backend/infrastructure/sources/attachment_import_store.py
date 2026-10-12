import hashlib
import json
import os
import re
import shutil
import time
import uuid
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path
from typing import BinaryIO

from ...application.attachment_import.import_errors import (
    ImportConflict,
    ImportLimitExceeded,
    ImportNotFound,
    ImportStorageError,
)
from ...application.attachment_import.import_models import ArtifactBundle, ImportResult
from ...domain.attachment.identifiers import DocumentId
from ..pmda_xml.artifact_mapping import MAX_ARTIFACT_BYTES, result_from_dict


class FileAttachmentImportStore:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        try:
            self.root.mkdir(parents=True, exist_ok=True)
            (self.root / ".locks").mkdir(exist_ok=True)
            self.cleanup()
        except OSError:
            raise ImportStorageError(
                "storage_error", "Import storage is unavailable"
            ) from None

    def _target(self, document_id: DocumentId, digest: str) -> Path:
        if re.fullmatch(r"[0-9a-f]{64}", digest) is None:
            raise ImportNotFound("import_not_found", "Stored import does not exist")
        document_key = hashlib.sha256(document_id.value.encode("utf-8")).hexdigest()
        path = self.root / "versions" / document_key / digest
        if not path.resolve().is_relative_to(self.root):
            raise ImportConflict("storage_conflict", "Stored import is inconsistent")
        return path

    def read(self, document_id: DocumentId, source_sha256: str) -> ImportResult:
        target = self._target(document_id, source_sha256)
        if not target.is_dir():
            raise ImportNotFound("import_not_found", "Stored import does not exist")
        try:
            integrity = json.loads((target / "integrity.json").read_bytes())
            required = {
                "source.xml",
                "document.json",
                "search_units.jsonl",
                "validation.json",
                "source_metadata.json",
                "result.json",
            }
            if integrity.keys() != required:
                raise ValueError("incomplete integrity manifest")
            for name in required:
                path = target / name
                if path.is_symlink() or not path.resolve().is_relative_to(target):
                    raise ValueError("unsafe artifact path")
                if hashlib.sha256(path.read_bytes()).hexdigest() != integrity[name]:
                    raise ValueError("artifact content differs")
            if integrity["source.xml"] != source_sha256:
                raise ValueError("source hash differs")
            result = result_from_dict(json.loads((target / "result.json").read_bytes()))
            if (
                result.document_id != document_id.value
                or result.source_sha256 != source_sha256
                or result.status != "stored"
                or result.search_index_updated
            ):
                raise ValueError("saved identity differs")
            return result
        except OSError, ValueError, TypeError, KeyError:
            raise ImportConflict(
                "storage_conflict", "Stored import is inconsistent"
            ) from None

    def commit(
        self,
        bundle: ArtifactBundle,
        source: bytes,
        *,
        check_cancel: Callable[[], None] = lambda: None,
    ) -> ImportResult:
        target = self._target(bundle.document_id, bundle.source_sha256)
        if hashlib.sha256(source).hexdigest() != bundle.source_sha256:
            raise ImportConflict(
                "source_hash_conflict", "Original source identity is inconsistent"
            )
        if len(source) > 10 * 1024 * 1024:
            raise ImportLimitExceeded(
                "source_size_limit", "XML input exceeds the size limit"
            )
        if target.exists():
            return replace(
                self.read(bundle.document_id, bundle.source_sha256), reused=True
            )
        files = {file.name: file.content for file in bundle.files}
        if set(files) != {
            "document.json",
            "search_units.jsonl",
            "validation.json",
            "source_metadata.json",
            "result.json",
        } or len(files) != len(bundle.files):
            raise ImportConflict(
                "invalid_artifact_bundle", "Artifact bundle is incomplete"
            )
        if (
            sum(
                len(content)
                for name, content in files.items()
                if name != "source_metadata.json"
            )
            > MAX_ARTIFACT_BYTES
        ):
            raise ImportLimitExceeded(
                "artifact_size_limit", "Generated artifacts exceed the size limit"
            )
        stage = self.root / (".stage-" + uuid.uuid4().hex)
        try:
            # Owner lock lives outside the stage so Windows can atomically rename it.
            with self._lock(stage.name + ".owner", check_cancel):
                check_cancel()
                stage.mkdir()
                (stage / ".attachment-stage").write_text(
                    "medi-chat.pmda-import-stage.v1", encoding="ascii"
                )
                contents = {"source.xml": source, **files}
                for name, content in contents.items():
                    check_cancel()
                    self._write_file(stage / name, content)
                integrity = {
                    name: hashlib.sha256(content).hexdigest()
                    for name, content in contents.items()
                }
                self._write_file(
                    stage / "integrity.json",
                    json.dumps(integrity, sort_keys=True).encode("ascii"),
                )
                reused = self._publish(stage, target, check_cancel)
                return reused if reused is not None else bundle.result
        except OSError:
            raise ImportStorageError(
                "storage_error", "Import could not be saved"
            ) from None
        finally:
            self._remove_stage(stage)

    def cleanup(self) -> None:
        for stage in self.root.glob(".stage-*"):
            if (
                stage.is_symlink()
                or not stage.is_dir()
                or not (stage / ".attachment-stage").is_file()
            ):
                continue
            try:
                if (stage / ".attachment-stage").read_text(
                    encoding="ascii"
                ) != "medi-chat.pmda-import-stage.v1":
                    continue
                with self._lock(stage.name + ".owner", lambda: None, wait=False):
                    self._remove_stage(stage)
            except BlockingIOError:
                continue

    def _remove_stage(self, stage: Path) -> None:
        resolved = stage.resolve()
        if (
            stage.exists()
            and not stage.is_symlink()
            and resolved.is_relative_to(self.root)
            and stage.name.startswith(".stage-")
            and (stage / ".attachment-stage").is_file()
        ):
            shutil.rmtree(stage)

    def _write_file(self, path: Path, content: bytes) -> None:
        with path.open("xb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())

    def _publish(
        self, stage: Path, target: Path, check_cancel: Callable[[], None]
    ) -> ImportResult | None:
        with self._lock(target.parent.name + target.name + ".commit", check_cancel):
            check_cancel()
            if target.exists():
                # Read document identity from stage, then independently verify winner integrity.
                result = result_from_dict(
                    json.loads((stage / "result.json").read_bytes())
                )
                return replace(
                    self.read(DocumentId(result.document_id), result.source_sha256),
                    reused=True,
                )
            target.parent.mkdir(parents=True, exist_ok=True)
            check_cancel()
            # Never replace an existing version. Commit is the single atomic visibility point.
            os.rename(stage, target)
        return None

    @contextmanager
    def _lock(
        self, name: str, check_cancel: Callable[[], None], *, wait: bool = True
    ) -> Iterator[None]:
        path = self.root / ".locks" / name
        if not path.resolve().is_relative_to(self.root):
            raise ImportConflict(
                "storage_conflict", "Import storage path is inconsistent"
            )
        with path.open("a+b") as stream:
            if stream.seek(0, 2) == 0:
                stream.write(b"0")
                stream.flush()
            while True:
                check_cancel()
                try:
                    self._file_lock(stream, unlock=False)
                    break
                except OSError:
                    if not wait:
                        raise BlockingIOError from None
                    time.sleep(0.01)
            try:
                yield
            finally:
                self._file_lock(stream, unlock=True)

    @staticmethod
    def _file_lock(stream: BinaryIO, *, unlock: bool) -> None:
        stream.seek(0)
        if os.name == "nt":
            import msvcrt

            msvcrt.locking(
                stream.fileno(), msvcrt.LK_UNLCK if unlock else msvcrt.LK_NBLCK, 1
            )
        else:
            import fcntl

            fcntl.flock(
                stream.fileno(),
                fcntl.LOCK_UN if unlock else fcntl.LOCK_EX | fcntl.LOCK_NB,
            )
