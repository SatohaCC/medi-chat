"""会話ユースケースのオーケストレーションを担当するApplication Service。"""

from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable, Sequence

from backend.application.retrieval.search_models import Evidence, IntentPolicy

from ..retrieval.intent_contracts import IntentClassifier
from ..retrieval.keyword_contracts import KeywordExtractor
from ..retrieval.search_keywords import search_evidence_by_keywords
from ..retrieval.snapshot_contracts import (
    RetrievalSnapshotProvider,
)
from .answer_preparation import prepare_reply as app_prepare_reply
from .answer_prompt_policy import AnswerPromptPolicy
from .answer_question import answer_question as app_answer_question
from .chat_models import ChatMessage, ChatResponse
from .llm_contracts import LLMProvider
from .stream_closing import closing_stream
from .stream_reply import stream_reply as app_stream_reply


class ChatApplicationService:
    """医薬品解決・根拠検索・回答生成の各ユースケースを束ねるアプリケーションサービス。"""

    def __init__(
        self,
        *,
        intent_classifier: IntentClassifier,
        keyword_extractor: KeywordExtractor,
        intent_policy: IntentPolicy,
        answer_prompt_policy: AnswerPromptPolicy,
        provider_factory: Callable[[str | None], LLMProvider],
        snapshot_provider: RetrievalSnapshotProvider,
    ) -> None:
        self.intent_classifier = intent_classifier
        self.keyword_extractor = keyword_extractor
        self.intent_policy = intent_policy
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
    ) -> AsyncIterator[str]:
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
            answer_prompt_policy=self.answer_prompt_policy,
            provider_factory=self.provider_factory,
            provider_name=provider_name,
            model_name=model_name,
            snapshot_provider=self.snapshot_provider,
        )
