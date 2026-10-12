"""TC133/134: 実copyASGI/REST両WS、全DTOと同接続次要求。"""

import asyncio
import sqlite3
import threading
from contextlib import asynccontextmanager, closing

import pytest
from backend.application.retrieval.intent_contracts import IntentResult
from backend.application.retrieval.snapshot_contracts import RetrievalSnapshot
from backend.domain.retrieval.primitives import IntentName, Probability
from backend.domain.retrieval.value_objects import IntentCandidate
from backend.main import create_app
from backend.tests.interaction_raw_oracle import DOCUMENTS, ROOT
from backend.tests.test_interaction_xml_oracle import (
    ORACLE,
    assert_prompt_oracle,
    assert_public_source,
)
from backend.tests.test_product_identity_responses import CASES, CONFIRMATIONS
from backend.tests.test_product_identity_retrieval import Keywords, X
from backend.tests.test_registration_publisher import publish
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def public_copy(tmp_path_factory):
    from backend.infrastructure.persistence.registration_publisher import (
        SqliteRegistrationPublisher,
    )
    from backend.infrastructure.sources.attachment_import_store import (
        FileAttachmentImportStore,
    )
    from backend.tests.test_alembic_migrations import _migrate_database

    root = tmp_path_factory.mktemp("identity-public")
    index = root / "copy.sqlite3"
    _migrate_database(index, root)
    pub = SqliteRegistrationPublisher(
        index, FileAttachmentImportStore(root / "imports")
    )
    for doc in [*[x[0] for x in DOCUMENTS], "780069_3961008F1020_1_30"]:
        publish(
            pub, next((ROOT / "data/pmda/originals").glob(f"*/{doc}.xml")).read_bytes()
        )
    return pub


class Classifier:
    def __init__(self, available):
        self.is_available = available

    async def classify(self, request):
        return IntentResult(
            self.is_available,
            {"fixed": True} if self.is_available else None,
            (IntentCandidate(IntentName("interaction"), Probability(1.0)),)
            if self.is_available
            else (),
        )


class Provider:
    def __init__(self):
        self.factory_calls = 0
        self.stream_calls = 0
        self.messages = []

    def factory(self, name):
        self.factory_calls += 1
        return self

    async def stream_response(self, messages, model=None):
        self.stream_calls += 1
        self.messages = messages
        yield "通常回答"
        yield "継続"


class SearchCounter:
    def __init__(self, reader, owner):
        self.reader = reader
        self.owner = owner

    async def search(self, criteria, medicines):
        self.owner.search_calls += 1
        return await self.reader.search(criteria, medicines)


class SnapshotCounter:
    def __init__(self, runtime):
        self.runtime = runtime
        self.search_calls = 0
        self.generations = []

    @asynccontextmanager
    async def acquire(self):
        async with self.runtime.acquire() as s:
            self.generations.append(s.generation_id)
            yield RetrievalSnapshot(
                s.generation_id,
                s.medicine_reader,
                SearchCounter(s.evidence_reader, self),
                s.document_count,
                s.unit_count,
            )


def lease_count(pub):
    with closing(sqlite3.connect(f"{pub.index_path.as_uri()}?mode=ro", uri=True)) as c:
        return c.execute("SELECT count(*) FROM generation_leases").fetchone()[0]


@pytest.fixture
def public_client(public_copy):
    provider = Provider()
    app = create_app(
        public_copy.index_path.parent,
        public_copy.index_path,
        import_directory=public_copy.store.root,
        llm_provider_factory=provider.factory,
    )
    with TestClient(app) as client:
        assert isinstance(client.app, FastAPI)
        service = app.state.chat_service
        counter = SnapshotCounter(service.snapshot_provider)
        service.snapshot_provider = counter
        service.keyword_extractor = Keywords()
        yield client, service, counter, provider


def expected_resolved():
    x = ORACLE[0]
    return [
        {
            "generic_name": x["generic_name"],
            "brand_names": [x["product_name"]],
            "yj_codes": [X],
            "document_ids": [x["document_id"]],
            "matched_aliases": [],
        }
    ]


def assert_normal_sources(sources, available):
    x = ORACLE[0]
    codes = ("10", "10.1", "10.2", "16.7")
    assert [s["unit_id"] for s in sources] == [
        x["sections"][c]["unit_id"] for c in codes
    ]
    for s, c in zip(sources, codes, strict=True):
        assert_public_source(s, x, c)
        assert s["retrieved_by"] == (["logic", "jev"] if available else ["logic"])


@pytest.mark.parametrize("available", [False, True])
@pytest.mark.parametrize("message,codes,strategy", CASES)
def test_tc133_rest_all_fields_zero_search_generation(
    public_client, public_copy, available, message, codes, strategy
):
    client, service, counter, provider = public_client
    service.intent_classifier = Classifier(available)
    r = client.post("/api/chat", json={"message": message, "product_yj_codes": codes})
    assert r.status_code == 200
    intent = (
        "interaction"
        if available or "併用" in message or "飲み合わせ" in message
        else "indications"
    )
    assert r.json() == {
        "answer": CONFIRMATIONS[strategy][0],
        "intent": intent,
        "retrieval_strategy": strategy,
        "resolved_medicines": expected_resolved(),
        "sources": [],
        "needs_clarification": True,
        "notices": [CONFIRMATIONS[strategy][1]],
        "jev_response": {"fixed": True} if available else None,
    }
    assert counter.search_calls == provider.factory_calls == provider.stream_calls == 0
    assert lease_count(public_copy) == 0


