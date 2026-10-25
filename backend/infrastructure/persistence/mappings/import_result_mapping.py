"""Mapping between database receipt records and Application ImportResult."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from backend.application.attachment_import.commands.models import ImportResult
from backend.infrastructure.serialization.import_result_codec import result_from_dict


def map_receipt_to_import_result(
    record: dict[str, Any],
    *,
    active: tuple[str, ...],
    generation: str,
    targets: list[Any],
    reused: bool = False,
) -> ImportResult:
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
