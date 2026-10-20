"""質問から添付文書の根拠を取得する技術非依存のユースケース。"""

import asyncio
from collections.abc import Awaitable, Callable
from copy import deepcopy

from backend.application.medicine.product_catalog import MedicineCatalog
from backend.application.medicine.product_contracts import RegisteredMedicineReader
from backend.application.medicine.product_models import ResolvedMedicine

from ...domain.retrieval.repositories import EvidenceRepository
from ...domain.retrieval.services import (
    detect_fixed_keyword_criteria as _detect_fixed_keyword_criteria,
)
from ...domain.retrieval.services import (
    merge_evidence,
)
from ...domain.retrieval.value_objects import Evidence, IntentPolicy, SearchCriteria
from .intent_contracts import IntentClassifier, IntentRequest
from .jev_detector import JevDetectionResult, detect_jev_criteria
from .keyword_contracts import KeywordExtractor
from .morphology_detector import detect_morphology_criteria
from .retrieval_models import RetrievalResult
from .snapshot_contracts import RetrievalSnapshotProvider

SourcesCallback = Callable[[list[Evidence]], Awaitable[None]]
CriteriaCallback = Callable[[list[SearchCriteria]], Awaitable[None]]


async def retrieve_evidence(
    message: str,
    product_yj_codes: list[str],
    *,
    medicine_reader: RegisteredMedicineReader,
    evidence_reader: EvidenceRepository,
    intent_classifier: IntentClassifier,
    keyword_extractor: KeywordExtractor,
    intent_policy: IntentPolicy,
    snapshot_provider: RetrievalSnapshotProvider | None = None,
    on_logic_sources: SourcesCallback | None = None,
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
                on_logic_sources=on_logic_sources,
            )
    medicine_catalog = MedicineCatalog(await medicine_reader.read_medicines())
    resolved = medicine_catalog.match_yj_codes(product_yj_codes)
    needs_clarification = not resolved
    excluded_terms = medicine_catalog.names_for_yj_codes(product_yj_codes)

    search_batches: dict[SearchCriteria, tuple[Evidence, ...]] = {}

    async def publish_logic(criteria: list[SearchCriteria]) -> None:
        if on_logic_sources is not None and not needs_clarification:
            sources = await _search_evidence(
                evidence_reader, tuple(resolved), criteria, cache=search_batches
            )
            await on_logic_sources(sources)

    criteria, jev_response, qualifying_intents = await collect_search_criteria(
        intent_classifier,
        keyword_extractor,
        message,
        excluded_terms,
        intent_policy=intent_policy,
        on_logic_criteria=publish_logic if on_logic_sources is not None else None,
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
    sources = await _search_evidence(
        evidence_reader, tuple(resolved), criteria, cache=search_batches
    )
    resolved_codes = {code for group in resolved for code in group.yj_codes}
    unregistered_codes = [
        code for code in product_yj_codes if code not in resolved_codes
    ]
    notices = []
    if unregistered_codes:
        notices.append(
            f"指定されたYJコード（{', '.join(unregistered_codes)}）は電子添文データが未登録のため、検索対象外として回答を作成しました。"
        )
    return RetrievalResult(
        intent=intent,
        retrieval_strategy="three_detectors",
        resolved_medicines=resolved,
        sources=sources,
        notices=notices,
        jev_response=deepcopy(jev_response),
        qualifying_intents=qualifying_intents,
    )


async def _search_evidence(
    reader: EvidenceRepository,
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


async def collect_search_criteria(
    intent_classifier: IntentClassifier,
    keyword_extractor: KeywordExtractor,
    message: str,
    excluded_terms: list[str],
    *,
    intent_policy: IntentPolicy,
    on_logic_criteria: CriteriaCallback | None = None,
):
    """各ローカル検出の条件を累積通知し、全検出完了後の条件を返す。"""
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
    logic_criteria: list[SearchCriteria] = []
    jev_response = None
    qualifying_intents: tuple[str, ...] = ()
    try:
        for completed in asyncio.as_completed(tasks):
            result = await completed
            if isinstance(result, JevDetectionResult):
                criteria.extend(result.search_criteria)
                jev_response = result.raw_response
                qualifying_intents = result.qualifying_intents
            else:
                if result is not None:
                    conditions = result if isinstance(result, tuple) else (result,)
                    criteria.extend(conditions)
                    logic_criteria.extend(conditions)
                    if conditions and on_logic_criteria is not None:
                        await on_logic_criteria(list(logic_criteria))
    finally:
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

    return criteria, jev_response, qualifying_intents
