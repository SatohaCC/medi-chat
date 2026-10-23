"""外部技術に依存しない回答streamの契約。"""

from collections.abc import AsyncIterator
from typing import Protocol


class LLMProvider(Protocol):
    """会話メッセージから回答のチャンクを返すport。"""

    def stream_response(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
    ) -> AsyncIterator[str]:
        raise NotImplementedError
