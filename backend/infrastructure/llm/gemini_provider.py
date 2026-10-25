"""Google Gemini LLM プロバイダー（gemini-3.8-flash を標準利用）"""

from __future__ import annotations

import asyncio
import logging
import os
from collections.abc import AsyncIterator
from typing import Any

from backend.application.chat.queries.services.stream_lifetime import closing_stream
from backend.infrastructure.llm.llm_provider_base import LLMProvider
from backend.infrastructure.llm.llm_provider_errors import (
    LLMRequestError,
    LLMUnavailableError,
)

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None  # type: ignore[assignment]
    types = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)


class GeminiProvider(LLMProvider):
    DEFAULT_MODEL = "gemini-3.8-flash"

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = (
            api_key
            or os.environ.get("GEMINI_API_KEY")
            or os.environ.get("GOOGLE_API_KEY")
        )
        # ユーザー指定の GEMINI_API_KEY とシステムの GOOGLE_API_KEY の競合を防止
        if "GEMINI_API_KEY" in os.environ and "GOOGLE_API_KEY" in os.environ:
            del os.environ["GOOGLE_API_KEY"]

    async def stream_response(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
    ) -> AsyncIterator[str]:
        """Google Gemini API を用いて回答テキストを非同期ストリーミング生成する"""
        target_model = model or self.DEFAULT_MODEL
        if not self.api_key or genai is None or types is None:
            raise LLMUnavailableError("gemini", target_model)
        system_content = next(
            (
                message.get("content", "")
                for message in reversed(messages)
                if message.get("role") == "system" and message.get("content")
            ),
            "",
        )

        client = genai.Client(api_key=self.api_key)

        try:
            # チャットAPI利用向けに過去ターンの履歴を構築（AFC警告の回避）
            conversation_messages = [m for m in messages if m.get("role") != "system"]
            history: list[Any] = [
                types.Content(
                    role="user" if m.get("role") == "user" else "model",
                    parts=[types.Part.from_text(text=m.get("content", ""))],
                )
                for m in conversation_messages[:-1]
            ]
            latest_message = (
                conversation_messages[-1].get("content", "")
                if conversation_messages
                else ""
            )
            config = (
                types.GenerateContentConfig(system_instruction=system_content)
                if system_content
                else None
            )

            max_retries = 3
            last_error: Exception | None = None

            for attempt in range(max_retries):
                started_streaming = False
                try:
                    # clientを再試行全体で共有し、応答streamは各attemptで終了する。
                    chat = client.aio.chats.create(
                        model=target_model, history=history, config=config
                    )
                    response = await chat.send_message_stream(latest_message)
                    async with closing_stream(response) as chunks:
                        async for chunk in chunks:
                            if chunk.text:
                                started_streaming = True
                                yield chunk.text
                    return
                except Exception as exc:
                    last_error = exc
                    if started_streaming:
                        raise LLMRequestError(
                            "gemini", target_model, exc, stream_started=True
                        ) from exc

                    err_str = str(exc)
                    if (
                        "503" in err_str or "UNAVAILABLE" in err_str
                    ) and attempt < max_retries - 1:
                        wait_sec = 1.0 * (attempt + 1)
                        logger.warning(
                            "503 received for %s. Retrying in %ss (attempt %s/%s)...",
                            target_model,
                            wait_sec,
                            attempt + 1,
                            max_retries,
                        )
                        await asyncio.sleep(wait_sec)
                        continue

                    break

            if last_error:
                raise LLMRequestError(
                    "gemini", target_model, last_error
                ) from last_error
        finally:
            try:
                await client.aio.aclose()
            finally:
                client.close()
