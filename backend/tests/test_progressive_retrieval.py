"""ローカル根拠の先行通知とJev待機・取消の契約。"""

import asyncio
import threading
from contextlib import asynccontextmanager

import pytest
from backend import main
from backend.application.chat.answer_preparation import prepare_reply
from backend.application.chat.chat_models import ChatMessage
from backend.application.retrieval import retrieve_evidence as retrieval
from backend.application.retrieval.jev_detector import JevDetectionResult
from backend.application.retrieval.snapshot_contracts import RetrievalSnapshot
from backend.domain.retrieval.identifiers import SearchGenerationId
from backend.domain.retrieval.primitives import (
    DetectionSource,
    IntentName,
    SearchKeyword,
)
from backend.domain.retrieval.value_objects import SearchCriteria
from backend.infrastructure.package_insert_definitions.loader import (
    get_package_insert_definitions,
)
from backend.presentation.chat_service import AppChatService
from backend.presentation.chat_websocket_routes import router
from backend.presentation.dependencies import get_chat_service
from backend.tests.registration_runtime_fixtures import (
    register_synthetic_prepared_index,
)
from backend.tests.storage_fixtures import (
    build_document_store,
    write_structured_document,
)
from backend.tests.test_answer_preparation import (
    MedicineReader,
    OrderedEvidenceReader,
    UnusedIntentClassifier,
    UnusedKeywordExtractor,
)
from backend.tests.test_chat_service import RecordingProvider
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.mark.asyncio
@pytest.mark.parametrize("collision", [False, True])
@pytest.mark.parametrize("finish", ["success", "cancel", "callback_error"])
async def test_logic_is_published_while_jev_waits_and_children_are_reclaimed(
    monkeypatch, collision, finish
):
    release = asyncio.Event()
    jev_finished = asyncio.Event()
    published = asyncio.Queue()
    lease_active = False

    class SnapshotProvider:
        @asynccontextmanager
        async def acquire(self):
            nonlocal lease_active
            lease_active = True
            try:
                yield RetrievalSnapshot(
                    generation_id=SearchGenerationId("test-generation"),
                    medicine_reader=MedicineReader(),
                    evidence_reader=OrderedEvidenceReader(collision),
                )
            finally:
                lease_active = False

    async def jev(*args, **kwargs):
        try:
            await release.wait()
            return JevDetectionResult(
                [
                    SearchCriteria(
                        source=DetectionSource.JEV, intent=IntentName("adverse_events")
                    )
                ]
            )
        finally:
            jev_finished.set()

    async def publish(sources):
        assert lease_active
        await published.put(sources)
        if finish == "callback_error":
            raise RuntimeError("send failed")

    monkeypatch.setattr(retrieval, "detect_jev_criteria", jev)
    monkeypatch.setattr(
        retrieval,
        "_detect_fixed_keyword_criteria",
        lambda *args: SearchCriteria(
            source=DetectionSource.LOGIC, intent=IntentName("interaction")
        ),
    )
    monkeypatch.setattr(retrieval, "detect_morphology_criteria", lambda *args: None)
    task = asyncio.create_task(
        prepare_reply(
            [ChatMessage(role="user", content="質問")],
            ["1234567A0000"],
            medicine_reader=MedicineReader(),
            evidence_reader=OrderedEvidenceReader(collision),
            intent_classifier=UnusedIntentClassifier(),
            keyword_extractor=UnusedKeywordExtractor(),
            intent_policy=get_package_insert_definitions().intent_policy,
            on_logic_sources=publish,
            snapshot_provider=SnapshotProvider(),
        )
    )
    try:
        early = await asyncio.wait_for(published.get(), 5)
        assert len(early) == 1
        assert early[0].retrieved_by == frozenset(["logic"])
        if finish == "success":
            assert not task.done()
            release.set()
            reply = await asyncio.wait_for(task, 5)
            assert len(reply.sources) == (1 if collision else 2)
            assert set().union(*(source.retrieved_by for source in reply.sources)) == {
                "logic",
                "jev",
            }
            assert early[0].retrieved_by == frozenset(["logic"])
        elif finish == "cancel":
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
        else:
            with pytest.raises(RuntimeError, match="send failed"):
                await task
        assert jev_finished.is_set()
        assert not lease_active
    finally:
        release.set()
        if not task.done():
            task.cancel()
        await asyncio.gather(task, return_exceptions=True)


