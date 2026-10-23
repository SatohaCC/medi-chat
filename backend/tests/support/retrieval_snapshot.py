"""Fixed reader ownership for tests of snapshot-based retrieval use cases."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from backend.application.medicine.product_contracts import RegisteredMedicineReader
from backend.application.retrieval.evidence_contracts import EvidenceRepository
from backend.application.retrieval.snapshot_contracts import (
    RetrievalSnapshot,
    SearchGenerationId,
)


class FixedSnapshotProvider:
    def __init__(
        self,
        medicine_reader: RegisteredMedicineReader,
        evidence_reader: EvidenceRepository,
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
