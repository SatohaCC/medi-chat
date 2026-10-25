"""LLMの未設定・通信失敗を、チャット用の代替応答へ変換する。"""

from __future__ import annotations

from collections.abc import AsyncIterator

from backend.application.chat.queries.services.stream_lifetime import closing_stream
from backend.infrastructure.llm.llm_error_messages import format_llm_error
from backend.infrastructure.llm.llm_provider_base import LLMProvider
from backend.infrastructure.llm.llm_provider_errors import (
    LLMRequestError,
    LLMUnavailableError,
)
from backend.infrastructure.llm.mock_response_stream import stream_mock_response


class FallbackLLMProvider(LLMProvider):
    def __init__(self, provider: LLMProvider) -> None:
        self.provider = provider

    async def stream_response(
        self, messages: list[dict[str, str]], model: str | None = None
    ) -> AsyncIterator[str]:
        try:
            async with closing_stream(
                self.provider.stream_response(messages, model=model)
            ) as response:
                async for chunk in response:
                    yield chunk
        except LLMUnavailableError as error:
            async for chunk in stream_mock_response(
                error.provider_name, error.model, messages
            ):
                yield chunk
        except LLMRequestError as error:
            yield format_llm_error(error)
