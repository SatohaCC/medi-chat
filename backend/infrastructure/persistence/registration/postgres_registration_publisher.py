"""PostgreSQL publication adapter; transactions own all retained payloads."""

import hashlib
import json
import uuid
from collections.abc import Callable

from sqlalchemy import Text, cast, delete, func, insert, select, text, update
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from backend.application.attachment_import.commands.models import ImportResult
from backend.application.attachment_import.errors import (
    ImportCancelled,
    ImportConflict,
    ImportStorageError,
)
from backend.domain.attachment.identifiers import DocumentId
from backend.domain.attachment.primitives import AttachmentSha256, RevisionYearMonth
from backend.domain.attachment.value_objects import RegistrationVersion
from backend.domain.medicine.identifiers import YjCode
from backend.infrastructure.document_import.attachment_contracts import (
    AttachmentArtifactEncoder,
)
from backend.infrastructure.document_import.attachment_payloads import DecodedAttachment
from backend.infrastructure.persistence.maintenance.postgres_registration_cleanup import (
    PostgresRegistrationCleanup,
)
from backend.infrastructure.persistence.registration.postgres_import_replay_reader import (
    PostgresImportReplayReader,
)
from backend.infrastructure.persistence.registration.registration_payloads import (
    PostgresRegistrationInput,
    PreparedRegistration,
)
from backend.infrastructure.persistence.registration.registration_plan import (
    plan_registration,
)
from backend.infrastructure.persistence.registration.registration_preparation import (
    RegistrationPreparer,
)
from backend.infrastructure.persistence.runtime.postgres_integrity import (
    PROJECTION_FINGERPRINT,
)
from backend.infrastructure.persistence.schemas import attachment_tables as s
from backend.infrastructure.serialization.import_result_codec import result_dict


class PostgresRegistrationPublisher:
    def __init__(
        self,
        engine: Engine,
        *,
        encoder: AttachmentArtifactEncoder,
        fault: Callable[[str], None] = lambda phase: None,
    ):
        self.engine = engine
        self.preparer = RegistrationPreparer(encoder)
        self.results = PostgresImportReplayReader(engine)
        self.maintenance = PostgresRegistrationCleanup(engine, fault=fault)
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
            versions = tuple(self.preparer.version(item) for item in inputs)
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
                PreparedRegistration(version, None)
                if version.version_id.value in known
                else self.preparer.prepare(item)
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
                planned = dict(
                    plan_registration(
                        before,
                        tuple(item.version for item in prepared),
                        frozenset(records),
                    ).assignments
                )
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
                self.maintenance.cleanup_after_publication()
            return tuple(
                self.results.read_result(identity, reused=reused)
                for identity, reused in requested
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
