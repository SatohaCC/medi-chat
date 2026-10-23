"""会話ユースケースのオーケストレーションを担当するApplication Service。"""

from __future__ import annotations

from collections.abc import AsyncGenerator, Awaitable, Callable, Sequence

from backend.application.chat.interfaces.llm_provider import LLMProvider
from backend.application.chat.queries.models import (
    AnswerPromptPolicy,
    ChatMessage,
    ChatResponse,
)
from backend.application.chat.queries.services.answer_question import (
    answer_question as app_answer_question,
)
from backend.application.chat.queries.services.reply_preparation import (
    prepare_reply as app_prepare_reply,
)
from backend.application.chat.queries.services.stream_lifetime import closing_stream
from backend.application.chat.queries.services.stream_reply import (
    stream_reply as app_stream_reply,
)
from backend.application.retrieval.interfaces.intent_classifier import (
    IntentClassifier,
)
from backend.application.retrieval.interfaces.keyword_extractor import (
    KeywordExtractor,
)
from backend.application.retrieval.interfaces.snapshot_provider import (
    RetrievalSnapshotProvider,
)
from backend.application.retrieval.queries.models import Evidence, IntentPolicy
from backend.application.retrieval.queries.policies.standard import (
    DEFAULT_RETRIEVAL_POLICY,
    EvidenceRetrievalPolicy,
)
from backend.application.retrieval.queries.services.keyword_search import (
    search_evidence_by_keywords,
)


class ChatQueries:
    """医薬品解決・根拠検索・回答生成の各ユースケースを束ねるアプリケーションサービス。"""

    def __init__(
        self,
        *,
        intent_classifier: IntentClassifier,
        keyword_extractor: KeywordExtractor,
        intent_policy: IntentPolicy,
        retrieval_policy: EvidenceRetrievalPolicy = DEFAULT_RETRIEVAL_POLICY,
        answer_prompt_policy: AnswerPromptPolicy,
        provider_factory: Callable[[str | None], LLMProvider],
        snapshot_provider: RetrievalSnapshotProvider,
    ) -> None:
        self.intent_classifier = intent_classifier
        self.keyword_extractor = keyword_extractor
        self.intent_policy = intent_policy
        self.retrieval_policy = retrieval_policy
        self.answer_prompt_policy = answer_prompt_policy
        self.provider_factory = provider_factory
        self.snapshot_provider = snapshot_provider

    @property
    def is_jev_available(self) -> bool:
        return getattr(self.intent_classifier, "is_available", True)

    async def search_keywords(
        self,
        query: str,
        product_yj_codes: Sequence[str] = (),
    ) -> tuple[Evidence, ...]:
        return await search_evidence_by_keywords(
            query,
            product_yj_codes,
            keyword_extractor=self.keyword_extractor,
            snapshot_provider=self.snapshot_provider,
        )

    async def prepare_reply(
        self,
        conversation: Sequence[ChatMessage],
        product_yj_codes: list[str],
        *,
        on_logic_sources: Callable[[list[Evidence]], Awaitable[None]] | None = None,
    ) -> ChatResponse:
        return await app_prepare_reply(
            conversation,
            product_yj_codes,
            intent_classifier=self.intent_classifier,
            keyword_extractor=self.keyword_extractor,
            intent_policy=self.intent_policy,
            retrieval_policy=self.retrieval_policy,
            snapshot_provider=self.snapshot_provider,
            on_logic_sources=on_logic_sources,
        )

    async def stream_answer(
        self,
        reply: ChatResponse,
        conversation: Sequence[ChatMessage],
        *,
        provider_name: str,
        model_name: str,
    ) -> AsyncGenerator[str]:
        async with closing_stream(
            app_stream_reply(
                reply,
                conversation,
                answer_prompt_policy=self.answer_prompt_policy,
                provider_factory=self.provider_factory,
                provider_name=provider_name,
                model_name=model_name,
            )
        ) as response:
            async for chunk in response:
                yield chunk

    async def answer_question(
        self,
        conversation: Sequence[ChatMessage],
        product_yj_codes: list[str],
        *,
        provider_name: str,
        model_name: str,
    ) -> ChatResponse:
        return await app_answer_question(
            conversation,
            product_yj_codes,
            intent_classifier=self.intent_classifier,
            keyword_extractor=self.keyword_extractor,
            intent_policy=self.intent_policy,
            retrieval_policy=self.retrieval_policy,
            answer_prompt_policy=self.answer_prompt_policy,
            provider_factory=self.provider_factory,
            provider_name=provider_name,
            model_name=model_name,
            snapshot_provider=self.snapshot_provider,
        )
