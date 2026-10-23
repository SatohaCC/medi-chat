import asyncio

import pytest
from backend.application.retrieval.queries.services.evidence_retrieval import (
    retrieve_evidence,
)
from backend.application.retrieval.values import DetectionSource
from backend.infrastructure.package_insert_definitions.assembly import (
    get_package_insert_definitions,
)
from backend.tests.application.chat.test_answer_preparation import MedicineReader
from backend.tests.application.retrieval.test_evidence_collection import make_evidence
from backend.tests.application.retrieval.test_selected_medicines import (
    NoJev,
    NoKeywords,
)
from backend.tests.support.retrieval_snapshot import FixedSnapshotProvider


@pytest.mark.asyncio
async def test_safety_sections_are_published_before_classification_and_merged():
    release = asyncio.Event()
    calls = []
    published = []

    class Classifier:
        async def classify(self, request):
            await release.wait()
            return await NoJev().classify(request)

    class Reader:
        async def search(self, criteria, medicines):
            calls.append(criteria)
            assert {code for medicine in medicines for code in medicine.yj_codes} == {
                "1234567A0000"
            }
            if criteria.source == DetectionSource.ALWAYS:
                assert tuple(code.value for code in criteria.section_codes) == (
                    "1",
                    "2",
                    "8",
                )
                assert not criteria.keywords and criteria.intent is None
                return tuple(make_evidence(code, code) for code in ("1", "2", "8.1"))
            return (make_evidence("2", "2"),)

    async def publish(sources):
        published.append(sources)
        release.set()

    async with asyncio.timeout(5):
        result = await retrieve_evidence(
            "禁忌を教えて",
            ["1234567A0000"],
            snapshot_provider=FixedSnapshotProvider(MedicineReader(), Reader()),
            intent_classifier=Classifier(),
            keyword_extractor=NoKeywords(),
            intent_policy=get_package_insert_definitions().intent_policy,
            on_logic_sources=publish,
        )
    assert [source.section["code"] for source in published[0]] == ["1", "2", "8.1"]
    assert len(result.sources) == 3
    assert next(
        source for source in result.sources if source.unit_id.value == "2"
    ).retrieved_by == {DetectionSource.ALWAYS, DetectionSource.LOGIC}
    assert sum(c.source == DetectionSource.ALWAYS for c in calls) == 1
    assert result.intent == "contraindications"


@pytest.mark.asyncio
async def test_no_safety_sections_does_not_create_empty_evidence():
    class Reader:
        async def search(self, criteria, medicines):
            return ()

    result = await retrieve_evidence(
        "こんにちは",
        ["1234567A0000"],
        snapshot_provider=FixedSnapshotProvider(MedicineReader(), Reader()),
        intent_classifier=NoJev(),
        keyword_extractor=NoKeywords(),
        intent_policy=get_package_insert_definitions().intent_policy,
    )
    assert result.sources == []


@pytest.mark.asyncio
@pytest.mark.parametrize("blocked_phase", ["search", "publication"])
async def test_detectors_start_while_initial_evidence_is_in_flight(
    monkeypatch, blocked_phase
):
    import backend.application.retrieval.queries.services.evidence_retrieval as retrieval
    from backend.application.retrieval.queries.models import JevDetectionResult

    loop = asyncio.get_running_loop()
    started = {name: asyncio.Event() for name in ("logic", "keyword", "jev")}
    published = []

    async def jev(*args, **kwargs):
        started["jev"].set()
        return JevDetectionResult()

    def fixed(*args):
        loop.call_soon_threadsafe(started["logic"].set)
        return ()

    def morphology(*args):
        loop.call_soon_threadsafe(started["keyword"].set)
        return None

    async def wait_for_detectors():
        async with asyncio.timeout(5):
            await asyncio.gather(*(event.wait() for event in started.values()))

    class Reader:
        async def search(self, criteria, medicines):
            assert criteria.source == DetectionSource.ALWAYS
            if blocked_phase == "search":
                await wait_for_detectors()
            return (make_evidence("warning", "1"),)

    async def publish(sources):
        if blocked_phase == "publication":
            await wait_for_detectors()
        published.append(sources)

    monkeypatch.setattr(retrieval, "detect_jev_criteria", jev)
    monkeypatch.setattr(retrieval, "_detect_fixed_keyword_criteria", fixed)
    monkeypatch.setattr(retrieval, "detect_morphology_criteria", morphology)
    result = await retrieve_evidence(
        "質問",
        ["1234567A0000"],
        snapshot_provider=FixedSnapshotProvider(MedicineReader(), Reader()),
        intent_classifier=NoJev(),
        keyword_extractor=NoKeywords(),
        intent_policy=get_package_insert_definitions().intent_policy,
        on_logic_sources=publish,
    )
    assert len(published) == 1
    assert published[0] == result.sources
    assert all(event.is_set() for event in started.values())


@pytest.mark.asyncio
@pytest.mark.parametrize("entry", ["prepare_reply", "answer_question"])
async def test_custom_always_sections_are_injected_through_chat_service(entry):
    from backend.application.chat.queries.chat import (
        ChatQueries,
    )
    from backend.application.chat.queries.models import ChatMessage
    from backend.application.indexing.values import SearchSectionCode
    from backend.application.retrieval.queries.policies.standard import (
        EvidenceRetrievalPolicy,
    )

    conditions = []

    class Reader:
        async def search(self, criteria, medicines):
            conditions.append(criteria)
            return ()

    class Provider:
        async def stream_response(self, messages, model=None):
            yield "テスト回答"

    definitions = get_package_insert_definitions()
    service = ChatQueries(
        intent_classifier=NoJev(),
        keyword_extractor=NoKeywords(),
        intent_policy=definitions.intent_policy,
        retrieval_policy=EvidenceRetrievalPolicy(
            always_retrieved_sections=(SearchSectionCode("9.2"),)
        ),
        answer_prompt_policy=definitions.answer_prompt_policy,
        snapshot_provider=FixedSnapshotProvider(MedicineReader(), Reader()),
        provider_factory=lambda _: Provider(),
    )
    arguments = (
        {}
        if entry == "prepare_reply"
        else {"provider_name": "test", "model_name": "test"}
    )
    await getattr(service, entry)(
        [ChatMessage(role="user", content="こんにちは")], ["1234567A0000"], **arguments
    )
    assert len(conditions) == 1
    assert conditions[0].source == DetectionSource.ALWAYS
    assert tuple(code.value for code in conditions[0].section_codes) == ("9.2",)
