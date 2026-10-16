"""SQLite公開世代と不変原本保存のadapter。"""

import hashlib
import json
import uuid
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from sqlalchemy import delete, insert, select, update
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.exc import SQLAlchemyError

from ...application.attachment_import.import_errors import (
    ImportCancelled,
    ImportConflict,
    ImportGone,
    ImportNotFound,
    ImportStorageError,
    InvalidAttachment,
)
from ...application.attachment_import.import_models import (
    DecodedAttachment,
    ImportResult,
)
from ...application.attachment_import.registration_contract import registration_version
from ...application.indexing.attachment_projection import (
    project_active_attachment,
    project_attachment,
)
from ...application.indexing.index_models import SourceSnapshot
from ...domain.attachment.exceptions import (
    MissingOrInvalidYjError,
    MissingRevisionError,
)
from ...domain.attachment.identifiers import (
    DocumentVersionId,
)
from ...domain.attachment.value_objects import (
    RegistrationVersion,
)
from ...domain.medicine.identifiers import YjCode
from ..index_payloads import build_index_document, build_index_unit
from ..json_payloads import parse_json_object
from ..package_insert_definitions.loader import get_package_insert_definitions
from ..pmda_xml.artifact_mapping import (
    PmdaArtifactEncoder,
    result_dict,
    result_from_dict,
)
from ..pmda_xml.decoder import PmdaXmlDecoder, SourceInformation
from ..pmda_xml.definition_settings import PmdaXmlSettings
from ..pmda_xml.registration_artifacts import encode_registered_units
from ..sources.attachment_import_store import FileAttachmentImportStore
from . import registration_schema as registration
from .index_writer import SqlAlchemyIndexWriter
from .registration_attempt import RegistrationAttempt
from .registration_lock import registration_lock
from .revision_selection import assign_latest, validate_active_revisions
from .sqlite_engine import create_sqlite_engine


@dataclass(frozen=True)
class RegistrationInput:
    decoded: DecodedAttachment
    source: bytes
    # Explicit initial-copy inventory, never a recursive ownership scan.
    owned_files: tuple[Path, ...] = ()
    source_path: Path | None = None
    document_payload: dict[str, Any] | None = None


