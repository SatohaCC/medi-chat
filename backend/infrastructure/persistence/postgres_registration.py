"""PostgreSQL publication adapter; transactions own all retained payloads."""

import hashlib
import json
import uuid
from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import PurePosixPath
from typing import Any, TypedDict

from sqlalchemy import Text, cast, delete, func, insert, select, text, update
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from backend.application.attachment_import.import_contracts import (
    AttachmentArtifactEncoder,
)
from backend.application.attachment_import.import_errors import (
    ImportCancelled,
    ImportConflict,
    ImportGone,
    ImportLimitExceeded,
    ImportNotFound,
    ImportStorageError,
    InvalidAttachment,
)
from backend.application.attachment_import.import_models import (
    DecodedAttachment,
    ImportPage,
    ImportResult,
    ImportSummary,
)
from backend.application.attachment_import.registration_contract import (
    registration_version,
)
from backend.application.indexing.attachment_projection import (
    project_attachment,
)
from backend.domain.attachment.exceptions import (
    MissingOrInvalidYjError,
    MissingRevisionError,
)
from backend.domain.attachment.identifiers import DocumentId
from backend.domain.attachment.primitives import AttachmentSha256, RevisionYearMonth
from backend.domain.attachment.value_objects import RegistrationVersion
from backend.domain.foundation.json_types import JsonValue
from backend.domain.medicine.identifiers import YjCode
from backend.infrastructure.index_payloads import (
    MAX_ARTIFACT_BYTES,
    result_dict,
    result_from_dict,
)

from . import postgres_schema as s
from .attachment_document_mapping import document_to_payload
from .postgres_integrity import PROJECTION_FINGERPRINT
from .postgres_projection import projection_records
from .revision_selection import assign_latest


@dataclass(frozen=True)
class FigureInput:
    logical_name: str
    media_type: str
    content: bytes


@dataclass(frozen=True)
class PostgresRegistrationInput:
    decoded: DecodedAttachment
    source: bytes
    figures: tuple[FigureInput, ...] = ()


class _NewVersionPayload(TypedDict):
    structure: dict[str, Any]
    catalogue: dict[str, Any]
    source: bytes
    filename: str
    validation: dict[str, Any]
    figures: tuple[FigureInput, ...]
    units: list[dict[str, JsonValue]]
    unit_products: list[dict[str, str]]
    result: ImportResult


@dataclass(frozen=True)
class _PreparedInput:
    version: RegistrationVersion
    payload: _NewVersionPayload | None


