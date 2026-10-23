"""Fixed reader ownership for tests of snapshot-based retrieval use cases."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from backend.application.medicine.interfaces.medicine_query_reader import (
    MedicineQueryReader,
)
from backend.application.medicine.values import SearchGenerationId
from backend.application.retrieval.interfaces.evidence_query_reader import (
    EvidenceQueryReader,
)
from backend.application.retrieval.interfaces.snapshot_provider import (
    RetrievalSnapshot,
)


class FixedSnapshotProvider:
    def __init__(
        self,
        medicine_reader: MedicineQueryReader,
        evidence_reader: EvidenceQueryReader,
    ):
        self.snapshot = RetrievalSnapshot(
            SearchGenerationId("test"), medicine_reader, evidence_reader
        )
        self.entered = 0
        self.exited = 0

    @asynccontextmanager
    async def acquire(self) -> AsyncIterator[RetrievalSnapshot]:
        self.entered += 1
        try:
            yield self.snapshot
        finally:
            self.exited += 1
