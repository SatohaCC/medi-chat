"""外部LLMや類義語サービスに依存しないキーワード拡張の契約。"""

from __future__ import annotations

from typing import Protocol


class KeywordExpander(Protocol):
    """検索キーワードから医療用同義語・類義語を生成するport。"""

    async def expand_keywords(self, query: str) -> tuple[str, ...]:
        raise NotImplementedError
