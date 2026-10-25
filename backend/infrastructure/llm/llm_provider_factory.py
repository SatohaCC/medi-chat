"""指定された名前に対応する回答生成用の LLM プロバイダーを作成する。"""

from __future__ import annotations

from backend.infrastructure.llm.fallback_provider import FallbackLLMProvider
from backend.infrastructure.llm.gemini_provider import GeminiProvider
from backend.infrastructure.llm.llm_provider_base import LLMProvider
from backend.infrastructure.llm.openai_provider import OpenAIProvider


def create_llm_provider(provider_name: str | None = None) -> LLMProvider:
    """指定された名前（gemini / openai）に対応する LLM プロバイダーを作成する。"""
    name = (provider_name or "gemini").lower().strip()
    if name in {"openai", "gpt"}:
        return FallbackLLMProvider(OpenAIProvider())
    return FallbackLLMProvider(GeminiProvider())
