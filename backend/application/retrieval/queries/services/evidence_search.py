"""Materialize each criterion once and retain source-faithful merged evidence."""

from backend.application.medicine.queries.models import ResolvedMedicine
from backend.application.retrieval.interfaces.evidence_query_reader import (
    EvidenceQueryReader,
)
from backend.application.retrieval.queries.models import Evidence, SearchCriteria
from backend.application.retrieval.queries.policies.selection import merge_evidence


async def search_evidence(
    reader: EvidenceQueryReader,
    medicines: tuple[ResolvedMedicine, ...],
    criteria: list[SearchCriteria],
    *,
    cache: dict[SearchCriteria, tuple[Evidence, ...]] | None = None,
) -> list[Evidence]:
    if cache is None:
        cache = {}
    batches = []
    for condition in criteria:
        if condition not in cache:
            cache[condition] = tuple(await reader.search(condition, medicines))
        batches.append((cache[condition], condition.source))
    return list(merge_evidence(batches))