def receive_done(ws):
    events = []
    while not events or events[-1]["type"] != "text_done":
        events.append(ws.receive_json())
        assert len(events) < 12, events
    return events


@pytest.mark.parametrize("path", ["/api/ws", "/ws/chat"])
@pytest.mark.parametrize("available", [False, True])
@pytest.mark.parametrize("message,codes,strategy", CASES[:4])
def test_tc134_fixed_end_ping_then_normal_same_connection(
    public_client, public_copy, path, available, message, codes, strategy
):
    client, service, counter, provider = public_client
    service.intent_classifier = Classifier(available)
    with client.websocket_connect(path) as ws:
        ws.send_json(
            {
                "type": "message",
                "product_yj_codes": codes,
                "messages": [
                    {"role": "system", "content": "アマリールの効能"},
                    {"role": "user", "content": message},
                ],
            }
        )
        assert receive_done(ws) == [
            {
                "type": "retrieval_status",
                "stage": "jev_searching" if available else "unavailable",
            },
            {"type": "text_delta", "content": CONFIRMATIONS[strategy][0]},
            {"type": "text_done"},
        ]
        assert (
            counter.search_calls == provider.factory_calls == provider.stream_calls == 0
            and lease_count(public_copy) == 0
        )
        ws.send_json({"type": "ping"})
        assert ws.receive_json() == {"type": "pong"}
        ws.send_json(
            {
                "type": "message",
                "product_yj_codes": [X],
                "messages": [{"role": "user", "content": "イグザレルトの飲み合わせ"}],
            }
        )
        events = receive_done(ws)
        types = [e["type"] for e in events]
        assert types == (
            [
                "retrieval_status",
                "sources",
                "sources",
                "jev_response",
                "retrieval_status",
                "text_delta",
                "text_delta",
                "text_done",
            ]
            if available
            else [
                "retrieval_status",
                "sources",
                "text_delta",
                "text_delta",
                "text_done",
            ]
        )
        assert events[0] == {
            "type": "retrieval_status",
            "stage": "jev_searching" if available else "unavailable",
        }
        assert_normal_sources(events[1]["sources"], False)
        if available:
            assert_normal_sources(events[2]["sources"], True)
            assert events[3] == {"type": "jev_response", "data": {"fixed": True}}
            assert events[4] == {
                "type": "retrieval_status",
                "stage": "complete",
                "jev_response": {"fixed": True},
            }
        assert events[-3:] == [
            {"type": "text_delta", "content": "通常回答"},
            {"type": "text_delta", "content": "継続"},
            {"type": "text_done"},
        ]
        assert (
            provider.factory_calls == provider.stream_calls == 1
            and counter.search_calls == (2 if available else 1)
            and lease_count(public_copy) == 0
        )
        ws.send_json({"type": "ping"})
        assert ws.receive_json() == {"type": "pong"}


@pytest.mark.parametrize("path", ["/api/ws", "/ws/chat"])
def test_tc134_disconnect_during_preparation_releases_real_lease(
    public_client, public_copy, path
):
    client, service, counter, provider = public_client
    entered = threading.Event()

    class BlockingClassifier:
        is_available = True

        async def classify(self, request):
            entered.set()
            await asyncio.Event().wait()
            raise AssertionError("unreachable after cancellation")

    service.intent_classifier = BlockingClassifier()
    with client.websocket_connect(path) as ws:
        ws.send_json(
            {
                "type": "message",
                "product_yj_codes": [X],
                "messages": [{"role": "user", "content": "アマリールの効能"}],
            }
        )
        assert ws.receive_json() == {
            "type": "retrieval_status",
            "stage": "jev_searching",
        }
        assert entered.wait(10) and lease_count(public_copy) == 1
    assert lease_count(public_copy) == 0
    assert counter.search_calls == provider.factory_calls == provider.stream_calls == 0


@pytest.mark.parametrize("available", [False, True])
def test_tc133_normal_rest_full_fields_original_prompt(
    public_client, public_copy, available
):
    client, service, counter, provider = public_client
    service.intent_classifier = Classifier(available)
    response = client.post(
        "/api/chat",
        json={"message": "イグザレルト錠2.5mgの飲み合わせ", "product_yj_codes": [X]},
    )
    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {
        "answer",
        "intent",
        "retrieval_strategy",
        "resolved_medicines",
        "sources",
        "needs_clarification",
        "notices",
        "jev_response",
    }
    assert payload["answer"] == "通常回答継続"
    assert (
        payload["intent"] == "interaction"
        and payload["retrieval_strategy"] == "three_detectors"
    )
    assert payload["resolved_medicines"] == expected_resolved()
    assert payload["needs_clarification"] is False and payload["notices"] == []
    assert payload["jev_response"] == ({"fixed": True} if available else None)
    assert_normal_sources(payload["sources"], available)
    assert_prompt_oracle(provider.messages, ORACLE[:1], history=False)
    assert (
        provider.factory_calls == provider.stream_calls == 1
        and counter.search_calls > 0
        and lease_count(public_copy) == 0
    )
