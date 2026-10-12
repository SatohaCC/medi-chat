"""API層のチャットモデルとapplicationの会話ユースケースをつなぐアダプター。"""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable, Sequence

from package_inserts.catalog_models import PackageInsertCatalog

from ..application.chat.answer_preparation import (
    prepare_reply as app_prepare_reply,
)
from ..application.chat.answer_question import (
    answer_question as app_answer_question,
)
from ..application.chat.llm_contracts import LLMProvider
from ..application.chat.stream_closing import closing_stream
from ..application.chat.stream_reply import stream_reply as app_stream_reply
from ..application.retrieval.intent_contracts import IntentClassifier
from ..application.retrieval.keyword_contracts import KeywordExtractor
from ..application.retrieval.snapshot_contracts import RetrievalSnapshotProvider
from ..config.generation_settings import GenerationDefaults, read_generation_defaults
from ..domain.attachment.repositories import AttachmentProductRepository
from ..domain.retrieval.repositories import EvidenceRepository
from .chat_dto_mapper import (
    chat_message_from_api,
    chat_response_from_api,
    chat_response_to_api,
)
from .chat_models import (
    ChatMessage as ApiChatMessage,
)
from .chat_models import (
    ChatResponse as ApiChatResponse,
)


class AppChatService:
    """RESTおよびWebSocket向けのチャットサービス実装。"""

    def __init__(
        self,
        *,
        medicine_reader: AttachmentProductRepository,
        evidence_reader: EvidenceRepository,
        intent_classifier: IntentClassifier,
        keyword_extractor: KeywordExtractor,
        catalog: PackageInsertCatalog,
        provider_factory: Callable[[str | None], LLMProvider],
        defaults: Callable[[], GenerationDefaults] = read_generation_defaults,
        snapshot_provider: RetrievalSnapshotProvider | None = None,
    ) -> None:
        self.medicine_reader = medicine_reader
        self.evidence_reader = evidence_reader
        self.intent_classifier = intent_classifier
        self.keyword_extractor = keyword_extractor
        self.catalog = catalog
        self.provider_factory = provider_factory
        self.defaults = defaults
        self.snapshot_provider = snapshot_provider

    @property
    def is_jev_available(self) -> bool:
        return getattr(self.intent_classifier, "is_available", True)

    async def prepare_reply(
        self,
        conversation: Sequence[ApiChatMessage],
        product_yj_codes: list[str],
    ) -> ApiChatResponse:
        pure_conversation = [chat_message_from_api(m) for m in conversation]
        pure_reply = await app_prepare_reply(
            pure_conversation,
            product_yj_codes,
            medicine_reader=self.medicine_reader,
            evidence_reader=self.evidence_reader,
            intent_classifier=self.intent_classifier,
            keyword_extractor=self.keyword_extractor,
            catalog=self.catalog,
            snapshot_provider=self.snapshot_provider,
        )
        return chat_response_to_api(pure_reply)

    async def stream_answer(
        self,
        reply: ApiChatResponse,
        conversation: Sequence[ApiChatMessage],
        provider_name: str | None = None,
        model_name: str | None = None,
    ) -> AsyncIterator[str]:
        settings = self.defaults()
        pure_reply = chat_response_from_api(reply)
        pure_conversation = [chat_message_from_api(m) for m in conversation]
        async with closing_stream(
            app_stream_reply(
                pure_reply,
                pure_conversation,
                catalog=self.catalog,
                provider_factory=self.provider_factory,
                provider_name=provider_name or settings.provider,
                model_name=model_name or settings.model,
            )
        ) as response:
            async for chunk in response:
                yield chunk

    async def answer_question(
        self,
        conversation: Sequence[ApiChatMessage],
        product_yj_codes: list[str],
        provider_name: str | None = None,
        model_name: str | None = None,
    ) -> ApiChatResponse:
        pure_conversation = [chat_message_from_api(m) for m in conversation]
        settings = self.defaults()
        pure_reply = await app_answer_question(
            pure_conversation,
            product_yj_codes,
            medicine_reader=self.medicine_reader,
            evidence_reader=self.evidence_reader,
            intent_classifier=self.intent_classifier,
            keyword_extractor=self.keyword_extractor,
            catalog=self.catalog,
            provider_factory=self.provider_factory,
            provider_name=provider_name or settings.provider,
            model_name=model_name or settings.model,
            snapshot_provider=self.snapshot_provider,
        )
        return chat_response_to_api(pure_reply)
