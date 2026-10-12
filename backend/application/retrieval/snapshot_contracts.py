"""取得開始からmaterialize終了までの世代所有境界。"""

from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from typing import Protocol

from ...domain.attachment.repositories import AttachmentProductRepository
from ...domain.retrieval.identifiers import SearchGenerationId
from ...domain.retrieval.repositories import EvidenceRepository


@dataclass(frozen=True, slots=True)
class RetrievalSnapshot:
    generation_id: SearchGenerationId
    medicine_reader: AttachmentProductRepository
    evidence_reader: EvidenceRepository
    document_count: int = 0
    unit_count: int = 0


class RetrievalSnapshotProvider(Protocol):
    def acquire(self) -> AbstractAsyncContextManager[RetrievalSnapshot]: ...