class PostgresRegistrationPublisher:
    def __init__(
        self,
        engine: Engine,
        *,
        encoder: AttachmentArtifactEncoder,
        fault: Callable[[str], None] = lambda phase: None,
    ):
        self.engine = engine
        self.encoder = encoder
        self.fault = fault

    def publish(
        self,
        decoded: DecodedAttachment,
        source: bytes,
        *,
        check_cancel: Callable[[], None] = lambda: None,
    ) -> ImportResult:
        return self.publish_inputs(
            (PostgresRegistrationInput(decoded, source),), check_cancel=check_cancel
        )[0]

    def publish_inputs(
        self,
        inputs: tuple[PostgresRegistrationInput, ...],
        *,
        initial: bool = False,
        check_cancel: Callable[[], None] = lambda: None,
    ) -> tuple[ImportResult, ...]:
        check_cancel()
        error_phase = "publication"
        try:
            versions = tuple(self._version(item) for item in inputs)
            with self.engine.connect() as connection:
                known = set(
                    connection.execute(
                        select(s.receipts.c.version_id).where(
                            s.receipts.c.version_id.in_(
                                version.version_id.value for version in versions
                            )
                        )
                    ).scalars()
                )
            prepared = [
                _PreparedInput(version, None)
                if version.version_id.value in known
                else self._prepare(item)
                for item, version in zip(inputs, versions, strict=True)
            ]
            self.fault("prepared")
            requested = []
            with self.engine.begin() as connection:
                state = (
                    connection.execute(select(s.state).with_for_update())
                    .mappings()
                    .one()
                )
                self.fault("locked")
                records = {
                    row["version_id"]: row
                    for row in connection.execute(select(s.receipts)).mappings()
                }
                if initial and records:
                    raise ImportConflict(
                        "already_initialized",
                        "Initial registration requires an empty database",
                        phase="publication",
                    )
                before = {
                    YjCode(row.yj_code): self._stored_version(records[row.version_id])
                    for row in connection.execute(select(s.active))
                }
                planned = dict(before)
                for item in sorted(
                    prepared,
                    key=lambda item: item.version.revised_at.value,
                    reverse=True,
                ):
                    if item.version.version_id.value not in records:
                        planned = assign_latest(planned, item.version)
                after = dict(before)
                sequence = state["sequence"]
                for item in prepared:
                    version = item.version
                    identity = version.version_id.value
                    existing = connection.execute(
                        select(s.receipts.c.version_id).where(
                            s.receipts.c.version_id == identity
                        )
                    ).first()
                    requested.append((identity, existing is not None))
                    if existing:
                        continue
                    payload = item.payload
                    if payload is None:
                        raise ImportConflict(
                            "receipt_identity_changed",
                            "Known receipt identity is unavailable",
                            phase="publication",
                        )
                    previous = dict(after)
                    after.update(
                        {
                            code: version
                            for code in version.yj_codes
                            if planned[code].version_id == version.version_id
                        }
                    )
                    replaced = sorted(
                        code.value
                        for code in version.yj_codes
                        if code in previous
                        and after[code].version_id != previous[code].version_id
                    )
                    cleanup_targets = sorted(
                        {previous[YjCode(code)].version_id.value for code in replaced}
                    )
                    sequence += 1
                    connection.execute(
                        insert(s.receipts),
                        {
                            "version_id": identity,
                            "document_id": version.document_id.value,
                            "source_sha256": version.source_sha256.value,
                            "sequence": sequence,
                            "revised_at": version.revised_at.value,
                            "yj_codes": sorted(code.value for code in version.yj_codes),
                            "replaced": replaced,
                            "cleanup_targets": cleanup_targets,
                            "result": result_dict(payload["result"]),
                            "artifacts_deleted": False,
                            "cleanup_reason": "",
                        },
                    )
                    self.fault("receipt")
                    error_phase = "artifact"
                    connection.execute(
                        insert(s.versions),
                        {
                            "version_id": identity,
                            "structure": payload["structure"],
                            "catalogue": payload["catalogue"],
                            "payload_fingerprint": "",
                            "projection_fingerprint": "",
                            "source": payload["source"],
                            "byte_size": len(payload["source"]),
                            "filename": payload["filename"],
                            "validation": payload["validation"],
                        },
                    )
                    connection.execute(
                        update(s.versions)
                        .where(s.versions.c.version_id == identity)
                        .values(
                            payload_fingerprint=func.md5(
                                cast(s.versions.c.structure, Text)
                                + cast(s.versions.c.catalogue, Text)
                            )
                        )
                    )
                    self.fault("source")
                    for figure in payload["figures"]:
                        connection.execute(
                            insert(s.assets),
                            {
                                "version_id": identity,
                                "logical_name": figure.logical_name,
                                "media_type": figure.media_type,
                                "source_sha256": hashlib.sha256(
                                    figure.content
                                ).hexdigest(),
                                "byte_size": len(figure.content),
                                "content": figure.content,
                            },
                        )
                    self.fault("assets")
                    error_phase = "projection"
                    for unit in payload["units"]:
                        connection.execute(
                            insert(s.units), {"version_id": identity, **unit}
                        )
                    self.fault("units")
                    for product in payload["unit_products"]:
                        connection.execute(
                            insert(s.unit_products), {"version_id": identity, **product}
                        )
                    connection.execute(
                        text(
                            f"UPDATE attachment_versions SET projection_fingerprint={PROJECTION_FINGERPRINT} WHERE version_id=:identity"
                        ),
                        {"identity": identity},
                    )
                    error_phase = "publication"
                if after != before:
                    generation = uuid.uuid4().hex
                    assignment = {
                        code.value: version.version_id.value
                        for code, version in after.items()
                    }
                    fingerprint = hashlib.sha256(
                        json.dumps(assignment, sort_keys=True).encode()
                    ).hexdigest()
                    connection.execute(
                        insert(s.generations),
                        {"generation_id": generation, "fingerprint": fingerprint},
                    )
                    connection.execute(delete(s.active))
                    connection.execute(
                        insert(s.active),
                        [
                            {"yj_code": code, "version_id": identity}
                            for code, identity in assignment.items()
                        ],
                    )
                    self.fault("active")
                    connection.execute(
                        insert(s.memberships),
                        [
                            {
                                "generation_id": generation,
                                "yj_code": code,
                                "version_id": identity,
                            }
                            for code, identity in assignment.items()
                        ],
                    )
                    connection.execute(
                        update(s.state).values(
                            generation_id=generation, sequence=sequence
                        )
                    )
                    self.fault("generation")
                else:
                    connection.execute(update(s.state).values(sequence=sequence))
                self.fault("before_commit")
                check_cancel()
            self.fault("after_commit")
            try:
                check_cancel()
            except ImportCancelled:
                pass
            else:
                self._cleanup_safe()
            return tuple(
                self._result(identity, reused=reused) for identity, reused in requested
            )
        except (SQLAlchemyError, OSError) as error:
            raise ImportStorageError(
                "registration_failed",
                "Registration could not be published",
                phase=error_phase,
            ) from error

    @staticmethod
    def _stored_version(record):
        return RegistrationVersion(
            document_id=DocumentId(record["document_id"]),
            source_sha256=AttachmentSha256(record["source_sha256"]),
            yj_codes=frozenset(YjCode(code) for code in record["yj_codes"]),
            revised_at=RevisionYearMonth(record["revised_at"]),
        )

    @staticmethod
    def _version(item: PostgresRegistrationInput) -> RegistrationVersion:
        try:
            version = registration_version(item.decoded.document)
        except MissingOrInvalidYjError:
            raise InvalidAttachment(
                "missing_or_invalid_yj",
                "Every listed product must have a valid YJ code",
                phase="validation",
            ) from None
        except MissingRevisionError:
            raise InvalidAttachment(
                "missing_revision",
                "A revision month is required to select the latest document",
                phase="validation",
            ) from None
        if hashlib.sha256(item.source).hexdigest() != version.source_sha256.value:
            raise InvalidAttachment(
                "source_hash_conflict",
                "Source bytes do not match the decoded document",
                phase="validation",
            )
        return version

    def _prepare(self, item: PostgresRegistrationInput) -> _PreparedInput:
        version = self._version(item)
        for figure in item.figures:
            name = PurePosixPath(figure.logical_name)
            if (
                name.is_absolute()
                or ".." in name.parts
                or "\\" in figure.logical_name
                or ":" in figure.logical_name
                or not figure.logical_name
                or not figure.media_type
            ):
                raise InvalidAttachment(
                    "unsafe_figure", "Figure name is unsafe", phase="validation"
                )
        projected = project_attachment(item.decoded.document)
        bundle = self.encoder.encode(
            item.decoded.document, projected, item.decoded.source_info
        )
        if (
            sum(
                len(file.content)
                for file in bundle.files
                if file.name != "source_metadata.json"
            )
            > MAX_ARTIFACT_BYTES
        ):
            raise ImportLimitExceeded(
                "artifact_size_limit", "Generated artifacts exceed the size limit"
            )
        artifacts = {file.name: file.content for file in bundle.files}
        metadata = json.loads(artifacts["document.json"])
        units, products = projection_records(item.decoded.document)
        return _PreparedInput(
            version,
            {
                "structure": document_to_payload(item.decoded.document),
                "catalogue": {
                    "document": metadata["document"],
                    "source": {
                        "pmda_url": metadata["source"]["pmda_url"],
                        "sha256": version.source_sha256.value,
                    },
                },
                "unit_products": products,
                "source": item.source,
                "filename": metadata["source"]["file"],
                "validation": json.loads(artifacts["validation.json"]),
                "figures": item.figures,
                "units": units,
                "result": bundle.result,
            },
        )

    def read_result(self, document_id: str, digest: str) -> ImportResult:
        return self._result(f"{document_id}:{digest}", get=True)

    def replay_result(self, document_id: str, digest: str) -> ImportResult:
        """Replay a retained receipt even after its original payload was reclaimed."""
        return self._result(f"{document_id}:{digest}", reused=True)

    def list_imports(self, *, limit: int, offset: int) -> ImportPage:
        try:
            with self.engine.connect().execution_options(
                isolation_level="REPEATABLE READ"
            ) as connection:
                connection.execute(text("SET TRANSACTION READ ONLY"))
                total = connection.execute(
                    select(func.count()).select_from(s.receipts)
                ).scalar_one()
                records = (
                    connection.execute(
                        select(s.receipts, s.versions.c.filename)
                        .outerjoin(
                            s.versions,
                            s.versions.c.version_id == s.receipts.c.version_id,
                        )
                        .order_by(s.receipts.c.sequence.desc())
                        .limit(limit)
                        .offset(offset)
                    )
                    .mappings()
                    .all()
                )
                active: dict[str, list[str]] = {}
                if records:
                    for row in connection.execute(
                        select(s.active.c.version_id, s.active.c.yj_code)
                        .where(
                            s.active.c.version_id.in_(
                                [r["version_id"] for r in records]
                            )
                        )
                        .order_by(s.active.c.yj_code.collate("C"))
                    ):
                        active.setdefault(row.version_id, []).append(row.yj_code)
                return ImportPage(
                    items=tuple(
                        ImportSummary(
                            document_id=r["document_id"],
                            source_sha256=r["source_sha256"],
                            filename=r["filename"],
                            registration_sequence=r["sequence"],
                            revised_at=r["revised_at"],
                            products=result_from_dict(r["result"]).products,
                            active_yj_codes=tuple(active.get(r["version_id"], ())),
                            artifacts_deleted=r["artifacts_deleted"],
                        )
                        for r in records
                    ),
                    total_count=total,
                )
        except SQLAlchemyError:
            raise ImportStorageError(
                "import_list_unavailable",
                "取り込み一覧を取得できません。",
                phase="publication",
            ) from None

    def _result(
        self, identity: str, *, reused: bool = False, get: bool = False
    ) -> ImportResult:
        with self.engine.connect().execution_options(
            isolation_level="REPEATABLE READ"
        ) as connection:
            connection.execute(text("SET TRANSACTION READ ONLY"))
            record = (
                connection.execute(
                    select(s.receipts).where(s.receipts.c.version_id == identity)
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
                        select(s.active.c.yj_code).where(
                            s.active.c.version_id == identity
                        )
                    ).scalars()
                )
            )
            generation = connection.execute(
                select(s.state.c.generation_id)
            ).scalar_one()
            targets = connection.execute(
                select(
                    s.receipts.c.version_id,
                    s.receipts.c.artifacts_deleted,
                    s.receipts.c.cleanup_reason,
                ).where(
                    s.receipts.c.version_id.in_(record["cleanup_targets"]),
                    s.receipts.c.version_id.not_in(select(s.active.c.version_id)),
                )
            ).all()
        pending = tuple(
            (target.version_id, target.cleanup_reason or "cleanup_required")
            for target in sorted(targets)
            if not target.artifacts_deleted
        )
        deleted = tuple(
            target.version_id for target in sorted(targets) if target.artifacts_deleted
        )
        return replace(
            result_from_dict(record["result"]),
            reused=reused,
            status=("registered_cleanup_pending" if pending else "registered")
            if active
            else "superseded",
            search_index_updated=bool(active),
            registration_sequence=record["sequence"],
            active_yj_codes=active,
            generation_id=generation,
            replaced_yj_codes=tuple(record["replaced"]),
            artifacts_deleted=record["artifacts_deleted"],
            deleted_version_ids=deleted,
            cleanup_pending=pending,
        )

    def cleanup(self) -> None:
        self.fault("before_cleanup_lock")
        with self.engine.begin() as connection:
            current = connection.execute(
                select(s.state.c.generation_id).with_for_update()
            ).scalar_one()
            self.fault("cleanup")
            if current is not None:
                connection.execute(
                    delete(s.memberships).where(
                        s.memberships.c.generation_id != current
                    )
                )
                connection.execute(
                    delete(s.generations).where(
                        s.generations.c.generation_id != current
                    )
                )
            eligible = self._eligible(current)
            identities = list(connection.execute(eligible).scalars())
            if identities:
                connection.execute(
                    delete(s.versions).where(s.versions.c.version_id.in_(identities))
                )
                connection.execute(
                    update(s.receipts)
                    .where(s.receipts.c.version_id.in_(identities))
                    .values(artifacts_deleted=True, cleanup_reason="")
                )
            self.fault("cleanup_before_commit")

    @staticmethod
    def _eligible(current):
        return select(s.receipts.c.version_id).where(
            s.receipts.c.artifacts_deleted.is_(False),
            s.receipts.c.version_id.not_in(select(s.active.c.version_id)),
            s.receipts.c.version_id.not_in(
                select(s.memberships.c.version_id).where(
                    s.memberships.c.generation_id == current
                )
            ),
        )

    def _cleanup_safe(self):
        try:
            self.cleanup()
        except SQLAlchemyError, OSError:
            with self.engine.begin() as connection:
                current = connection.execute(
                    select(s.state.c.generation_id).with_for_update()
                ).scalar_one()
                connection.execute(
                    update(s.receipts)
                    .where(s.receipts.c.version_id.in_(self._eligible(current)))
                    .values(cleanup_reason="database_cleanup_failed")
                )
