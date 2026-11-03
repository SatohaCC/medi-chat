"""The three mandatory tools run concurrently and release retrieval before generation."""

import asyncio

import pytest
from backend.application.chat.queries.models import ChatMessage
from backend.application.retrieval.queries.models import IntentCandidate, IntentResult
from backend.application.retrieval.queries.services.evidence_retrieval import (
    retrieve_evidence,
)
from backend.application.retrieval.values import IntentName, Probability
from backend.infrastructure.agent.langgraph_chat_agent_adapter import (
    LangGraphChatAgentAdapter,
)
from backend.infrastructure.package_insert_definitions.definition_assembly import (
    get_package_insert_definitions,
)
from backend.tests.application.chat.test_answer_preparation import MedicineReader
from backend.tests.application.chat.test_package_insert_tools import (
    Classifier,
    Extractor,
    Reader,
    provider,
)
from backend.tests.support.retrieval_snapshot import FixedSnapshotProvider
from langchain_core.messages import AIMessage, SystemMessage


@pytest.mark.asyncio
@pytest.mark.parametrize("finish", ["success", "error", "cancel"])
async def test_local_tools_publish_before_jev_and_own_all_children(finish):
    release, started, finished = asyncio.Event(), asyncio.Event(), asyncio.Event()
    published = asyncio.Queue()

    class Medicines(MedicineReader):
        calls = 0

        async def read_medicines(self):
            self.calls += 1
            return await super().read_medicines()

    medicines = Medicines()
    tools, snapshot, reader, _, extractor = provider(medicines)

    class BlockingClassifier(Classifier):
        async def classify(self, request):
            started.set()
            try:
                await release.wait()
                if finish == "error":
                    raise RuntimeError("test detector failed")
                return await super().classify(request)
            finally:
                finished.set()

    tools.intent_classifier = BlockingClassifier()

    class Model:
        calls = 0

        async def ainvoke(self, messages, config=None):
            self.calls += 1
            assert snapshot.entered == snapshot.exited == 1
            prompt = next(m.text for m in messages if isinstance(m, SystemMessage))
            assert all(name in prompt for name in ("always", "logic", "keyword", "jev"))
            return AIMessage(content="テスト回答")

    model = Model()
    definitions = get_package_insert_definitions()
    agent = LangGraphChatAgentAdapter(
        mandatory_tool_provider=tools,
        model=model,
        answer_prompt_policy=definitions.answer_prompt_policy,
    )

    async def publish(sources):
        assert snapshot.exited == 0
        await published.put(sources)

    task = asyncio.create_task(
        agent.run(
            [ChatMessage(role="user", content="相互作用と頭痛")],
            ["1234567A0000"],
            on_sources=publish,
        )
    )
    await asyncio.wait_for(started.wait(), 2)
    first = await asyncio.wait_for(published.get(), 2)
    assert first and not task.done() and not finished.is_set()
    assert model.calls == 0
    if finish == "cancel":
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    elif finish == "error":
        release.set()
        with pytest.raises(RuntimeError, match="test detector failed"):
            await task
    else:
        release.set()
        reply = await task
        legacy_snapshot = FixedSnapshotProvider(MedicineReader(), Reader())
        legacy = await retrieve_evidence(
            "相互作用と頭痛",
            ["1234567A0000"],
            intent_classifier=Classifier(),
            keyword_extractor=Extractor(),
            intent_policy=definitions.intent_policy,
            retrieval_policy=definitions.retrieval_policy,
            snapshot_provider=legacy_snapshot,
        )
        assert reply.sources == legacy.sources
        assert reply.resolved_medicines == legacy.resolved_medicines
        assert reply.intent == legacy.intent
        assert reply.qualifying_intents == legacy.qualifying_intents
        assert reply.jev_response == legacy.jev_response
        assert reply.notices == legacy.notices
        assert model.calls == 1
    assert finished.is_set()
    assert snapshot.entered == snapshot.exited == 1
    assert medicines.calls == 1
    assert extractor.calls == 1 if finish == "success" else extractor.calls <= 1


@pytest.mark.asyncio
async def test_unregistered_product_clarification_never_creates_a_model():
    tools, snapshot, reader, classifier, extractor = provider()
    agent = LangGraphChatAgentAdapter(mandatory_tool_provider=tools)
    reply = await agent.run(
        [ChatMessage(role="user", content="相互作用")], ["9999999F9999"]
    )
    assert reply.needs_clarification and not reply.sources
    assert "YJコード" in reply.answer
    assert reader.calls == []
    assert classifier.calls == extractor.calls == 0
    assert snapshot.entered == snapshot.exited == 1


@pytest.mark.asyncio
async def test_publication_failure_reclaims_detectors_and_closes_snapshot():
    tools, snapshot, _, _, _ = provider()
    stopped = asyncio.Event()

    class BlockingClassifier(Classifier):
        async def classify(self, request) -> IntentResult:
            try:
                await asyncio.Event().wait()
                raise AssertionError("Blocking fixture released unexpectedly")
            finally:
                stopped.set()

    tools.intent_classifier = BlockingClassifier()
    agent = LangGraphChatAgentAdapter(mandatory_tool_provider=tools)

    async def publish(sources):
        raise RuntimeError("test send failed")

    with pytest.raises(RuntimeError, match="test send failed"):
        await agent.run(
            [ChatMessage(role="user", content="相互作用")],
            ["1234567A0000"],
            on_sources=publish,
        )
    assert stopped.is_set()
    assert snapshot.entered == snapshot.exited == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("scenario", ["unavailable", "general", "multiple", "partial"])
async def test_tool_split_preserves_classification_and_partial_product_semantics(
    scenario,
):
    definitions = get_package_insert_definitions()

    class ScenarioClassifier(Classifier):
        async def classify(self, request):
            if scenario == "unavailable":
                return IntentResult(is_available=False)
            labels = (
                ((definitions.intent_policy.general_intent.value, 1.0),)
                if scenario == "general"
                else (("interaction", 0.6), ("dosage", 0.4))
            )
            return IntentResult(
                is_available=True,
                candidates=tuple(
                    IntentCandidate(
                        intent=IntentName(label), probability=Probability(score)
                    )
                    for label, score in labels
                ),
                choice=labels[0][0],
                raw_response={"test": scenario},
                publish_selection=True,
            )

    tools, _, _, _, _ = provider()
    tools.intent_classifier = ScenarioClassifier()

    class Model:
        async def ainvoke(self, messages, config=None):
            return AIMessage(content="テスト回答")

    codes = ["1234567A0000"] + (["9999999F9999"] if scenario == "partial" else [])
    message = "相互作用と頭痛"
    reply = await LangGraphChatAgentAdapter(
        mandatory_tool_provider=tools, model=Model()
    ).run([ChatMessage(role="user", content=message)], codes)
    original = await retrieve_evidence(
        message,
        codes,
        intent_classifier=ScenarioClassifier(),
        keyword_extractor=Extractor(),
        intent_policy=definitions.intent_policy,
        retrieval_policy=definitions.retrieval_policy,
        snapshot_provider=FixedSnapshotProvider(MedicineReader(), Reader()),
    )
    assert reply.sources == original.sources
    assert reply.intent == original.intent
    assert reply.qualifying_intents == original.qualifying_intents
    assert reply.jev_response == original.jev_response
    assert reply.resolved_medicines == original.resolved_medicines
    assert reply.notices == original.notices
