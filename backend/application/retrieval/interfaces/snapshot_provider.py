"""取得開始からmaterialize終了までの世代所有境界。"""

from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from typing import Protocol

from backend.application.medicine.interfaces.medicine_query_reader import (
    MedicineQueryReader,
)
from backend.application.medicine.values import SearchGenerationId
from backend.application.retrieval.interfaces.evidence_query_reader import (
    EvidenceQueryReader,
)


@dataclass(frozen=True, slots=True)
class RetrievalSnapshot:
    generation_id: SearchGenerationId
    medicine_reader: MedicineQueryReader
    evidence_reader: EvidenceQueryReader
    document_count: int = 0
    unit_count: int = 0


class RetrievalSnapshotProvider(Protocol):
    def acquire(self) -> AbstractAsyncContextManager[RetrievalSnapshot]: ...
