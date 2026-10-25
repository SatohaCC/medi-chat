"""Reader for replaying import receipts."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Engine

from backend.application.attachment_import.commands.models import ImportResult
from backend.application.attachment_import.errors import ImportNotFound
from backend.infrastructure.persistence.mappings.import_result_mapping import (
    map_receipt_to_import_result,
)
from backend.infrastructure.persistence.records.postgres_import_receipt_records import (
    fetch_active_yj_codes_by_version,
    fetch_cleanup_targets,
    fetch_generation_id,
    fetch_receipt_by_version,
)


class PostgresImportReplayReader:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def read_result(self, identity: str, *, reused: bool = False) -> ImportResult:
        with self.engine.connect().execution_options(
            isolation_level="REPEATABLE READ"
        ) as connection:
            connection.execute(text("SET TRANSACTION READ ONLY"))
            record = fetch_receipt_by_version(connection, identity)
            if record is None:
                raise ImportNotFound(
                    "import_not_found",
                    "Registered import does not exist",
                    phase="publication",
                )
            active = fetch_active_yj_codes_by_version(connection, identity)
            generation = fetch_generation_id(connection)
            targets = fetch_cleanup_targets(connection, record["cleanup_targets"])

        return map_receipt_to_import_result(
            record,
            active=active,
            generation=generation,
            targets=targets,
            reused=reused,
        )

    def replay_result(self, document_id: str, digest: str) -> ImportResult:
        """Replay a retained receipt even after its original payload was reclaimed."""
        identity = f"{document_id}:{digest}"
        return self.read_result(identity, reused=True)
