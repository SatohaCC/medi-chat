"""LLMが未設定の場合に返す、開発用の代替応答。"""

from __future__ import annotations

import asyncio
import re
from collections.abc import AsyncIterator


async def stream_mock_response(
    provider_name: str, model: str, messages: list[dict[str, str]]
) -> AsyncIterator[str]:
    last_user_message = ""
    system_content = ""
    for message in reversed(messages):
        if message.get("role") == "user" and not last_user_message:
            last_user_message = message.get("content", "")
        elif message.get("role") == "system" and not system_content:
            system_content = message.get("content", "")
    sources_count = len(re.findall(r"\[根拠 \d+\]", system_content))
    grounding_info = (
        f"（添付文書の根拠: {sources_count}件を受信）\n\n" if sources_count > 0 else ""
    )
    if provider_name == "openai":
        label, api_name, key_name = "OpenAI", "OpenAI", "OPENAI_API_KEY"
    else:
        label, api_name, key_name = "Gemini", "Google Gemini", "GEMINI_API_KEY"
    mock_text = (
        f"【{label} ({model}) モック対話】\n\n"
        f"{grounding_info}"
        f"APIキーがまだ設定されていません。受信メッセージ: 「{last_user_message}」\n\n"
        f"`.env.local` または環境変数に `{key_name}` を設定すると、実際の{api_name} APIとリアルタイムで対話できます。"
    )
    for char in mock_text:
        await asyncio.sleep(0.005)
        yield char
