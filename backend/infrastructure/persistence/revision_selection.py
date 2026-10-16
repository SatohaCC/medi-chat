"""原本改訂規則への変換と、永続化済み公開参照の読取検証。"""

import json
from typing import Any

from ...application.attachment_import.import_errors import ImportConflict
from ...domain.attachment.exceptions import ConflictingRevisionError
from ...domain.attachment.identifiers import DocumentId
from ...domain.attachment.primitives import AttachmentSha256, RevisionYearMonth
from ...domain.attachment.services import latest_attachment
from ...domain.attachment.value_objects import RegistrationVersion
from ...domain.foundation.exceptions import DomainValidationError
from ...domain.medicine.identifiers import YjCode


def stored_version(record: dict[str, Any]) -> RegistrationVersion:
    try:
        revisions = json.loads(record["result_json"])["revisions"]
        revised_at = RevisionYearMonth(
            max(revision["year_month"] for revision in revisions)
        )
    except (KeyError, ValueError, TypeError, DomainValidationError) as exc:
        raise ImportConflict(
            "revision_policy_migration_required",
            "Stored registration has no valid revision month; explicit reinitialization is required",
            phase="validation",
        ) from exc
    return RegistrationVersion(
        document_id=DocumentId(record["document_id"]),
        source_sha256=AttachmentSha256(record["source_sha256"]),
        yj_codes=frozenset(
            YjCode(code) for code in json.loads(record["yj_codes_json"])
        ),
        revised_at=revised_at,
    )


def assign_latest(
    active: dict[YjCode, RegistrationVersion], version: RegistrationVersion
) -> dict[YjCode, RegistrationVersion]:
    updated = dict(active)
    for code in sorted(version.yj_codes, key=lambda code: code.value):
        try:
            updated[code] = latest_attachment(active.get(code), version)
        except ConflictingRevisionError as exc:
            error = ImportConflict(
                "same_revision_conflict",
                "Different originals for the same YJ code have the same revision month",
                phase="validation",
            )
            error.conflicts = (
                (
                    code.value,
                    tuple(
                        sorted(
                            {active[code].version_id.value, version.version_id.value}
                        )
                    ),
                ),
            )
            raise error from exc
    return updated


def validate_active_revisions(
    records: dict[str, dict[str, Any]], assigned: dict[str, str]
) -> dict[YjCode, RegistrationVersion]:
    """保存済み公開先を検証する。日付順へ自動で書き換えない。"""
    versions = {
        identity: stored_version(record) for identity, record in records.items()
    }
    expected: dict[YjCode, RegistrationVersion] = {}
    try:
        active = {
            YjCode(code): versions[identity] for code, identity in assigned.items()
        }
        for version in sorted(
            versions.values(), key=lambda v: v.revised_at.value, reverse=True
        ):
            expected = assign_latest(expected, version)
    except (ImportConflict, KeyError) as exc:
        raise ImportConflict(
            "revision_policy_migration_required",
            "Stored registrations have ambiguous latest revisions; explicit reinitialization is required",
            phase="validation",
        ) from exc
    if active != expected or any(
        records[v.version_id.value]["artifacts_deleted"] for v in active.values()
    ):
        raise ImportConflict(
            "revision_policy_migration_required",
            "Stored active documents do not follow revision dates; explicit reinitialization is required",
            phase="validation",
        )
    return active
