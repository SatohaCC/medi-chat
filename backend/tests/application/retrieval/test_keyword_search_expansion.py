"""キーワード検索のLLM類似語拡張に関する単体テスト。"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Any

import pytest
from backend.application.retrieval.interfaces.keyword_expander import (
    KeywordExpander,
)
from backend.application.retrieval.queries.policies.selection import (
    build_keyword_search_criteria,
)
from backend.application.retrieval.queries.services.keyword_search import (
    search_evidence_by_keywords,
)
from backend.infrastructure.llm.llm_keyword_expansion_adapter import (
    LLMKeywordExpander,
)
from backend.tests.application.chat.test_answer_preparation import (
    MedicineReader,
)
from backend.tests.support.retrieval_snapshot import FixedSnapshotProvider


class FakeExpander(KeywordExpander):
    def __init__(self, expansions: tuple[str, ...] = ("悪心", "嘔吐")) -> None:
        self.expansions = expansions
        self.called_with: list[str] = []

    async def expand_keywords(self, query: str) -> tuple[str, ...]:
        self.called_with.append(query)
        return self.expansions


class FailingExpander(KeywordExpander):
    async def expand_keywords(self, query: str) -> tuple[str, ...]:
        raise RuntimeError("LLM failure")


class MockEvidenceReader:
    def __init__(self) -> None:
        self.searched_criteria: list[Any] = []

    async def search(self, criteria: Any, medicines: Any) -> tuple[Any, ...]:
        self.searched_criteria.append(criteria)
        return ()


@pytest.mark.asyncio
async def test_keyword_search_with_expand_false_does_not_call_expander() -> None:
    expander = FakeExpander()
    evidence_reader = MockEvidenceReader()
    provider = FixedSnapshotProvider(MedicineReader(), evidence_reader)

    result = await search_evidence_by_keywords(
        "吐き気",
        ["1234567A0000"],
        keyword_expander=expander,
        expand=False,
        snapshot_provider=provider,
    )

    assert expander.called_with == []
    assert result.expanded_keywords == ()
    assert len(evidence_reader.searched_criteria) == 1
    assert tuple(k.value for k in evidence_reader.searched_criteria[0].keywords) == (
        "吐き気",
    )


@pytest.mark.asyncio
async def test_keyword_search_with_expand_true_calls_expander_and_combines_terms() -> (
    None
):
    expander = FakeExpander(("悪心", "嘔吐", "吐き気", "a"))
    evidence_reader = MockEvidenceReader()
    provider = FixedSnapshotProvider(MedicineReader(), evidence_reader)

    result = await search_evidence_by_keywords(
        "吐き気",
        ["1234567A0000"],
        keyword_expander=expander,
        expand=True,
        snapshot_provider=provider,
    )

    assert expander.called_with == ["吐き気"]
    # "吐き気" was in original query, "a" has length < 2, so only "悪心" and "嘔吐" are expanded
    assert result.expanded_keywords == ("悪心", "嘔吐")
    assert len(evidence_reader.searched_criteria) == 1
    searched_words = tuple(
        k.value for k in evidence_reader.searched_criteria[0].keywords
    )
    assert searched_words == ("吐き気", "悪心", "嘔吐")


@pytest.mark.asyncio
async def test_keyword_search_with_expand_true_falls_back_when_expander_fails() -> None:
    expander = FailingExpander()
    evidence_reader = MockEvidenceReader()
    provider = FixedSnapshotProvider(MedicineReader(), evidence_reader)

    result = await search_evidence_by_keywords(
        "吐き気",
        ["1234567A0000"],
        keyword_expander=expander,
        expand=True,
        snapshot_provider=provider,
    )

    assert result.expanded_keywords == ()
    assert len(evidence_reader.searched_criteria) == 1
    assert tuple(k.value for k in evidence_reader.searched_criteria[0].keywords) == (
        "吐き気",
    )


def test_build_keyword_search_criteria_with_additional_keywords() -> None:
    criteria = build_keyword_search_criteria(
        "吐き気", additional_keywords=["悪心", "嘔吐", "吐き気", ""]
    )
    assert criteria is not None
    assert tuple(k.value for k in criteria.keywords) == ("吐き気", "悪心", "嘔吐")


class MockStreamProvider:
    def __init__(self, response_text: str) -> None:
        self.response_text = response_text

    async def stream_response(
        self, messages: list[dict[str, str]], model: str | None = None
    ) -> AsyncIterator[str]:
        yield self.response_text


@pytest.mark.asyncio
async def test_llm_keyword_expander_parses_json_output() -> None:
    provider = MockStreamProvider('```json\n["悪心", "嘔吐", "むかつき"]\n```')
    expander = LLMKeywordExpander(lambda _: provider)

    expanded = await expander.expand_keywords("吐き気")
    assert expanded == ("悪心", "嘔吐", "むかつき")


@pytest.mark.asyncio
async def test_llm_keyword_expander_filters_original_tokens() -> None:
    provider = MockStreamProvider('["吐き気", "悪心", "嘔吐"]')
    expander = LLMKeywordExpander(lambda _: provider)

    expanded = await expander.expand_keywords("吐き気")
    assert expanded == ("悪心", "嘔吐")


@pytest.mark.asyncio
async def test_llm_keyword_expander_handles_timeout() -> None:
    class SlowProvider:
        async def stream_response(
            self, messages: list[dict[str, str]], model: str | None = None
        ) -> AsyncIterator[str]:
            await asyncio.sleep(0.5)
            yield "[]"

    expander = LLMKeywordExpander(lambda _: SlowProvider(), timeout_seconds=0.05)
    expanded = await expander.expand_keywords("吐き気")
    assert expanded == ()
