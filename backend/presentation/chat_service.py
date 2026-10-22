"""API層のチャットモデルとapplicationの会話ユースケースをつなぐアダプター。"""

from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable, Sequence

from backend.application.retrieval.search_models import Evidence

from ..application.chat.chat_models import ChatResponse as ApplicationChatResponse
from ..application.chat.chat_service import ChatApplicationService
from ..application.chat.stream_closing import closing_stream
from ..config.generation_settings import GenerationDefaults, read_generation_defaults
from .chat_dto_mapper import (
    chat_message_from_api,
    chat_response_to_api,
    evidence_to_api,
)
from .chat_models import (
    ChatMessage as ApiChatMessage,
)
from .chat_models import (
    ChatResponse as ApiChatResponse,
)
from .evidence_models import ChatSource


class AppChatService:
    """RESTおよびWebSocket向けのDTO変換を行い、ChatApplicationServiceへ委譲するアダプター。"""

    def __init__(
        self,
        *,
        application_service: ChatApplicationService,
        defaults: Callable[[], GenerationDefaults] = read_generation_defaults,
    ) -> None:
        self._app_service = application_service
        self.defaults = defaults

    @property
    def is_jev_available(self) -> bool:
        return self._app_service.is_jev_available

    @staticmethod
    def sources_to_api(sources: Sequence[Evidence]) -> list[ChatSource]:
        """送信用の根拠DTOを作る。生成処理は元のApplication結果を使用する。"""
        return [evidence_to_api(source) for source in sources]

    async def search_keywords(
        self,
        query: str,
        product_yj_codes: Sequence[str] = (),
    ) -> list[ChatSource]:
        results = await self._app_service.search_keywords(query, product_yj_codes)
        return self.sources_to_api(results)

    async def prepare_reply(
        self,
        conversation: Sequence[ApiChatMessage],
        product_yj_codes: list[str],
        *,
        on_logic_sources: Callable[[list[ChatSource]], Awaitable[None]] | None = None,
    ) -> ApplicationChatResponse:
        pure_conversation = [chat_message_from_api(m) for m in conversation]

        async def publish_logic(sources: list[Evidence]) -> None:
            if on_logic_sources is not None:
                await on_logic_sources(self.sources_to_api(sources))

        pure_reply = await self._app_service.prepare_reply(
            pure_conversation,
            product_yj_codes,
            on_logic_sources=publish_logic if on_logic_sources is not None else None,
        )
        return pure_reply

    async def stream_answer(
        self,
        reply: ApplicationChatResponse,
        conversation: Sequence[ApiChatMessage],
        provider_name: str | None = None,
        model_name: str | None = None,
    ) -> AsyncIterator[str]:
        settings = self.defaults()
        pure_conversation = [chat_message_from_api(m) for m in conversation]
        async with closing_stream(
            self._app_service.stream_answer(
                reply,
                pure_conversation,
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
        pure_reply = await self._app_service.answer_question(
            pure_conversation,
            product_yj_codes,
            provider_name=provider_name or settings.provider,
            model_name=model_name or settings.model,
        )
        return chat_response_to_api(pure_reply)
