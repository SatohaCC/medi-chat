"""API層のチャットモデルとapplicationの会話ユースケースをつなぐアダプター。"""

from __future__ import annotations

from collections.abc import AsyncGenerator, Awaitable, Callable, Sequence
from contextlib import aclosing as closing_stream
from uuid import UUID

from langsmith import trace, traceable
from langsmith.run_trees import RunTree
from langsmith.utils import tracing_is_enabled

from backend.application.chat.queries.chat import (
    ChatQueries,
)
from backend.application.chat.queries.models import (
    ChatResponse as ApplicationChatResponse,
)
from backend.application.retrieval.queries.models import Evidence

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
        application_service: ChatQueries,
        defaults: Callable[[], GenerationDefaults] = read_generation_defaults,
        feedback_token_issuer: Callable[[UUID, str, str], str] | None = None,
    ) -> None:
        self._app_service = application_service
        self.defaults = defaults
        self._feedback_token_issuer = feedback_token_issuer

    def _completed_feedback_token(
        self, run: RunTree | None, user_id: str
    ) -> str | None:
        if (
            self._feedback_token_issuer is None
            or not user_id
            or run is None
            or not run.session_name
            or tracing_is_enabled() is not True
        ):
            return None
        return self._feedback_token_issuer(run.id, run.session_name, user_id)

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

    @traceable(name="medi_chat.prepare_reply", run_type="chain")
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
        *,
        user_id: str = "",
        on_completed: Callable[[str | None], None] | None = None,
    ) -> AsyncGenerator[str]:
        settings = self.defaults()
        pure_conversation = [chat_message_from_api(m) for m in conversation]
        user_query = next(
            (m.content for m in reversed(conversation) if m.role == "user"), ""
        )
        api_sources = self.sources_to_api(reply.sources)
        with trace(
            "medi_chat.stream_answer",
            "chain",
            metadata={"user_id": user_id} if user_id else None,
            inputs={
                "question": user_query,
                "conversation": [
                    {"role": m.role, "content": m.content} for m in conversation
                ],
                "intent": reply.intent,
                "retrieval_strategy": reply.retrieval_strategy,
                "evidence_sources": [
                    {
                        "section": f"{s.section.get('code', '')} {s.section.get('title', '')}".strip(),
                        "product_name": s.product_name,
                        "generic_name": s.generic_name,
                        "excerpt": s.excerpt,
                        "url": s.url,
                    }
                    for s in api_sources
                ],
                "evidence_count": len(api_sources),
                "resolved_medicines": [
                    {
                        "generic_name": getattr(m, "generic_name", ""),
                        "brand_names": [b.value for b in m.medicine.brand_names]
                        if getattr(m, "medicine", None)
                        and getattr(m.medicine, "brand_names", None)
                        else getattr(m, "brand_names", []),
                    }
                    for m in reply.resolved_medicines
                ],
                "provider": provider_name or settings.provider,
                "model": model_name or settings.model,
            },
        ) as run:
            output_chunks: list[str] = []
            try:
                async with closing_stream(
                    self._app_service.stream_answer(
                        reply,
                        pure_conversation,
                        provider_name=provider_name or settings.provider,
                        model_name=model_name or settings.model,
                    )
                ) as response:
                    async for chunk in response:
                        output_chunks.append(chunk)
                        yield chunk
            finally:
                if run is not None and not getattr(run, "end_time", None):
                    run.end(outputs={"answer": "".join(output_chunks)})
        if on_completed is not None:
            on_completed(self._completed_feedback_token(run, user_id))

    async def answer_question(
        self,
        conversation: Sequence[ApiChatMessage],
        product_yj_codes: list[str],
        provider_name: str | None = None,
        model_name: str | None = None,
        *,
        user_id: str = "",
    ) -> ApiChatResponse:
        pure_conversation = [chat_message_from_api(m) for m in conversation]
        settings = self.defaults()
        with trace(
            "medi_chat.answer_question",
            "chain",
            metadata={"user_id": user_id} if user_id else None,
            inputs={
                "conversation": [
                    {"role": m.role, "content": m.content} for m in conversation
                ],
                "product_yj_codes": product_yj_codes,
            },
        ) as run:
            pure_reply = await self._app_service.answer_question(
                pure_conversation,
                product_yj_codes,
                provider_name=provider_name or settings.provider,
                model_name=model_name or settings.model,
            )
            response = chat_response_to_api(pure_reply)
            if run is not None:
                run.end(outputs=response.model_dump())
        response.feedback_token = self._completed_feedback_token(run, user_id)
        return response
