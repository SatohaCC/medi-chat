"""添付文書からキーワードを検索する技術非依存のユースケース。"""

from __future__ import annotations

from collections.abc import Sequence

from backend.application.medicine.interfaces.medicine_query_reader import (
    MedicineQueryReader,
)
from backend.application.medicine.queries.policies.catalog_matching import (
    MedicineCatalog,
)
from backend.application.medicine.values import parse_yj_codes
from backend.application.retrieval.interfaces.evidence_query_reader import (
    EvidenceQueryReader,
)
from backend.application.retrieval.interfaces.keyword_extractor import (
    KeywordExtractor,
)
from backend.application.retrieval.interfaces.snapshot_provider import (
    RetrievalSnapshotProvider,
)
from backend.application.retrieval.queries.models import Evidence
from backend.application.retrieval.queries.policies.selection import (
    build_keyword_search_criteria,
    merge_evidence,
)
from backend.application.retrieval.values import DetectionSource
from backend.domain.medicine.identifiers import YjCode


async def search_evidence_by_keywords(
    query: str,
    product_yj_codes: Sequence[str] = (),
    *,
    keyword_extractor: KeywordExtractor | None = None,
    snapshot_provider: RetrievalSnapshotProvider,
) -> tuple[Evidence, ...]:
    """キーワードと任意の対象医薬品コードに基づいて添付文書の根拠を検索する。"""
    codes = parse_yj_codes(product_yj_codes)
    async with snapshot_provider.acquire() as snapshot:
        return await _search_evidence_by_keywords(
            query,
            codes,
            medicine_reader=snapshot.medicine_reader,
            evidence_reader=snapshot.evidence_reader,
            keyword_extractor=keyword_extractor,
        )


async def _search_evidence_by_keywords(
    query: str,
    product_yj_codes: tuple[YjCode, ...] = (),
    *,
    medicine_reader: MedicineQueryReader,
    evidence_reader: EvidenceQueryReader,
    keyword_extractor: KeywordExtractor | None = None,
) -> tuple[Evidence, ...]:
    """キーワードと任意の対象医薬品コードに基づいて添付文書の根拠を検索する。"""
    medicines = await medicine_reader.read_medicines()
    if not medicines:
        return ()

    catalog = MedicineCatalog(medicines)
    requested_codes = product_yj_codes
    if requested_codes:
        targets = tuple(catalog.match_yj_codes(requested_codes))
    else:
        all_yj_codes = [m.yj_code for m in medicines if m.yj_code]
        targets = tuple(catalog.match_yj_codes(all_yj_codes))

    if not targets:
        return ()

    criteria = build_keyword_search_criteria(query)
    if criteria is None:
        return ()

    raw_evidence = await evidence_reader.search(criteria, targets)
    return merge_evidence([(raw_evidence, DetectionSource.KEYWORD)])