@pytest.mark.asyncio
async def test_unresolved_products_do_not_publish_partial_evidence(monkeypatch):
    async def jev(*args, **kwargs):
        return JevDetectionResult()

    async def publish(sources):
        raise AssertionError("確認が必要な製品の根拠を送信してはいけない")

    monkeypatch.setattr(retrieval, "detect_jev_criteria", jev)
    monkeypatch.setattr(retrieval, "detect_morphology_criteria", lambda *args: None)
    reply = await prepare_reply(
        [ChatMessage(role="user", content="質問")],
        ["1234567A0000", "unknown"],
        medicine_reader=MedicineReader(),
        evidence_reader=OrderedEvidenceReader(False),
        intent_classifier=UnusedIntentClassifier(),
        keyword_extractor=UnusedKeywordExtractor(),
        intent_policy=get_package_insert_definitions().intent_policy,
        on_logic_sources=publish,
    )
    assert reply.needs_clarification
    assert reply.sources == []


def test_websocket_sends_logic_before_jev_then_replaces_with_integrated_sources(
    monkeypatch,
):
    release = threading.Event()

    async def jev(*args, **kwargs):
        assert await asyncio.to_thread(release.wait, 5), "Jev was not released"
        return JevDetectionResult(
            [
                SearchCriteria(
                    source=DetectionSource.JEV, intent=IntentName("adverse_events")
                )
            ],
            raw_response={"test": True},
        )

    monkeypatch.setattr(retrieval, "detect_jev_criteria", jev)
    monkeypatch.setattr(
        retrieval,
        "_detect_fixed_keyword_criteria",
        lambda *args: SearchCriteria(
            source=DetectionSource.LOGIC, intent=IntentName("interaction")
        ),
    )
    monkeypatch.setattr(retrieval, "detect_morphology_criteria", lambda *args: None)
    provider = RecordingProvider()
    service = AppChatService(
        medicine_reader=MedicineReader(),
        evidence_reader=OrderedEvidenceReader(True),
        intent_classifier=UnusedIntentClassifier(),
        keyword_extractor=UnusedKeywordExtractor(),
        intent_policy=get_package_insert_definitions().intent_policy,
        answer_prompt_policy=get_package_insert_definitions().answer_prompt_policy,
        provider_factory=lambda _: provider,
    )
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_chat_service] = lambda: service
    try:
        with TestClient(app) as client, client.websocket_connect("/api/ws") as socket:
            socket.send_json(
                {
                    "type": "message",
                    "product_yj_codes": ["1234567A0000"],
                    "messages": [{"role": "user", "content": "質問"}],
                }
            )
            assert socket.receive_json() == {
                "type": "retrieval_status",
                "stage": "jev_searching",
            }
            early = socket.receive_json()
            assert early["type"] == "sources"
            assert early["sources"][0]["retrieved_by"] == ["logic"]
            assert provider.calls == []
            release.set()
            final = socket.receive_json()
            assert final["type"] == "sources"
            assert len(final["sources"]) == 1
            assert set(final["sources"][0]["retrieved_by"]) == {"logic", "jev"}
            assert socket.receive_json()["type"] == "jev_response"
            assert socket.receive_json()["stage"] == "complete"
            assert socket.receive_json()["type"] == "text_delta"
            assert socket.receive_json()["type"] == "text_delta"
            assert socket.receive_json()["type"] == "text_done"
            assert len(provider.calls) == 1
    finally:
        release.set()


