"""OpenAI SDKによるモデル名解決とストリーミング通信。"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator

from .provider_errors import LLMRequestError, LLMUnavailableError
from .provider_interface import LLMProvider

try:
    from openai import AsyncOpenAI
except ImportError:
    AsyncOpenAI = None  # type: ignore[assignment, misc]


class OpenAIProvider(LLMProvider):
    DEFAULT_MODEL = os.environ.get("OPENAI_MODEL", "gpt-6-luna")

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")

    async def stream_response(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
    ) -> AsyncIterator[str]:
        """OpenAI API を用いて回答テキストを非同期ストリーミング生成する"""
        target_model = model or self.DEFAULT_MODEL
        if target_model == "luna":
            target_model = "gpt-6-luna"

        if not self.api_key or AsyncOpenAI is None:
            raise LLMUnavailableError("openai", target_model)

        try:
            client = AsyncOpenAI(api_key=self.api_key)
            try:
                formatted_messages = [
                    {"role": m.get("role", "user"), "content": m.get("content", "")}
                    for m in messages
                ]
                response = await client.chat.completions.create(
                    model=target_model,
                    messages=formatted_messages,  # type: ignore[arg-type]
                    stream=True,
                )
                try:
                    async for chunk in response:  # type: ignore[union-attr]
                        choices = getattr(chunk, "choices", None)
                        if choices:
                            delta = getattr(choices[0], "delta", None)
                            content = getattr(delta, "content", None)
                            if content:
                                yield str(content)
                finally:
                    await response.aclose()  # type: ignore[union-attr]
            finally:
                await client.close()
        except Exception as exc:
            raise LLMRequestError("openai", target_model, exc) from exc
