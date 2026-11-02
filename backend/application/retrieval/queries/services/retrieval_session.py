"""One request's product resolution, snapshot, criteria cache and publication."""

import asyncio
from collections.abc import AsyncGenerator, Awaitable, Callable, Sequence
from contextlib import asynccontextmanager
from copy import deepcopy

from backend.application.medicine.queries.policies.catalog_matching import (
    MedicineCatalog,
)
from backend.application.medicine.values import parse_yj_codes
from backend.application.retrieval.interfaces.evidence_query_reader import (
    EvidenceQueryReader,
)
from backend.application.retrieval.interfaces.snapshot_provider import (
    RetrievalSnapshotProvider,
)
from backend.application.retrieval.queries.models import (
    Evidence,
    IntentPolicy,
    JevDetectionResult,
    RetrievalResult,
    SearchCriteria,
)
from backend.application.retrieval.queries.policies.standard import (
    EvidenceRetrievalPolicy,
)
from backend.application.retrieval.queries.services.evidence_search import (
    search_evidence,
)
from backend.application.retrieval.values import DetectionSource
from backend.domain.medicine.identifiers import YjCode


class EvidenceRetrievalSession:
    def __init__(
        self,
        *,
        catalog: MedicineCatalog,
        codes: tuple[YjCode, ...],
        reader: EvidenceQueryReader,
        intent_policy: IntentPolicy,
        retrieval_policy: EvidenceRetrievalPolicy,
    ) -> None:
        self.resolved = tuple(catalog.match_yj_codes(codes))
        self.excluded_terms = tuple(catalog.names_for_yj_codes(codes))
        self.reader = reader
        self.intent_policy = intent_policy
        self.needs_clarification = not self.resolved
        self.always_criteria = (
            [
                SearchCriteria(
                    source=DetectionSource.ALWAYS,
                    section_codes=retrieval_policy.always_retrieved_sections,
                )
            ]
            if retrieval_policy.always_retrieved_sections and self.resolved
            else []
        )
        self.criteria: list[SearchCriteria] = []
        self.cache: dict[SearchCriteria, tuple[Evidence, ...]] = {}
        self.jev = JevDetectionResult()
        self.lock = asyncio.Lock()
        self.closed = False
        resolved_codes = {
            code for medicine in self.resolved for code in medicine.yj_codes
        }
        missing = [code.value for code in codes if code.value not in resolved_codes]
        self.notices = (
            ["検索対象の構造化データに登録されているYJコードを指定してください。"]
            if self.needs_clarification
            else [
                f"指定されたYJコード（{', '.join(missing)}）は電子添文データが未登録のため、検索対象外として回答を作成しました。"
            ]
            if missing
            else []
        )

    def ensure_open(self) -> None:
        if self.closed:
            raise RuntimeError("Retrieval session is closed")

    async def retrieve(
        self,
        criteria: Sequence[SearchCriteria],
        *,
        on_sources: Callable[[list[Evidence]], Awaitable[None]] | None = None,
        jev: JevDetectionResult | None = None,
    ) -> RetrievalResult:
        # Readers share one MVCC transaction. Serialize IO and publication, not detectors.
        async with self.lock:
            self.ensure_open()
            self.criteria.extend(criteria)
            if jev is not None:
                self.jev = jev
            sources = []
            if not self.needs_clarification:
                sources = await search_evidence(
                    self.reader,
                    self.resolved,
                    self.always_criteria + list(criteria),
                    cache=self.cache,
                )
                if on_sources is not None:
                    cumulative = await search_evidence(
                        self.reader,
                        self.resolved,
                        self.always_criteria + self.criteria,
                        cache=self.cache,
                    )
                    if cumulative:
                        await on_sources(cumulative)
            detected = tuple(
                dict.fromkeys(
                    c.intent.value for c in self.criteria if c.intent is not None
                )
            )
            intent = (
                ", ".join(self.jev.qualifying_intents or detected)
                or self.intent_policy.fallback_intent.value
            )
            return RetrievalResult(
                intent=intent,
                retrieval_strategy="independent_detector",
                resolved_medicines=list(self.resolved),
                sources=sources,
                needs_clarification=self.needs_clarification,
                notices=list(self.notices),
                qualifying_intents=self.jev.qualifying_intents,
                jev_response=deepcopy(self.jev.raw_response),
            )


@asynccontextmanager
async def acquire_retrieval_session(
    product_yj_codes: Sequence[str],
    *,
    snapshot_provider: RetrievalSnapshotProvider,
    intent_policy: IntentPolicy,
    retrieval_policy: EvidenceRetrievalPolicy,
) -> AsyncGenerator[EvidenceRetrievalSession]:
    codes = parse_yj_codes(product_yj_codes)
    async with snapshot_provider.acquire() as snapshot:
        session = EvidenceRetrievalSession(
            catalog=MedicineCatalog(await snapshot.medicine_reader.read_medicines()),
            codes=codes,
            reader=snapshot.evidence_reader,
            intent_policy=intent_policy,
            retrieval_policy=retrieval_policy,
        )
        try:
            yield session
        finally:
            session.closed = True
