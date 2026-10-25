import asyncio

import pytest
from backend.application.retrieval.queries.models import IntentResult
from backend.application.retrieval.queries.services.evidence_retrieval import (
    retrieve_evidence,
)
from backend.infrastructure.package_insert_definitions.definition_assembly import (
    get_package_insert_definitions,
)
from backend.tests.application.chat.test_answer_preparation import MedicineReader
from backend.tests.application.retrieval.test_evidence_collection import make_evidence
from backend.tests.support.retrieval_snapshot import FixedSnapshotProvider


class NoKeywords:
    def extract_keywords(self, text):
        return ()


@pytest.mark.asyncio
async def test_all_logic_conditions_reach_search_and_progressive_results_without_duplicates():
    calls = []
    published = []
    release_jev = asyncio.Event()

    class Classifier:
        async def classify(self, request):
            await release_jev.wait()
            return IntentResult(is_available=False)

    class Reader:
        async def search(self, criteria, medicines):
            if criteria.intent is None:
                return ()
            calls.append(criteria.intent.value)
            return (
                make_evidence("shared", "10.1", "共通の原文"),
                make_evidence(criteria.intent.value, "11.1", "分類ごとの原文"),
            )

    async def publish(sources):
        published.append(sources)
        release_jev.set()

    async with asyncio.timeout(5):
        result = await retrieve_evidence(
            "副作用と飲み合わせを教えて",
            ["1234567A0000"],
            snapshot_provider=FixedSnapshotProvider(MedicineReader(), Reader()),
            intent_classifier=Classifier(),
            keyword_extractor=NoKeywords(),
            intent_policy=get_package_insert_definitions().intent_policy,
            on_logic_sources=publish,
        )
    assert set(calls) == {"interaction", "adverse_events", "indications"}
    assert len(calls) == 3  # final retrieval reuses already-published searches
    assert len(result.sources) == 4  # one shared + one for each classification
    assert len(published) == 1
    assert published[-1] == result.sources
