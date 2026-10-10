"""回答準備の技術非依存入口。"""

import asyncio
from collections.abc import Sequence
from copy import deepcopy

from package_inserts.catalog_models import PackageInsertCatalog

from ...domain.attachment.repositories import AttachmentProductRepository
from ...domain.attachment.value_objects import AttachmentProductMatch
from ...domain.retrieval.repositories import EvidenceRepository
from ...domain.retrieval.services import (
    detect_fixed_keyword_criteria as _detect_fixed_keyword_criteria,
)
from ...domain.retrieval.services import merge_evidence
from ...domain.retrieval.value_objects import Evidence, SearchCriteria
from ..indexing.medicine_catalog import AttachmentProductCatalog
from ..retrieval.intent_contracts import IntentClassifier, IntentRequest
from ..retrieval.jev_detector import JevDetectionResult, detect_jev_criteria
from ..retrieval.keyword_contracts import KeywordExtractor
from ..retrieval.morphology_detector import detect_morphology_criteria
from .chat_models import ChatMessage, ChatResponse


async def prepare_reply(
    conversation: Sequence[ChatMessage],
    product_yj_codes: list[str],
    *,
    medicine_reader: AttachmentProductRepository,
    evidence_reader: EvidenceRepository,
    intent_classifier: IntentClassifier,
    keyword_extractor: KeywordExtractor,
    catalog: PackageInsertCatalog,
) -> ChatResponse:
    message = next(
        (item.content for item in reversed(conversation) if item.role == "user"), ""
    )
    medicine_catalog = AttachmentProductCatalog(await medicine_reader.read_medicines())
    excluded_terms = medicine_catalog.aliases_for_yj_codes(product_yj_codes)
    criteria, jev_response, qualifying_intents = await collect_search_criteria(
        intent_classifier, keyword_extractor, message, excluded_terms, catalog=catalog
    )

    resolved = medicine_catalog.resolve_medicines(message, product_yj_codes)
    needs_clarification = (
        not resolved
        or not medicine_catalog.covers_requested_products(resolved, product_yj_codes)
    )
    intent = (
        ", ".join(
            dict.fromkeys(
                item.intent.value
                for item in criteria
                if item.intent is not None and item.intent.value
            )
        )
        or catalog.fallback_intent
    )
    if qualifying_intents:
        intent = ", ".join(qualifying_intents)
    if needs_clarification:
        return ChatResponse(
            answer="指定されたYJコードのすべてに対応する電子添文が、現在の検索データにありません。",
            intent=intent,
            retrieval_strategy="product_code_lookup",
            resolved_medicines=resolved,
            needs_clarification=True,
            notices=[
                "検索対象の構造化データに登録されているYJコードを指定してください。"
            ],
            jev_response=deepcopy(jev_response),
            qualifying_intents=qualifying_intents,
        )
    sources = await _search_evidence(evidence_reader, tuple(resolved), criteria)
    return ChatResponse(
        answer=_summarize_evidence(sources),
        intent=intent,
        retrieval_strategy="three_detectors",
        resolved_medicines=resolved,
        sources=sources,
        jev_response=deepcopy(jev_response),
        qualifying_intents=qualifying_intents,
    )


async def _search_evidence(
    reader: EvidenceRepository,
    medicines: tuple[AttachmentProductMatch, ...],
    criteria: list[SearchCriteria],
) -> list[Evidence]:
    batches = []
    for condition in criteria:
        batches.append((await reader.search(condition, medicines), condition.source))
    return list(merge_evidence(batches))


def _summarize_evidence(sources: list[Evidence]) -> str:
    if not sources:
        return "検索条件に合う添付文書の記載を見つけられませんでした。"
    sections = list(
        dict.fromkeys(
            f"{source.section.get('code')} {source.section.get('title')}".strip()
            for source in sources
        )
    )
    return (
        f"関連する添付文書の記載を{len(sources)}件取得しました。"
        f"対象項目: {', '.join(sections)}。"
    )


async def collect_search_criteria(
    intent_classifier: IntentClassifier,
    keyword_extractor: KeywordExtractor,
    message: str,
    excluded_terms: list[str],
    *,
    catalog: PackageInsertCatalog,
):
    """全検出完了後の検索条件を、検索IOを行わず返す。"""
    tasks = [
        asyncio.create_task(
            detect_jev_criteria(
                intent_classifier, IntentRequest(message), catalog=catalog
            )
        ),
        asyncio.create_task(
            asyncio.to_thread(
                detect_morphology_criteria, keyword_extractor, message, excluded_terms
            )
        ),
        asyncio.create_task(
            asyncio.to_thread(_detect_fixed_keyword_criteria, message, catalog)
        ),
    ]
    criteria: list[SearchCriteria] = []
    jev_response = None
    qualifying_intents: tuple[str, ...] = ()
    try:
        for completed in asyncio.as_completed(tasks):
            result = await completed
            if isinstance(result, JevDetectionResult):
                criteria.extend(result.search_criteria)
                jev_response = result.raw_response
                qualifying_intents = result.qualifying_intents
            elif result is not None:
                criteria.append(result)
    finally:
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

    return criteria, jev_response, qualifying_intents
