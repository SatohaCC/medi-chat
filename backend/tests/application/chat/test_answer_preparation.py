"""DM-08/12/13: 製品確認と判定完了順に依存する現行契約。"""

import asyncio
import itertools
import threading
from copy import deepcopy

import pytest
from backend.application.chat import answer_preparation as preparation
from backend.application.chat.chat_models import ChatMessage
from backend.application.medicine.product_models import RegisteredMedicine
from backend.application.retrieval import retrieve_evidence as retrieval
from backend.application.retrieval.intent_contracts import IntentRequest, IntentResult
from backend.application.retrieval.jev_detector import JevDetectionResult
from backend.application.retrieval.search_models import SearchCriteria
from backend.application.retrieval.search_values import (
    DetectionSource,
    IntentName,
    SearchKeyword,
)
from backend.domain.attachment.identifiers import DocumentId
from backend.domain.attachment.primitives import PmdaUrl
from backend.domain.attachment.value_objects import (
    AttachmentProductRevision,
    MedicineDocumentReference,
)
from backend.domain.medicine.entities import MedicineProduct
from backend.domain.medicine.identifiers import YjCode
from backend.domain.medicine.primitives import (
    BrandName,
    GenericName,
)
from backend.domain.medicine.value_objects import MedicineNames
from backend.infrastructure.package_insert_definitions.assembly import (
    get_package_insert_definitions,
)
from backend.tests.application.retrieval.test_evidence_collection import make_evidence
from backend.tests.support.retrieval_snapshot import FixedSnapshotProvider


class MedicineReader:
    async def read_medicines(self):
        return (
            RegisteredMedicine(
                medicine=MedicineProduct(
                    yj_code=YjCode("1234567A0000"),
                    names=MedicineNames(
                        brand_name=BrandName("商品"),
                        generic_name=GenericName("成分"),
                        english_name=None,
                        hiragana_name=None,
                    ),
                ),
                reference=MedicineDocumentReference(
                    document_id=DocumentId("document"),
                    pmda_url=PmdaUrl("https://example.test"),
                    revision=AttachmentProductRevision({}),
                ),
            ),
        )


class UnusedIntentClassifier:
    async def classify(self, request: IntentRequest) -> IntentResult:
        raise AssertionError("controlled detector must not call the classifier")


class UnusedKeywordExtractor:
    def extract_keywords(self, text: str) -> tuple[str, ...]:
        raise AssertionError("controlled detector must not call the extractor")


class DetectorFailure(RuntimeError):
    pass


@pytest.mark.asyncio
@pytest.mark.parametrize("failure_source", ["intent", "morphology", "cancel"])
async def test_preparation_failure_and_cancel_reclaim_async_children_and_release_threads(
    monkeypatch, failure_source
):
    release_thread = threading.Event()
    thread_started = threading.Event()
    thread_finished = threading.Event()
    release_intent = asyncio.Event()
    intent_started = asyncio.Event()
    intent_finished = asyncio.Event()
    children = []
    original_create_task = asyncio.create_task

    class IntentClassifier:
        async def classify(self, request: IntentRequest) -> IntentResult:
            intent_started.set()
            try:
                await release_intent.wait()
                raise DetectorFailure("intent failed")
            finally:
                intent_finished.set()

    class KeywordExtractor:
        def extract_keywords(self, text: str) -> tuple[str, ...]:
            thread_started.set()
            try:
                assert release_thread.wait(5), "worker not released"
                if failure_source == "morphology":
                    raise DetectorFailure("morphology failed")
                return ()
            finally:
                thread_finished.set()

    def track_task(coroutine):
        task = original_create_task(coroutine)
        children.append(task)
        return task

    monkeypatch.setattr(retrieval.asyncio, "create_task", track_task)
    task = original_create_task(
        preparation.prepare_reply(
            [ChatMessage(role="user", content="質問")],
            ["1234567A0000"],
            snapshot_provider=FixedSnapshotProvider(
                MedicineReader(), OrderedEvidenceReader(False)
            ),
            intent_classifier=IntentClassifier(),
            keyword_extractor=KeywordExtractor(),
            intent_policy=get_package_insert_definitions().intent_policy,
        )
    )
    try:
        await asyncio.wait_for(intent_started.wait(), 5)
        assert await asyncio.to_thread(thread_started.wait, 5)
        if failure_source == "intent":
            release_intent.set()
        elif failure_source == "morphology":
            release_thread.set()
        else:
            task.cancel()
        with pytest.raises(
            asyncio.CancelledError if failure_source == "cancel" else DetectorFailure
        ):
            await asyncio.wait_for(task, 5)
        assert intent_finished.is_set()
        assert len(children) == 3 and all(child.done() for child in children)
        assert not task.cancelled() if failure_source != "cancel" else task.cancelled()
    finally:
        release_thread.set()
        release_intent.set()
        if not task.done():
            task.cancel()
        await asyncio.gather(task, return_exceptions=True)
        assert await asyncio.to_thread(thread_finished.wait, 5)


