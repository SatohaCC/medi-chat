"""Reclaim unreferenced generations and payloads in a separate transaction."""

from collections.abc import Callable

from sqlalchemy import delete, select, update
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from backend.infrastructure.persistence.schemas import attachment_tables as s


class PostgresRegistrationCleanup:
    def __init__(
        self, engine: Engine, *, fault: Callable[[str], None] = lambda phase: None
    ):
        self.engine = engine
        self.fault = fault

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

    def cleanup_after_publication(self):
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
