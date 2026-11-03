"""Three independent evidence tools share one request-owned snapshot."""

import asyncio

import pytest
from backend.application.chat.interfaces.medical_tool import ToolExecutionInput
from backend.application.chat.queries.services.package_insert_tools import (
    PackageInsertTools,
)
from backend.application.retrieval.values import DetectionSource
from backend.infrastructure.package_insert_definitions.definition_assembly import (
    get_package_insert_definitions,
)
from backend.tests.application.chat.test_answer_preparation import MedicineReader
from backend.tests.application.retrieval.test_evidence_collection import make_evidence
from backend.tests.integration.test_langgraph_chat_integration import (
    DummyIntentClassifier,
)
from backend.tests.support.retrieval_snapshot import FixedSnapshotProvider


class Reader:
    def __init__(self):
        self.calls = []

    async def search(self, criteria, medicines):
        self.calls.append(criteria)
        return (make_evidence(criteria.source.value, excerpt=criteria.source.value),)


class Classifier(DummyIntentClassifier):
    calls = 0

    async def classify(self, request):
        self.calls += 1
        return await super().classify(request)


class Extractor:
    calls = 0

    def extract_keywords(self, text):
        self.calls += 1
        assert "商品" not in text
        assert "成分" not in text
        return ("頭痛",)


def provider(medicine_reader=None):
    definitions = get_package_insert_definitions()
    reader, classifier, extractor = Reader(), Classifier(), Extractor()
    snapshot = FixedSnapshotProvider(medicine_reader or MedicineReader(), reader)
    tools = PackageInsertTools(
        snapshot_provider=snapshot,
        intent_classifier=classifier,
        keyword_extractor=extractor,
        intent_policy=definitions.intent_policy,
        retrieval_policy=definitions.retrieval_policy,
    )
    return tools, snapshot, reader, classifier, extractor


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "index,source,detector_calls",
    [
        (0, DetectionSource.LOGIC, (0, 0)),
        (1, DetectionSource.KEYWORD, (0, 1)),
        (2, DetectionSource.JEV, (1, 0)),
    ],
)
async def test_each_tool_uses_only_its_own_detector(index, source, detector_calls):
    tool_provider, snapshot, reader, classifier, extractor = provider()
    request = ToolExecutionInput(
        message="@商品の相互作用と頭痛", product_yj_codes=["1234567A0000"]
    )
    async with tool_provider.acquire(request) as tools:
        assert [t.name for t in tools] == [
            "package_insert_fixed_keyword",
            "package_insert_morphology",
            "package_insert_jev",
        ]
        assert all(t.is_mandatory for t in tools)
        result = await tools[index].execute(request)
        assert result.tool_name == tools[index].name
        assert {condition.source for condition in reader.calls} == {
            DetectionSource.ALWAYS,
            source,
        }
        assert (classifier.calls, extractor.calls) == detector_calls
        assert result.resolved_medicines
        assert not result.needs_clarification
        assert snapshot.entered == 1 and snapshot.exited == 0
    assert snapshot.exited == 1


@pytest.mark.asyncio
async def test_common_safety_is_searched_once_and_progressive_sources_are_cumulative():
    tool_provider, snapshot, reader, classifier, extractor = provider()
    batches = []

    async def publish(sources):
        batches.append(sources)

    request = ToolExecutionInput(
        message="相互作用", product_yj_codes=["1234567A0000"], on_sources=publish
    )
    async with tool_provider.acquire(request) as tools:
        results = await asyncio.gather(*(t.execute(request) for t in tools))
    assert len([c for c in reader.calls if c.source == DetectionSource.ALWAYS]) == 1
    assert len(reader.calls) == len(set(reader.calls))
    assert classifier.calls == extractor.calls == 1
    assert all(
        {s.unit_id for s in earlier} <= {s.unit_id for s in later}
        for earlier, later in zip(batches, batches[1:], strict=False)
    )
    assert {s.retrieved_by for s in batches[-1]} == {
        frozenset({s}) for s in DetectionSource
    }
    assert any(r.jev_response is not None or r.qualifying_intents for r in results)
    assert snapshot.entered == snapshot.exited == 1


@pytest.mark.asyncio
async def test_unregistered_products_do_not_search_or_call_detectors():
    tool_provider, snapshot, reader, classifier, extractor = provider()
    request = ToolExecutionInput(message="相互作用", product_yj_codes=["9999999F9999"])
    async with tool_provider.acquire(request) as tools:
        results = await asyncio.gather(*(t.execute(request) for t in tools))
    assert all(r.needs_clarification and not r.sources for r in results)
    assert reader.calls == []
    assert classifier.calls == extractor.calls == 0
    assert snapshot.entered == snapshot.exited == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("index", [0, 1, 2])
async def test_tools_cannot_use_a_closed_request(index):
    tools_provider, _, reader, classifier, extractor = provider()
    request = ToolExecutionInput(message="相互作用", product_yj_codes=["1234567A0000"])
    async with tools_provider.acquire(request) as tools:
        tool = tools[index]
    with pytest.raises(RuntimeError, match="Retrieval session is closed"):
        await tool.execute(request)
    assert reader.calls == []
    assert classifier.calls == extractor.calls == 0


@pytest.mark.asyncio
async def test_concurrent_requests_do_not_share_search_cache():
    tools_provider, snapshot, reader, classifier, extractor = provider()
    request = ToolExecutionInput(message="相互作用", product_yj_codes=["1234567A0000"])

    async def run():
        async with tools_provider.acquire(request) as tools:
            await asyncio.gather(*(t.execute(request) for t in tools))

    await asyncio.gather(run(), run())
    assert snapshot.entered == snapshot.exited == 2
    assert classifier.calls == extractor.calls == 2
    assert len([c for c in reader.calls if c.source == DetectionSource.ALWAYS]) == 2
