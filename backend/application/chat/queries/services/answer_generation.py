"""LLMProviderの契約を用いた回答stream。"""

from collections.abc import AsyncIterator

from backend.application.chat.interfaces.llm_provider import LLMProvider
from backend.application.chat.queries.services.stream_lifetime import closing_stream


async def stream_answer(
    provider: LLMProvider,
    messages: list[dict[str, str]],
    model: str | None = None,
) -> AsyncIterator[str]:
    """注入されたproviderの回答チャンクを順番に返す。"""
    async with closing_stream(
        provider.stream_response(messages, model=model)
    ) as response:
        async for chunk in response:
            yield chunk
