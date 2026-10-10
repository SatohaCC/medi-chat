"""LLMプロバイダーの抽象基底クラス"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator


class LLMProvider(ABC):
    @abstractmethod
    async def stream_response(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
    ) -> AsyncIterator[str]:
        """レスポンスチャンクを非同期ストリーミングで生成する"""
        yield ""
