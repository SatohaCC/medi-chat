"""質問から添付文書の根拠を取得する技術非依存のユースケース。"""

import asyncio
from copy import deepcopy

from ...domain.attachment.repositories import AttachmentProductRepository
from ...domain.attachment.value_objects import AttachmentProductMatch
from ...domain.medicine.identifiers import YjCode
from ...domain.retrieval.product_identity import (
    product_identity_reason,
    recognize_product_questions,
)
from ...domain.retrieval.repositories import EvidenceRepository
from ...domain.retrieval.services import (
    detect_fixed_keyword_criteria as _detect_fixed_keyword_criteria,
)
from ...domain.retrieval.services import merge_evidence
from ...domain.retrieval.value_objects import Evidence, IntentPolicy, SearchCriteria
from ..indexing.medicine_catalog import AttachmentProductCatalog
from .intent_contracts import IntentClassifier, IntentRequest
from .jev_detector import JevDetectionResult, detect_jev_criteria
from .keyword_contracts import KeywordExtractor
from .morphology_detector import detect_morphology_criteria
from .retrieval_models import RetrievalResult
from .snapshot_contracts import RetrievalSnapshotProvider


async def retrieve_evidence(
    message: str,
    product_yj_codes: list[str],
    *,
    medicine_reader: AttachmentProductRepository,
    evidence_reader: EvidenceRepository,
    intent_classifier: IntentClassifier,
    keyword_extractor: KeywordExtractor,
    intent_policy: IntentPolicy,
    snapshot_provider: RetrievalSnapshotProvider | None = None,
) -> RetrievalResult:
    if snapshot_provider is not None:
        async with snapshot_provider.acquire() as snapshot:
            return await retrieve_evidence(
                message,
                product_yj_codes,
                medicine_reader=snapshot.medicine_reader,
                evidence_reader=snapshot.evidence_reader,
                intent_classifier=intent_classifier,
                keyword_extractor=keyword_extractor,
                intent_policy=intent_policy,
            )
    medicine_catalog = AttachmentProductCatalog(await medicine_reader.read_medicines())
    resolved = medicine_catalog.resolve_medicines(message, product_yj_codes)
    needs_clarification = (
        not resolved
        or not medicine_catalog.covers_requested_products(resolved, product_yj_codes)
    )
    excluded_terms = medicine_catalog.aliases_for_yj_codes(product_yj_codes)
    criteria, jev_response, qualifying_intents = await collect_search_criteria(
        intent_classifier,
        keyword_extractor,
        message,
        excluded_terms,
        intent_policy=intent_policy,
    )

    intent = (
        ", ".join(
            dict.fromkeys(
                item.intent.value
                for item in criteria
                if item.intent is not None and item.intent.value
            )
        )
        or intent_policy.fallback_intent.value
    )
    if qualifying_intents:
        intent = ", ".join(qualifying_intents)
    if needs_clarification:
        return RetrievalResult(
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
    questions = recognize_product_questions(
        message, medicine_catalog.original_product_names()
    )
    reason = product_identity_reason(
        tuple(
            tuple(
                medicine_catalog.question_name_candidates(name.value)
                for name in question.names
            )
            for question in questions
        ),
        frozenset(YjCode.from_value(code) for code in product_yj_codes),
    )
    if reason is not None:
        return RetrievalResult(
            intent=intent,
            retrieval_strategy=reason.value,
            resolved_medicines=resolved,
            needs_clarification=True,
            jev_response=deepcopy(jev_response),
            qualifying_intents=qualifying_intents,
            product_identity_reason=reason,
        )
    sources = await _search_evidence(evidence_reader, tuple(resolved), criteria)
    return RetrievalResult(
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


async def collect_search_criteria(
    intent_classifier: IntentClassifier,
    keyword_extractor: KeywordExtractor,
    message: str,
    excluded_terms: list[str],
    *,
    intent_policy: IntentPolicy,
):
    """全検出完了後の検索条件を、検索IOを行わず返す。"""
    tasks = [
        asyncio.create_task(
            detect_jev_criteria(
                intent_classifier, IntentRequest(message), intent_policy=intent_policy
            )
        ),
        asyncio.create_task(
            asyncio.to_thread(
                detect_morphology_criteria, keyword_extractor, message, excluded_terms
            )
        ),
        asyncio.create_task(
            asyncio.to_thread(_detect_fixed_keyword_criteria, message, intent_policy)
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
