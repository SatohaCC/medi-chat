"""A configured smoke probe refuses recovery work using only read operations."""

import json
import sqlite3
from contextlib import closing
from pathlib import Path

from ...config.import_settings import resolve_import_directory
from ..persistence.owned_sqlite import OwnedSqliteConnection
from ..persistence.read_workers import ReadWorkers
from ..persistence.registration_lock import registration_lock
from ..persistence.registration_reader import read_registered_snapshot


def verify_no_recovery_work(index_path: Path) -> None:
    with closing(
        sqlite3.connect(
            index_path.as_uri() + "?mode=ro", uri=True, factory=OwnedSqliteConnection
        )
    ) as connection:
        pending = connection.execute(
            "SELECT COUNT(*) FROM registration_receipts WHERE artifacts_deleted=0 AND version_id NOT IN (SELECT version_id FROM active_registrations)"
        ).fetchone()[0]
        leases = connection.execute(
            "SELECT COUNT(*) FROM generation_leases"
        ).fetchone()[0]
        obsolete = connection.execute(
            "SELECT COUNT(*) FROM registration_generations WHERE generation_id NOT IN (SELECT generation_id FROM registration_state)"
        ).fetchone()[0]
        references = {
            file["path"]
            for table in ("registration_receipts", "registration_generations")
            for (payload,) in connection.execute(f"SELECT files_json FROM {table}")
            for file in json.loads(payload)
        }
        roots = {
            Path(root)
            for (root,) in connection.execute(
                "SELECT DISTINCT root FROM registration_owned_files"
            )
        }
    if pending or leases or obsolete:
        raise RuntimeError(
            "configured gate requires explicit startup/CLI recovery; pending ownership or leases exist"
        )
    roots.add(resolve_import_directory())
    for root in roots:
        if root.is_symlink():
            raise RuntimeError(
                "configured gate requires explicit recovery; unsafe ownership root"
            )
        if any(
            (stage / ".attachment-stage").is_file() for stage in root.glob(".stage-*")
        ):
            raise RuntimeError(
                "configured gate requires explicit recovery; private stage exists"
            )
        for journal in (root / ".registration-attempts").glob("*.json"):
            try:
                value = json.loads(journal.read_bytes())
                if any(path not in references for path in value["files"]):
                    raise RuntimeError(
                        "configured gate requires explicit recovery; unpublished attempt exists"
                    )
            except OSError, ValueError, TypeError, KeyError:
                raise RuntimeError(
                    "configured gate requires explicit recovery; ownership journal is unreadable"
                ) from None


class ReadOnlyGenerationProbe:
    """Health-only observation never acquires a lease or performs recovery."""

    def __init__(self, index_path: Path, workers: ReadWorkers) -> None:
        self.index_path = index_path
        self.workers = workers

    async def statistics(self) -> dict[str, str | int]:
        def read() -> dict[str, str | int]:
            with registration_lock(self.index_path):
                verify_no_recovery_work(self.index_path)
                snapshot = read_registered_snapshot(self.index_path)
                if snapshot is None:
                    raise RuntimeError("initial_registration_required")
                with closing(
                    sqlite3.connect(
                        self.index_path.as_uri() + "?mode=ro",
                        uri=True,
                        factory=OwnedSqliteConnection,
                    )
                ) as connection:
                    generation = connection.execute(
                        "SELECT generation_id FROM registration_state WHERE singleton=1"
                    ).fetchone()[0]
                return {
                    "generation_id": generation,
                    "document_count": len(snapshot.documents),
                    "unit_count": len(snapshot.units),
                }

        return await self.workers.run(read)
