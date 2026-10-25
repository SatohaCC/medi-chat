"""Database records reader for registration receipts, active versions, and history."""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.engine import Connection

from backend.infrastructure.persistence.schemas import attachment_tables as s


def fetch_receipt_by_version(
    connection: Connection, identity: str
) -> dict[str, Any] | None:
    row = (
        connection.execute(
            select(s.receipts).where(s.receipts.c.version_id == identity)
        )
        .mappings()
        .first()
    )
    return dict(row) if row is not None else None


def fetch_active_yj_codes_by_version(
    connection: Connection, identity: str
) -> tuple[str, ...]:
    return tuple(
        sorted(
            connection.execute(
                select(s.active.c.yj_code).where(s.active.c.version_id == identity)
            ).scalars()
        )
    )


def fetch_generation_id(connection: Connection) -> str:
    return str(connection.execute(select(s.state.c.generation_id)).scalar_one())


def fetch_cleanup_targets(
    connection: Connection, target_version_ids: list[str]
) -> list[Any]:
    return list(
        connection.execute(
            select(
                s.receipts.c.version_id,
                s.receipts.c.artifacts_deleted,
                s.receipts.c.cleanup_reason,
            ).where(
                s.receipts.c.version_id.in_(target_version_ids),
                s.receipts.c.version_id.not_in(select(s.active.c.version_id)),
            )
        ).all()
    )


def fetch_receipt_page(
    connection: Connection, *, limit: int, offset: int
) -> tuple[int, list[dict[str, Any]], dict[str, list[str]]]:
    total = connection.execute(
        select(func.count()).select_from(s.receipts)
    ).scalar_one()
    records = [
        dict(r)
        for r in connection.execute(
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
    ]
    active: dict[str, list[str]] = {}
    if records:
        for row in connection.execute(
            select(s.active.c.version_id, s.active.c.yj_code)
            .where(s.active.c.version_id.in_([r["version_id"] for r in records]))
            .order_by(s.active.c.yj_code.collate("C"))
        ):
            active.setdefault(row.version_id, []).append(row.yj_code)
    return total, records, active