@pytest.mark.asyncio
@pytest.mark.parametrize("collision", [False, True])
async def test_fixed_evidence_does_not_wait_for_morphology_and_updates_are_cumulative(
    monkeypatch,
    collision,
):
    morphology_release = threading.Event()
    morphology_started = threading.Event()
    jev_release = asyncio.Event()
    published = asyncio.Queue()
    reader = OrderedEvidenceReader(collision)

    def morphology(*args):
        morphology_started.set()
        assert morphology_release.wait(5)
        return SearchCriteria(
            source=DetectionSource.KEYWORD, keywords=(SearchKeyword("頭痛"),)
        )

    async def jev(*args, **kwargs):
        await jev_release.wait()
        return JevDetectionResult(
            [
                SearchCriteria(
                    source=DetectionSource.JEV, intent=IntentName("adverse_events")
                )
            ]
        )

    monkeypatch.setattr(retrieval, "detect_morphology_criteria", morphology)
    monkeypatch.setattr(retrieval, "detect_jev_criteria", jev)
    monkeypatch.setattr(
        retrieval,
        "_detect_fixed_keyword_criteria",
        lambda *args: SearchCriteria(
            source=DetectionSource.LOGIC, intent=IntentName("interaction")
        ),
    )
    task = asyncio.create_task(
        prepare_reply(
            [ChatMessage(role="user", content="質問")],
            ["1234567A0000"],
            medicine_reader=MedicineReader(),
            evidence_reader=reader,
            intent_classifier=UnusedIntentClassifier(),
            keyword_extractor=UnusedKeywordExtractor(),
            intent_policy=get_package_insert_definitions().intent_policy,
            on_logic_sources=published.put,
        )
    )
    try:
        assert await asyncio.to_thread(morphology_started.wait, 5)
        first = await asyncio.wait_for(published.get(), 5)
        assert {source.unit_id.value for source in first} == (
            {"shared"} if collision else {"logic"}
        )
        assert not task.done()
        morphology_release.set()
        second = await asyncio.wait_for(published.get(), 5)
        assert {source.unit_id.value for source in second} == (
            {"shared"} if collision else {"logic", "keyword"}
        )
        assert set().union(*(source.retrieved_by for source in second)) == {
            "logic",
            "keyword",
        }
        assert not task.done()
        jev_release.set()
        final = await asyncio.wait_for(task, 5)
        assert {source.unit_id.value for source in final.sources} == (
            {"shared"} if collision else {"logic", "keyword", "jev"}
        )
        assert set().union(*(source.retrieved_by for source in final.sources)) == {
            "logic",
            "keyword",
            "jev",
        }
        assert [condition.source for condition in reader.conditions] == [
            "logic",
            "keyword",
            "jev",
        ]
        assert first[0].retrieved_by == frozenset(["logic"])
        # 新しい要求では再検索し、前の要求の結果を使い回さない。
        await prepare_reply(
            [ChatMessage(role="user", content="質問")],
            ["1234567A0000"],
            medicine_reader=MedicineReader(),
            evidence_reader=reader,
            intent_classifier=UnusedIntentClassifier(),
            keyword_extractor=UnusedKeywordExtractor(),
            intent_policy=get_package_insert_definitions().intent_policy,
            on_logic_sources=published.put,
        )
        assert len(reader.conditions) == 6
        assert all(
            sum(condition.source == source for condition in reader.conditions) == 2
            for source in ("logic", "keyword", "jev")
        )
    finally:
        morphology_release.set()
        jev_release.set()
        if not task.done():
            task.cancel()
        await asyncio.gather(task, return_exceptions=True)


def test_startup_initializes_janome_off_event_loop_before_accepting_requests(
    tmp_path, monkeypatch
):
    structured = write_structured_document(tmp_path)
    index = tmp_path / "index.sqlite3"
    build_document_store(structured, index)
    register_synthetic_prepared_index(structured, index)
    initialized = []

    def initialize():
        with pytest.raises(RuntimeError, match="no running event loop"):
            asyncio.get_running_loop()
        initialized.append(True)

    monkeypatch.setattr(main, "get_janome_tokenizer", initialize)
    monkeypatch.setenv("TYPESAFE_API_KEY", "")
    monkeypatch.setenv("JEV_API_KEY", "")
    app = main.create_app(structured, index, import_directory=tmp_path / "imports")
    assert initialized == []
    with TestClient(app) as client:
        assert initialized == [True]
        assert client.get("/health").status_code == 200