def _dump(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _load_active(connection: Connection) -> dict[YjCode, RegistrationVersion]:
    records = {
        row["version_id"]: dict(row)
        for row in connection.execute(
            select(registration.registration_receipts)
        ).mappings()
    }
    assigned = {
        row.yj_code: row.version_id
        for row in connection.execute(select(registration.active_registrations))
    }
    return validate_active_revisions(records, assigned)


class SqliteRegistrationPublisher:
    def __init__(
        self,
        index_path: Path,
        store: FileAttachmentImportStore,
        *,
        fault: Callable[[str], None] = lambda phase: None,
        allowed_roots: tuple[Path, ...] = (),
        xml_settings: PmdaXmlSettings | None = None,
        engine: Engine | None = None,
    ) -> None:
        self.index_path = index_path.resolve()
        self._shared_engine = engine
        self._xml_settings = (
            xml_settings
            if xml_settings is not None
            else get_package_insert_definitions().xml_settings
        )
        self.store = store
        self.fault = fault
        self.allowed_roots = (store.root, *(root.resolve() for root in allowed_roots))

    def _lock(self, check_cancel: Callable[[], None]):
        return registration_lock(self.index_path, check_cancel)

    def _engine(self):
        if self._shared_engine is not None:
            return self._shared_engine
        return create_sqlite_engine("sqlite:///" + self.index_path.as_posix())

    def _dispose_engine(self, engine: Engine) -> None:
        # Injected pools belong to the composition root, not individual operations.
        if engine is not self._shared_engine:
            engine.dispose()

    def _owned(self, paths: tuple[Path, ...]) -> list[dict[str, str]]:
        files = []
        for path in paths:
            root = next(
                (
                    root
                    for root in self.allowed_roots
                    if path.absolute().is_relative_to(root)
                ),
                None,
            )
            if root is None or self._unsafe(path, root):
                raise ImportStorageError(
                    "unsafe_owned_file", "Owned artifact is unsafe", phase="artifact"
                )
            files.append(
                {
                    "path": str(path.absolute()),
                    "root": str(root),
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                }
            )
        return files

    @staticmethod
    def _unsafe(path: Path, root: Path) -> bool:
        if not path.absolute().is_relative_to(root) or ".." in path.parts:
            return True
        return any(
            parent.is_symlink()
            for parent in (path, *path.parents)
            if parent.is_relative_to(root)
        ) or not path.resolve().is_relative_to(root)

    def publish(
        self,
        decoded: DecodedAttachment,
        source: bytes,
        *,
        check_cancel: Callable[[], None] = lambda: None,
    ) -> ImportResult:
        return self.publish_inputs(
            (RegistrationInput(decoded, source),), check_cancel=check_cancel
        )[0]

    def publish_inputs(
        self,
        inputs: tuple[RegistrationInput, ...],
        *,
        initial: bool = False,
        check_cancel: Callable[[], None] = lambda: None,
    ) -> tuple[ImportResult, ...]:
        from ..composition.index_verifier import verify_schema_readiness
        from .sqlite_recovery import recover_sqlite_journal

        recover_sqlite_journal(self.index_path)
        verify_schema_readiness(self.index_path)
        try:
            for item in inputs:
                registration_version(item.decoded.document)
        except MissingOrInvalidYjError:
            raise InvalidAttachment(
                "missing_or_invalid_yj",
                "Every listed product must have a valid YJ code",
                phase="validation",
            ) from None
        except MissingRevisionError as exc:
            raise InvalidAttachment(
                "missing_revision",
                "A revision month is required to select the latest document",
                phase="validation",
            ) from exc
        engine = self._engine()
        phase = "artifact"
        attempt: RegistrationAttempt | None = None
        published = False
        try:
            with self._lock(check_cancel):
                attempt = RegistrationAttempt(self.store.root)
                with engine.connect() as connection:
                    before = _load_active(connection)
                    records = {
                        row["version_id"]: dict(row)
                        for row in connection.execute(
                            select(registration.registration_receipts)
                        ).mappings()
                    }
                    payloads = dict(
                        connection.execute(
                            select(
                                registration.registration_version_artifacts.c.version_id,
                                registration.registration_version_artifacts.c.document_payload_json,
                            )
                        ).all()
                    )
                    for version_id, payload in payloads.items():
                        records[version_id]["document_payload_json"] = payload
                after = before
                newly = []
                requested = []
                seen = set(records)
                for item in inputs:
                    identity = registration_version(
                        item.decoded.document
                    ).version_id.value
                    requested.append((identity, identity in seen))
                    seen.add(identity)
                ordered = sorted(
                    inputs,
                    key=lambda item: (
                        registration_version(item.decoded.document).revised_at.value
                    ),
                    reverse=True,
                )
                # Reject a batch conflict before writing any artifact. Newest first
                # also avoids treating ambiguity among obsolete versions as latest.
                planned = dict(before)
                for item in ordered:
                    planned = assign_latest(
                        planned, registration_version(item.decoded.document)
                    )
                for item in inputs:
                    version = registration_version(item.decoded.document)
                    if version.version_id.value in records:
                        continue
                    check_cancel()
                    info = item.decoded.source_info
                    if not isinstance(info, SourceInformation):
                        raise InvalidAttachment(
                            "invalid_source_information",
                            "Source information is invalid",
                        )
                    bundle = PmdaArtifactEncoder().encode(
                        item.decoded.document,
                        project_attachment(item.decoded.document),
                        info,
                    )
                    if item.source_path is None:
                        target = self.store._target(
                            bundle.document_id, bundle.source_sha256
                        )
                        if not target.exists():
                            contents = {
                                "source.xml": item.source,
                                **{file.name: file.content for file in bundle.files},
                            }
                            integrity = json.dumps(
                                {
                                    name: hashlib.sha256(content).hexdigest()
                                    for name, content in contents.items()
                                },
                                sort_keys=True,
                            ).encode("ascii")
                            for name, content in {
                                **contents,
                                "integrity.json": integrity,
                                ".attachment-stage": b"medi-chat.pmda-import-stage.v1",
                            }.items():
                                attempt.claim(target / name, content)
                        self.store.commit(
                            bundle, item.source, check_cancel=check_cancel
                        )
                        target = self.store._target(
                            bundle.document_id, bundle.source_sha256
                        )
                        source_path = target / "source.xml"
                        owned_paths = tuple(
                            target / name
                            for name in (
                                "source.xml",
                                "document.json",
                                "search_units.jsonl",
                                "validation.json",
                                "source_metadata.json",
                                "result.json",
                                "integrity.json",
                                ".attachment-stage",
                            )
                        )
                    else:
                        source_path = item.source_path
                        owned_paths = item.owned_files
                        if (
                            source_path not in owned_paths
                            or source_path.read_bytes() != item.source
                        ):
                            raise ImportConflict(
                                "source_hash_conflict",
                                "Initial source inventory is inconsistent",
                                phase="artifact",
                            )
                    files = self._owned(owned_paths)
                    previous = after
                    # Receipts follow input order; only the prevalidated batch
                    # winners may change publication, even for obsolete ties.
                    after = {
                        **after,
                        **{
                            code: version
                            for code in version.yj_codes
                            if planned[code].version_id == version.version_id
                        },
                    }
                    replaced_codes = frozenset(
                        code
                        for code in version.yj_codes
                        if code in previous
                        and after[code].version_id != previous[code].version_id
                    )
                    cleanup_targets = sorted(
                        {previous[code].version_id.value for code in replaced_codes}
                    )
                    record = {
                        "version_id": version.version_id.value,
                        "document_id": version.document_id.value,
                        "source_sha256": version.source_sha256.value,
                        "sequence": max(
                            (row["sequence"] for row in records.values()), default=0
                        )
                        + 1,
                        "yj_codes_json": _dump(
                            sorted(code.value for code in version.yj_codes)
                        ),
                        "replaced_json": _dump(
                            sorted(code.value for code in replaced_codes)
                        ),
                        "result_json": _dump(result_dict(bundle.result)),
                        "document_payload_json": _dump(
                            item.document_payload or info.document
                        ),
                        "source_path": str(source_path.absolute()),
                        "files_json": _dump(files),
                        "cleanup_targets_json": _dump(cleanup_targets),
                        "artifacts_deleted": 0,
                        "cleanup_reason": "",
                    }
                    records[version.version_id.value] = record
                    newly.append(record)
                    self.fault("artifacts")
                if newly:
                    changed = after != before
                    snapshot: SourceSnapshot | None = None
                    generation_id: str | None = None
                    generation_files: list[dict[str, str]] = []
                    if changed:
                        phase = "projection"
                        generation_id = uuid.uuid4().hex
                        snapshot, generation_files = self._build(
                            after, records, generation_id, check_cancel, attempt
                        )
                        self.fault("index")
                        if len(
                            {medicine.yj_code for medicine in snapshot.medicines}
                        ) != len(snapshot.medicines):
                            raise ValueError("candidate YJ must be unique")
                        self.fault("candidates")
                        check_cancel()
                    phase = "publication"
                    with engine.begin() as connection:
                        self.fault("transaction")
                        for record in newly:
                            receipt = dict(record)
                            payload = receipt.pop("document_payload_json")
                            connection.execute(
                                insert(registration.registration_receipts), receipt
                            )
                            connection.execute(
                                insert(registration.registration_version_artifacts),
                                {
                                    "version_id": record["version_id"],
                                    "document_payload_json": payload,
                                },
                            )
                            for file in json.loads(record["files_json"]):
                                connection.execute(
                                    insert(registration.registration_owned_files),
                                    {
                                        "version_id": record["version_id"],
                                        "file_id": file["path"],
                                        "root": file["root"],
                                        "sha256": file["sha256"],
                                    },
                                )
                        if changed:
                            assert snapshot is not None and generation_id is not None
                            connection.execute(
                                delete(registration.active_registrations)
                            )
                            connection.execute(
                                insert(registration.active_registrations),
                                [
                                    {
                                        "yj_code": code.value,
                                        "version_id": version.version_id.value,
                                    }
                                    for code, version in after.items()
                                ],
                            )
                            serialized = self._snapshot_value(snapshot, after)
                            connection.execute(
                                insert(registration.registration_generations),
                                {
                                    "generation_id": generation_id,
                                    "snapshot_json": _dump(serialized),
                                    "fingerprint": snapshot.fingerprint,
                                    "files_json": _dump(generation_files),
                                },
                            )
                            SqlAlchemyIndexWriter(engine).replace_in_transaction(
                                connection, snapshot
                            )
                            connection.execute(delete(registration.registration_state))
                            connection.execute(
                                insert(registration.registration_state),
                                {"singleton": 1, "generation_id": generation_id},
                            )
                        self.fault("commit")
                        check_cancel()
                    published = True
                # Once published, cancellation never rolls the registration back.
                self.fault("after_commit")
                try:
                    check_cancel()
                except ImportCancelled:
                    pass
                else:
                    self._cleanup(engine)
                return tuple(
                    self._result(engine, version_id, reused=reused)
                    for version_id, reused in requested
                )
        except (OSError, SQLAlchemyError) as exc:
            raise ImportStorageError(
                "registration_failed",
                "Registration could not be published",
                phase=phase,
            ) from exc
        finally:
            if attempt is not None:
                with suppress(OSError):
                    if published:
                        attempt.path.unlink(missing_ok=True)
                    else:
                        attempt.finish()
            self._dispose_engine(engine)

    def _build(
        self,
        active_versions: dict[YjCode, RegistrationVersion],
        records: dict[str, dict[str, Any]],
        generation_id: str,
        check_cancel: Callable[[], None],
        attempt: RegistrationAttempt,
    ) -> tuple[SourceSnapshot, list[dict[str, str]]]:
        active: dict[str, set[YjCode]] = {}
        for code, version in active_versions.items():
            active.setdefault(version.version_id.value, set()).add(code)
        documents = {}
        medicines = []
        units = []
        fingerprint = hashlib.sha256(
            _dump(
                {
                    version: sorted(code.value for code in codes)
                    for version, codes in sorted(active.items())
                }
            ).encode()
        )
        generation_dir = self.store.root / "generations" / generation_id
        generation_dir.mkdir(parents=True)
        paths = []
        for version_id, codes in sorted(active.items()):
            check_cancel()
            record = records[version_id]
            source = Path(record["source_path"]).read_bytes()
            if hashlib.sha256(source).hexdigest() != record["source_sha256"]:
                raise ImportConflict(
                    "published_artifact_corrupt",
                    "Published source is inconsistent",
                    phase="projection",
                )
            decoded = PmdaXmlDecoder(xml_settings=self._xml_settings).decode(source)
            if not isinstance(decoded.source_info, SourceInformation):
                raise ValueError("invalid source information")
            projection = project_active_attachment(decoded.document, frozenset(codes))
            content = encode_registered_units(decoded.document, projection)
            path = generation_dir / (
                hashlib.sha256(version_id.encode()).hexdigest() + ".jsonl"
            )
            attempt.claim(path, content)
            self.store._write_file(path, content)
            paths.append(path)
            document, products = build_index_document(
                parse_json_object(record["document_payload_json"])
            )
            documents.setdefault(document.document_id, document)
            medicines.extend(
                product for product in products if product.yj_code in codes
            )
            units.extend(
                build_index_unit(parse_json_object(line), document.document_id)
                for line in content.decode("utf-8").splitlines()
            )
            for file in json.loads(record["files_json"]):
                p = Path(file["path"])
                root = Path(file["root"])
                if root not in self.allowed_roots or self._unsafe(p, root):
                    raise ImportConflict(
                        "published_artifact_corrupt",
                        "Published file path is unsafe",
                        phase="projection",
                    )
                actual = hashlib.sha256(p.read_bytes()).hexdigest()
                if actual != file["sha256"]:
                    raise ImportConflict(
                        "published_artifact_corrupt",
                        "Published artifact is inconsistent",
                        phase="projection",
                    )
                fingerprint.update(file["path"].encode())
                fingerprint.update(actual.encode())
            fingerprint.update(version_id.encode())
            fingerprint.update(content)
        return SourceSnapshot(
            tuple(documents.values()),
            tuple(medicines),
            tuple(units),
            "content-v1:" + fingerprint.hexdigest(),
        ), self._owned(tuple(paths))

    @staticmethod
    def _snapshot_value(
        snapshot: SourceSnapshot, active_versions: dict[YjCode, RegistrationVersion]
    ) -> dict[str, Any]:
        return {
            "version_ids": sorted(
                {version.version_id.value for version in active_versions.values()}
            ),
            "documents": [
                {"document_id": doc.document_id, "payload": doc.payload}
                for doc in snapshot.documents
            ],
            "units": [unit.payload for unit in snapshot.units],
            "medicines": [
                {
                    "document_id": medicine.document_id.value,
                    "yj_code": medicine.yj_code.value if medicine.yj_code else None,
                    "brand_name": medicine.brand_name,
                    "generic_name": medicine.generic_name,
                    "english_name": medicine.english_name,
                    "hiragana_name": medicine.hiragana_name,
                    "pmda_url": medicine.pmda_url.value,
                    "revision": medicine.revision.to_dict(),
                }
                for medicine in snapshot.medicines
            ],
        }

    def _cleanup(self, engine) -> None:
        from .process_identity import process_identity

        with engine.begin() as connection:
            for lease in connection.execute(
                select(registration.generation_leases)
            ).mappings():
                try:
                    identity = process_identity(lease["owner_pid"])
                except OSError:
                    continue
                if identity != lease["owner_start"]:
                    connection.execute(
                        delete(registration.generation_leases).where(
                            registration.generation_leases.c.lease_id
                            == lease["lease_id"]
                        )
                    )
        with engine.connect() as connection:
            active_versions = _load_active(connection)
            lease_generations = set(
                connection.execute(
                    select(registration.generation_leases.c.generation_id)
                ).scalars()
            )
            protected = set()
            for snapshot in connection.execute(
                select(registration.registration_generations.c.snapshot_json).where(
                    registration.registration_generations.c.generation_id.in_(
                        lease_generations
                    )
                )
            ).scalars():
                protected.update(
                    DocumentVersionId(version)
                    for version in json.loads(snapshot)["version_ids"]
                )
            records = {
                row["version_id"]: dict(row)
                for row in connection.execute(
                    select(registration.registration_receipts)
                ).mappings()
            }
            protected_versions = {
                version.version_id for version in active_versions.values()
            } | protected
            eligible = frozenset(
                DocumentVersionId(identity)
                for identity, record in records.items()
                if not record["artifacts_deleted"]
                and DocumentVersionId(identity) not in protected_versions
            )
            # File ownership/leases are storage lifecycle rules, not a document aggregate.
            removable = frozenset(
                file["path"]
                for identity, record in records.items()
                if DocumentVersionId(identity) in eligible
                for file in json.loads(record["files_json"])
            )
            retained = frozenset(
                file["path"]
                for identity, record in records.items()
                if DocumentVersionId(identity) not in eligible
                and not record["artifacts_deleted"]
                for file in json.loads(record["files_json"])
            )
            removable -= retained
            owned = {
                (row.version_id, row.file_id): (row.root, row.sha256)
                for row in connection.execute(
                    select(registration.registration_owned_files)
                )
            }
        inactive_protected = protected.difference(
            version.version_id for version in active_versions.values()
        )
        if inactive_protected:
            with engine.begin() as connection:
                connection.execute(
                    update(registration.registration_receipts)
                    .where(
                        registration.registration_receipts.c.version_id.in_(
                            version.value for version in inactive_protected
                        )
                    )
                    .values(cleanup_reason="lease_active")
                )
        for version_id in eligible:
            complete = True
            reason = ""
            for file in json.loads(records[version_id.value]["files_json"]):
                path = Path(file["path"])
                root = Path(file["root"])
                if owned.get((version_id.value, file["path"])) != (
                    file["root"],
                    file["sha256"],
                ):
                    complete = False
                    reason = "unowned_file"
                    continue
                if root not in self.allowed_roots or self._unsafe(path, root):
                    complete = False
                    reason = "unsafe_path"
                    continue
                if file["path"] not in removable:
                    continue
                try:
                    if path.exists():
                        if (
                            hashlib.sha256(path.read_bytes()).hexdigest()
                            != file["sha256"]
                        ):
                            complete = False
                            reason = reason or "artifact_changed"
                            continue
                        path.unlink()
                        self.fault("cleanup")
                except OSError:
                    complete = False
                    reason = reason or "io_error"
            with engine.begin() as connection:
                if complete:
                    connection.execute(
                        delete(registration.registration_version_artifacts).where(
                            registration.registration_version_artifacts.c.version_id
                            == version_id.value
                        )
                    )
                connection.execute(
                    update(registration.registration_receipts)
                    .where(
                        registration.registration_receipts.c.version_id
                        == version_id.value
                    )
                    .values(artifacts_deleted=int(complete), cleanup_reason=reason)
                )
        # Old derived generations are private after publication; retain leased ones.
        with engine.connect() as connection:
            current = connection.execute(
                select(registration.registration_state.c.generation_id)
            ).scalar_one_or_none()
            obsolete = [
                dict(row)
                for row in connection.execute(
                    select(registration.registration_generations)
                ).mappings()
                if row["generation_id"] != current
                and row["generation_id"] not in lease_generations
            ]
        for generation in obsolete:
            complete = True
            for file in json.loads(generation["files_json"]):
                path = Path(file["path"])
                root = self.store.root
                if (
                    Path(file["root"]) != root
                    or self._unsafe(path, root)
                    or path.parent != root / "generations" / generation["generation_id"]
                ):
                    complete = False
                    continue
                try:
                    if path.exists():
                        if (
                            hashlib.sha256(path.read_bytes()).hexdigest()
                            != file["sha256"]
                        ):
                            complete = False
                            continue
                        path.unlink()
                except OSError:
                    complete = False
            if complete:
                with engine.begin() as connection:
                    connection.execute(
                        delete(registration.registration_generations).where(
                            registration.registration_generations.c.generation_id
                            == generation["generation_id"]
                        )
                    )

        with engine.connect() as connection:
            referenced = {
                file["path"]
                for table in (
                    registration.registration_receipts,
                    registration.registration_generations,
                )
                for payload in connection.execute(select(table.c.files_json)).scalars()
                for file in json.loads(payload)
            }
        RegistrationAttempt.recover(self.store.root, referenced)

    def _result(
        self, engine, version_id: str, *, reused: bool = False, get: bool = False
    ) -> ImportResult:
        with engine.connect() as connection:
            record = (
                connection.execute(
                    select(registration.registration_receipts).where(
                        registration.registration_receipts.c.version_id == version_id
                    )
                )
                .mappings()
                .first()
            )
            if record is None:
                raise ImportNotFound(
                    "import_not_found",
                    "Registered import does not exist",
                    phase="publication",
                )
            if get and record["artifacts_deleted"]:
                raise ImportGone(
                    "version_deleted",
                    "Registered version artifacts have been deleted",
                    phase="publication",
                )
            active = tuple(
                sorted(
                    connection.execute(
                        select(registration.active_registrations.c.yj_code).where(
                            registration.active_registrations.c.version_id == version_id
                        )
                    ).scalars()
                )
            )
            generation_id = connection.execute(
                select(registration.registration_state.c.generation_id)
            ).scalar_one()
            target_rows = connection.execute(
                select(
                    registration.registration_receipts.c.version_id,
                    registration.registration_receipts.c.artifacts_deleted,
                    registration.registration_receipts.c.cleanup_reason,
                ).where(
                    registration.registration_receipts.c.version_id.in_(
                        json.loads(record["cleanup_targets_json"])
                    ),
                    registration.registration_receipts.c.version_id.not_in(
                        select(registration.active_registrations.c.version_id)
                    ),
                )
            ).all()
        original = result_from_dict(json.loads(record["result_json"]))
        pending = tuple(
            (version, reason or "cleanup_required")
            for version, deleted, reason in sorted(target_rows)
            if not deleted
        )
        deleted = tuple(
            version for version, deleted, reason in sorted(target_rows) if deleted
        )
        return replace(
            original,
            reused=reused,
            status=("registered_cleanup_pending" if pending else "registered")
            if active
            else "superseded",
            search_index_updated=bool(active),
            generation_id=generation_id,
            registration_sequence=record["sequence"],
            active_yj_codes=active,
            replaced_yj_codes=tuple(json.loads(record["replaced_json"])),
            deleted_version_ids=deleted,
            cleanup_pending=pending,
            artifacts_deleted=bool(record["artifacts_deleted"]),
        )

    def read_result(self, document_id: str, digest: str) -> ImportResult:
        engine = self._engine()
        try:
            return self._result(engine, f"{document_id}:{digest}", get=True)
        finally:
            self._dispose_engine(engine)

    def recover(self) -> None:
        from ..sources.registration_source import read_registered_snapshot
        from .sqlite_recovery import recover_sqlite_journal

        engine = self._engine()
        try:
            with self._lock(lambda: None):
                recover_sqlite_journal(self.index_path, locked=True)
                with engine.connect() as connection:
                    _load_active(connection)
                if read_registered_snapshot(self.index_path) is None:
                    raise RuntimeError("initial_registration_required")
                self._cleanup(engine)
        finally:
            self._dispose_engine(engine)
