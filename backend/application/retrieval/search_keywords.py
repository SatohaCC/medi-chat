"""添付文書からキーワードを検索する技術非依存のユースケース。"""

from __future__ import annotations

import re
from collections.abc import Sequence

from ...domain.attachment.repositories import AttachmentProductRepository
from ...domain.retrieval.primitives import DetectionSource, SearchKeyword
from ...domain.retrieval.repositories import EvidenceRepository
from ...domain.retrieval.services import merge_evidence
from ...domain.retrieval.value_objects import Evidence, SearchCriteria
from ..indexing.medicine_catalog import AttachmentProductCatalog
from .keyword_contracts import KeywordExtractor
from .snapshot_contracts import RetrievalSnapshotProvider


async def search_evidence_by_keywords(
    query: str,
    product_yj_codes: Sequence[str] = (),
    *,
    medicine_reader: AttachmentProductRepository,
    evidence_reader: EvidenceRepository,
    keyword_extractor: KeywordExtractor | None = None,
    snapshot_provider: RetrievalSnapshotProvider | None = None,
) -> tuple[Evidence, ...]:
    """キーワードと任意の対象医薬品コードに基づいて添付文書の根拠を検索する。"""
    if snapshot_provider is not None:
        async with snapshot_provider.acquire() as snapshot:
            return await search_evidence_by_keywords(
                query,
                product_yj_codes,
                medicine_reader=snapshot.medicine_reader,
                evidence_reader=snapshot.evidence_reader,
                keyword_extractor=keyword_extractor,
            )

    medicines = await medicine_reader.read_medicines()
    if not medicines:
        return ()

    catalog = AttachmentProductCatalog(medicines)
    requested_codes = [code.strip() for code in product_yj_codes if code.strip()]
    if requested_codes:
        targets = tuple(catalog.match_yj_codes(requested_codes))
    else:
        all_yj_codes = [m.yj_code for m in medicines if m.yj_code]
        targets = tuple(catalog.match_yj_codes(all_yj_codes))

    if not targets:
        return ()

    # スペース区切りの入力語を基本キーワードとする
    raw_terms = [t.strip() for t in re.split(r"[\s　]+", query) if t.strip()]
    valid_keywords = [term for term in raw_terms if len(term) >= 2]

    if not valid_keywords:
        return ()

    criteria = SearchCriteria(
        source=DetectionSource.KEYWORD,
        keywords=tuple(SearchKeyword(term) for term in valid_keywords),
    )

    raw_evidence = await evidence_reader.search(criteria, targets)
    return merge_evidence([(raw_evidence, DetectionSource.KEYWORD)])
