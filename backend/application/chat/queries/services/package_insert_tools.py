"""Bind the three mandatory tools to one request-owned retrieval session."""

from collections.abc import AsyncGenerator, Sequence
from contextlib import asynccontextmanager

from backend.application.chat.interfaces.medical_tool import (
    MedicalTool,
    ToolExecutionInput,
)
from backend.application.chat.queries.services.package_insert_fixed_keyword_tool import (
    PackageInsertFixedKeywordTool,
)
from backend.application.chat.queries.services.package_insert_jev_tool import (
    PackageInsertJevTool,
)
from backend.application.chat.queries.services.package_insert_morphology_tool import (
    PackageInsertMorphologyTool,
)
from backend.application.retrieval.interfaces.intent_classifier import IntentClassifier
from backend.application.retrieval.interfaces.keyword_extractor import KeywordExtractor
from backend.application.retrieval.interfaces.snapshot_provider import (
    RetrievalSnapshotProvider,
)
from backend.application.retrieval.queries.models import IntentPolicy
from backend.application.retrieval.queries.policies.standard import (
    EvidenceRetrievalPolicy,
)
from backend.application.retrieval.queries.services.retrieval_session import (
    acquire_retrieval_session,
)


class PackageInsertTools:
    def __init__(
        self,
        *,
        intent_classifier: IntentClassifier,
        keyword_extractor: KeywordExtractor,
        intent_policy: IntentPolicy,
        retrieval_policy: EvidenceRetrievalPolicy,
        snapshot_provider: RetrievalSnapshotProvider,
    ) -> None:
        self.intent_classifier = intent_classifier
        self.keyword_extractor = keyword_extractor
        self.intent_policy = intent_policy
        self.retrieval_policy = retrieval_policy
        self.snapshot_provider = snapshot_provider

    @asynccontextmanager
    async def acquire(
        self, input_data: ToolExecutionInput
    ) -> AsyncGenerator[Sequence[MedicalTool]]:
        async with acquire_retrieval_session(
            input_data.product_yj_codes,
            snapshot_provider=self.snapshot_provider,
            intent_policy=self.intent_policy,
            retrieval_policy=self.retrieval_policy,
        ) as session:
            yield (
                PackageInsertFixedKeywordTool(session),
                PackageInsertMorphologyTool(session, self.keyword_extractor),
                PackageInsertJevTool(session, self.intent_classifier),
            )