class OrderedEvidenceReader:
    def __init__(self, collision):
        self.collision = collision
        self.conditions = []

    async def search(self, criteria, medicines):
        if criteria.source == DetectionSource.ALWAYS:
            return ()
        self.conditions.append(criteria)
        return (
            make_evidence(
                "shared" if self.collision else criteria.source,
                {"logic": "10.1", "jev": "11.1", "keyword": "9.4"}[criteria.source],
                f"{criteria.source}の原文",
            ),
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "order", list(itertools.permutations(("logic", "jev", "keyword")))
)
@pytest.mark.parametrize("collision", [False, True])
async def test_detector_completion_order_preserves_intent_and_first_content(
    monkeypatch, order, collision
):
    releases = {source: threading.Event() for source in ("logic", "keyword")}
    jev_release = asyncio.Event()
    consumed = asyncio.Queue()
    original_as_completed = asyncio.as_completed

    def controlled_completion(tasks):
        async def observe(completed):
            result = await completed
            consumed.put_nowait(None)
            return result

        return (observe(completed) for completed in original_as_completed(tasks))

    async def jev(*args, **kwargs):
        await jev_release.wait()
        return JevDetectionResult(
            [
                SearchCriteria(
                    source=DetectionSource("jev"), intent=IntentName("adverse_events")
                )
            ]
        )

    def fixed(*args):
        assert releases["logic"].wait(5), "fixed detector was not released"
        return (
            SearchCriteria(
                source=DetectionSource("logic"), intent=IntentName("interaction")
            ),
        )

    def morphology(*args):
        assert releases["keyword"].wait(5), "keyword detector was not released"
        return SearchCriteria(
            source=DetectionSource("keyword"),
            intent=IntentName("pregnancy"),
            keywords=(SearchKeyword("症状"),),
        )

    monkeypatch.setattr(retrieval, "detect_jev_criteria", jev)
    monkeypatch.setattr(retrieval, "_detect_fixed_keyword_criteria", fixed)
    monkeypatch.setattr(retrieval, "detect_morphology_criteria", morphology)
    monkeypatch.setattr(retrieval.asyncio, "as_completed", controlled_completion)
    reader = OrderedEvidenceReader(collision)
    task = asyncio.create_task(
        preparation.prepare_reply(
            [ChatMessage(role="user", content="質問")],
            ["1234567A0000"],
            snapshot_provider=FixedSnapshotProvider(MedicineReader(), reader),
            intent_classifier=UnusedIntentClassifier(),
            keyword_extractor=UnusedKeywordExtractor(),
            intent_policy=get_package_insert_definitions().intent_policy,
        )
    )
    try:
        for source in order:
            if source == "jev":
                jev_release.set()
            else:
                releases[source].set()
            await asyncio.wait_for(consumed.get(), 5)
        reply = await asyncio.wait_for(task, 5)
    finally:
        jev_release.set()
        for release in releases.values():
            release.set()
        if not task.done():
            task.cancel()
        await asyncio.gather(task, return_exceptions=True)

    assert [condition.source for condition in reader.conditions] == list(order)
    names = {"logic": "interaction", "jev": "adverse_events", "keyword": "pregnancy"}
    assert reply.intent == ", ".join(names[source] for source in order)
    if collision:
        assert len(reply.sources) == 1
        assert reply.sources[0].excerpt.value == f"{order[0]}の原文"
        assert reply.sources[0].retrieved_by == frozenset(["logic", "jev", "keyword"])
    else:
        assert [source.unit_id.value for source in reply.sources] == [
            "keyword",
            "logic",
            "jev",
        ]
        assert [source.excerpt.value for source in reply.sources] == [
            "keywordの原文",
            "logicの原文",
            "jevの原文",
        ]


@pytest.mark.asyncio
async def test_partially_unresolved_products_preserve_resolved_medicine_and_skip_search(
    monkeypatch,
):
    async def jev(*args, **kwargs):
        return JevDetectionResult(raw_response={"error": "検出器エラー"})

    monkeypatch.setattr(retrieval, "detect_jev_criteria", jev)
    monkeypatch.setattr(retrieval, "detect_morphology_criteria", lambda *args: None)
    reader = OrderedEvidenceReader(False)
    codes = ["1234567A0000", "0000000A0000"]
    before = deepcopy(codes)
    reply = await preparation.prepare_reply(
        [ChatMessage(role="user", content="質問")],
        codes,
        snapshot_provider=FixedSnapshotProvider(MedicineReader(), reader),
        intent_classifier=UnusedIntentClassifier(),
        keyword_extractor=UnusedKeywordExtractor(),
        intent_policy=get_package_insert_definitions().intent_policy,
    )
    assert reply.needs_clarification is False
    assert reply.resolved_medicines[0].yj_codes == ("1234567A0000",)
    assert reply.resolved_medicines[0].document_ids == ("document",)
    assert reply.jev_response == {"error": "検出器エラー"}
    assert codes == before

    all_unknown_reply = await preparation.prepare_reply(
        [ChatMessage(role="user", content="質問")],
        ["0000000A0000"],
        snapshot_provider=FixedSnapshotProvider(MedicineReader(), reader),
        intent_classifier=UnusedIntentClassifier(),
        keyword_extractor=UnusedKeywordExtractor(),
        intent_policy=get_package_insert_definitions().intent_policy,
    )
    assert all_unknown_reply.needs_clarification is True
    assert all_unknown_reply.resolved_medicines == []
    assert (
        all_unknown_reply.answer
        == "指定されたYJコードのすべてに対応する電子添文が、現在の検索データにありません。"
    )
