"""Own native chat-model SDK clients for exactly one agent request."""

import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from langchain_core.language_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_openai._compat import httpx as openai_httpx

from backend.config.generation_settings import read_generation_defaults


@asynccontextmanager
async def create_agent_model(
    provider_name: str | None,
    model_name: str | None,
) -> AsyncGenerator[BaseChatModel]:
    defaults = read_generation_defaults()
    provider = provider_name or defaults.provider
    if provider not in {"openai", "gemini"}:
        raise ValueError(f"Unsupported agent provider: {provider}")
    settings = defaults.resolve(provider_name, model_name)
    target = settings.model
    if provider == "openai":
        model = ChatOpenAI(
            model="gpt-6-luna" if target == "luna" else target,
            # An unhashable Timeout bypasses langchain_openai's shared client cache.
            timeout=openai_httpx.Timeout(45),
            max_retries=1,
            max_completion_tokens=4096,
        )
        try:
            yield model
        finally:
            try:
                await model.root_async_client.close()
            finally:
                model.root_client.close()
    else:
        google = ChatGoogleGenerativeAI(
            model=target,
            api_key=os.environ.get("GEMINI_API_KEY")
            or os.environ.get("GOOGLE_API_KEY"),
            vertexai=False,
            timeout=45,
            retries=2,
            max_output_tokens=4096,
        )
        try:
            yield google
        finally:
            await google.aclose()
