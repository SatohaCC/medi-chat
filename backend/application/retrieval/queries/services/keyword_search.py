"""添付文書からキーワードを検索する技術非依存のユースケース。"""

from __future__ import annotations

import re
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
from backend.application.retrieval.interfaces.keyword_expander import (
    KeywordExpander,
)
from backend.application.retrieval.interfaces.keyword_extractor import (
    KeywordExtractor,
)
from backend.application.retrieval.interfaces.snapshot_provider import (
    RetrievalSnapshotProvider,
)
from backend.application.retrieval.queries.models import (
    KeywordSearchResult,
    SearchCriteria,
)
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
    keyword_expander: KeywordExpander | None = None,
    expand: bool = False,
    snapshot_provider: RetrievalSnapshotProvider,
) -> KeywordSearchResult:
    """キーワードと任意の対象医薬品コードに基づいて添付文書の根拠を検索する。"""
    codes = parse_yj_codes(product_yj_codes)

    expanded_terms: tuple[str, ...] = ()
    if expand and keyword_expander is not None:
        try:
            expanded = await keyword_expander.expand_keywords(query)
            original_terms = {
                t.lower() for raw in re.split(r"[\s　]+", query) if (t := raw.strip())
            }
            expanded_terms = tuple(
                dict.fromkeys(
                    term
                    for raw in expanded
                    if len(term := raw.strip()) >= 2
                    and term.lower() not in original_terms
                )
            )
        except Exception:
            expanded_terms = ()

    criteria = build_keyword_search_criteria(query, additional_keywords=expanded_terms)
    if criteria is None:
        return KeywordSearchResult(evidence=(), expanded_keywords=expanded_terms)

    async with snapshot_provider.acquire() as snapshot:
        return await _search_evidence_by_keywords(
            criteria,
            codes,
            medicine_reader=snapshot.medicine_reader,
            evidence_reader=snapshot.evidence_reader,
            expanded_terms=expanded_terms,
        )


async def _search_evidence_by_keywords(
    criteria: SearchCriteria,
    product_yj_codes: tuple[YjCode, ...] = (),
    *,
    medicine_reader: MedicineQueryReader,
    evidence_reader: EvidenceQueryReader,
    expanded_terms: tuple[str, ...] = (),
) -> KeywordSearchResult:
    """キーワードと任意の対象医薬品コードに基づいて添付文書の根拠を検索する。"""
    medicines = await medicine_reader.read_medicines()
    if not medicines:
        return KeywordSearchResult(evidence=(), expanded_keywords=expanded_terms)

    catalog = MedicineCatalog(medicines)
    requested_codes = product_yj_codes
    if requested_codes:
        targets = tuple(catalog.match_yj_codes(requested_codes))
    else:
        all_yj_codes = [m.yj_code for m in medicines if m.yj_code]
        targets = tuple(catalog.match_yj_codes(all_yj_codes))

    if not targets:
        return KeywordSearchResult(evidence=(), expanded_keywords=expanded_terms)

    raw_evidence = await evidence_reader.search(criteria, targets)
    merged = merge_evidence([(raw_evidence, DetectionSource.KEYWORD)])
    return KeywordSearchResult(evidence=merged, expanded_keywords=expanded_terms)
