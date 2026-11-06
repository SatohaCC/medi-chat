"""LLMを用いた添付文書検索キーワードの同義語・類義語拡張。"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from collections.abc import Callable
from typing import Any

from backend.application.chat.interfaces.llm_provider import LLMProvider
from backend.application.retrieval.interfaces.keyword_expander import (
    KeywordExpander,
)

logger = logging.getLogger(__name__)

_DEFAULT_EXPANDER_TIMEOUT = 4.0

_EXPANSION_SYSTEM_PROMPT = (
    "あなたは添付文書検索の専門アシスタントです。\n"
    "ユーザーが入力した検索語について、添付文書（電子添文）の検索精度を向上させるための「医学的同義語・類義語・正式病名・症状名」を2〜4語生成してください。\n"
    "関連しない疾患名や薬効群へ過剰に連想を広げないでください。\n"
    '結果はJSON配列形式のみで出力してください。例: ["悪心", "嘔吐"]'
)


class LLMKeywordExpander(KeywordExpander):
    """LLMを用いて検索語から添付文書向け類義語を生成する実装。"""

    def __init__(
        self,
        provider_factory: Callable[[str | None], LLMProvider],
        *,
        provider_name: str | None = "openai",
        model_name: str | None = "gpt-6-luna",
        timeout_seconds: float = _DEFAULT_EXPANDER_TIMEOUT,
    ) -> None:
        self._provider_factory = provider_factory
        self._provider_name = provider_name
        self._model_name = model_name
        self._timeout_seconds = timeout_seconds

    async def expand_keywords(self, query: str) -> tuple[str, ...]:
        """検索キーワードから医療用同義語・類義語を生成する。"""
        stripped = query.strip()
        if len(stripped) < 2:
            return ()

        try:
            return await asyncio.wait_for(
                self._generate_expansion(stripped),
                timeout=self._timeout_seconds,
            )
        except TimeoutError:
            logger.warning(
                "Keyword expansion timed out after %s seconds for query: %s",
                self._timeout_seconds,
                stripped,
            )
            return ()
        except Exception as exc:
            logger.warning(
                "Keyword expansion failed for query %r: %s",
                stripped,
                exc,
                exc_info=True,
            )
            return ()

    async def _generate_expansion(self, query: str) -> tuple[str, ...]:
        provider = self._provider_factory(self._provider_name)
        # FallbackLLMProvider によるモック対話・エラー文字列出力を防ぎ、エラー時は例外を伝播させる
        raw_provider = getattr(provider, "provider", provider)
        messages = [
            {"role": "system", "content": _EXPANSION_SYSTEM_PROMPT},
            {"role": "user", "content": f"検索キーワード: {query}"},
        ]
        chunks: list[str] = []
        async for chunk in raw_provider.stream_response(
            messages, model=self._model_name
        ):
            if chunk:
                chunks.append(chunk)

        raw_output = "".join(chunks).strip()
        return self._parse_expanded_keywords(raw_output, query)

    @staticmethod
    def _parse_expanded_keywords(output: str, original_query: str) -> tuple[str, ...]:
        original_terms = {
            t.lower()
            for raw in re.split(r"[\s　]+", original_query)
            if (t := raw.strip())
        }

        match = re.search(r"\[.*?\]", output, re.DOTALL)
        if not match:
            return ()

        try:
            parsed: Any = json.loads(match.group(0))
            if isinstance(parsed, list):
                terms = [
                    t
                    for x in parsed
                    if isinstance(x, str)
                    and 2 <= len(t := x.strip()) <= 30
                    and "\n" not in t
                    and not any(
                        marker in t
                        for marker in ("モック", "APIキー", "エラー", "【", "】")
                    )
                    and t.lower() not in original_terms
                ]
                if terms:
                    return tuple(list(dict.fromkeys(terms))[:4])
        except Exception:
            pass

        return ()
