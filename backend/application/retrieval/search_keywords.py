"""添付文書からキーワードを検索する技術非依存のユースケース。"""

from __future__ import annotations

from collections.abc import Sequence

from backend.application.medicine.input_values import parse_yj_codes
from backend.application.medicine.product_catalog import MedicineCatalog
from backend.application.medicine.product_contracts import RegisteredMedicineReader
from backend.application.retrieval.evidence_contracts import EvidenceRepository
from backend.application.retrieval.search_models import Evidence
from backend.application.retrieval.search_policy import (
    build_keyword_search_criteria,
    merge_evidence,
)
from backend.application.retrieval.search_values import DetectionSource
from backend.domain.medicine.identifiers import YjCode

from .keyword_contracts import KeywordExtractor
from .snapshot_contracts import RetrievalSnapshotProvider


async def search_evidence_by_keywords(
    query: str,
    product_yj_codes: Sequence[str] = (),
    *,
    medicine_reader: RegisteredMedicineReader,
    evidence_reader: EvidenceRepository,
    keyword_extractor: KeywordExtractor | None = None,
    snapshot_provider: RetrievalSnapshotProvider | None = None,
) -> tuple[Evidence, ...]:
    """キーワードと任意の対象医薬品コードに基づいて添付文書の根拠を検索する。"""
    return await _search_evidence_by_keywords(
        query,
        parse_yj_codes(product_yj_codes),
        medicine_reader=medicine_reader,
        evidence_reader=evidence_reader,
        keyword_extractor=keyword_extractor,
        snapshot_provider=snapshot_provider,
    )


async def _search_evidence_by_keywords(
    query: str,
    product_yj_codes: tuple[YjCode, ...] = (),
    *,
    medicine_reader: RegisteredMedicineReader,
    evidence_reader: EvidenceRepository,
    keyword_extractor: KeywordExtractor | None = None,
    snapshot_provider: RetrievalSnapshotProvider | None = None,
) -> tuple[Evidence, ...]:
    """キーワードと任意の対象医薬品コードに基づいて添付文書の根拠を検索する。"""
    if snapshot_provider is not None:
        async with snapshot_provider.acquire() as snapshot:
            return await _search_evidence_by_keywords(
                query,
                product_yj_codes,
                medicine_reader=snapshot.medicine_reader,
                evidence_reader=snapshot.evidence_reader,
                keyword_extractor=keyword_extractor,
            )

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
