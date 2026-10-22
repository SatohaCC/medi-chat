"""DM-22/23/24: 実組立経路の所有終了と設定優先順位。"""

import asyncio
from collections.abc import AsyncGenerator

import pytest
from backend.application.chat.chat_models import ChatResponse
from backend.application.chat.chat_service import ChatApplicationService
from backend.infrastructure.package_insert_definitions.loader import (
    get_package_insert_definitions,
)
from backend.presentation.chat_models import ChatMessage
from backend.presentation.chat_service import AppChatService
from backend.tests.application.chat.test_answer_preparation import (
    MedicineReader,
    UnusedIntentClassifier,
    UnusedKeywordExtractor,
)
from backend.tests.infrastructure.intent.test_jev_intent_mapping import RecordingReader
from backend.tests.support.postgres_fixtures import pg_api as pg_api
from backend.tests.support.postgres_fixtures import pg_engines as pg_engines
from backend.tests.support.retrieval_snapshot import FixedSnapshotProvider


class RecordingProvider:
    def __init__(self):
        self.closed = False
        self.models = []

    async def stream_response(self, messages, model=None):
        self.models.append(model)
        try:
            yield "first"
            await asyncio.Event().wait()
        finally:
            self.closed = True


@pytest.mark.asyncio
@pytest.mark.parametrize("explicit", [False, True])
async def test_api_service_closes_owned_stream_and_preserves_generation_defaults(
    monkeypatch, explicit
):
    monkeypatch.setenv("DEFAULT_PROVIDER", "gemini")
    monkeypatch.setenv("DEFAULT_MODEL", "default-model")
    provider = RecordingProvider()
    names = []

    def factory(name):
        names.append(name)
        return provider

    service = AppChatService(
        application_service=ChatApplicationService(
            snapshot_provider=FixedSnapshotProvider(
                MedicineReader(), RecordingReader()
            ),
            intent_classifier=UnusedIntentClassifier(),
            keyword_extractor=UnusedKeywordExtractor(),
            intent_policy=get_package_insert_definitions().intent_policy,
            answer_prompt_policy=get_package_insert_definitions().answer_prompt_policy,
            provider_factory=factory,
        )
    )
    reply = ChatResponse(
        answer="", intent="document_search", retrieval_strategy="three_detectors"
    )
    stream = service.stream_answer(
        reply,
        [ChatMessage(role="user", content="質問")],
        "openai" if explicit else None,
        "explicit-model" if explicit else None,
    )
    assert await anext(stream) == "first"
    assert isinstance(stream, AsyncGenerator)
    await stream.aclose()
    assert names == (["openai"] if explicit else ["gemini"])
    assert provider.models == (["explicit-model"] if explicit else ["default-model"])
    assert provider.closed is True


def test_application_lifespan_closes_owned_intent_sdk(pg_api, monkeypatch):
    from backend import main
    from fastapi.testclient import TestClient

    class OwnedClassifier(UnusedIntentClassifier):
        is_available = False
        closed = False

        async def aclose(self):
            self.closed = True

    classifier = OwnedClassifier()
    monkeypatch.setattr(main, "JevIntentClassifier", lambda **kwargs: classifier)
    with TestClient(pg_api()) as client:
        assert client.get("/health").status_code == 200
        assert classifier.closed is False
    assert classifier.closed is True


@pytest.mark.asyncio
async def test_prepared_application_reply_is_retained_until_generation(monkeypatch):
    from unittest.mock import AsyncMock

    definitions = get_package_insert_definitions()
    service = AppChatService(
        application_service=ChatApplicationService(
            snapshot_provider=FixedSnapshotProvider(
                MedicineReader(), RecordingReader()
            ),
            intent_classifier=UnusedIntentClassifier(),
            keyword_extractor=UnusedKeywordExtractor(),
            intent_policy=definitions.intent_policy,
            answer_prompt_policy=definitions.answer_prompt_policy,
            provider_factory=lambda _: RecordingProvider(),
        )
    )
    prepared = ChatResponse(
        answer="",
        intent="interaction",
        retrieval_strategy="three_detectors",
        qualifying_intents=("interaction",),
        jev_response=None,
    )
    monkeypatch.setattr(
        service._app_service, "prepare_reply", AsyncMock(return_value=prepared)
    )
    received = []

    async def generate(reply, conversation, **kwargs):
        received.append(reply)
        assert reply.qualifying_intents == ("interaction",)
        yield "answer"

    monkeypatch.setattr(service._app_service, "stream_answer", generate)
    conversation = [ChatMessage(role="user", content="質問")]
    reply = await service.prepare_reply(conversation, ["1234567A0000"])
    assert reply is prepared
    assert [chunk async for chunk in service.stream_answer(reply, conversation)] == [
        "answer"
    ]
    assert received == [prepared]
    assert received[0] is prepared


@pytest.mark.asyncio
async def test_lifespan_composes_application_service_before_api_adapter(monkeypatch):
    from types import SimpleNamespace
    from unittest.mock import AsyncMock, Mock

    from backend.config.database_settings import PostgresDatabaseSettings
    from backend.infrastructure.composition import app_lifespan
    from backend.infrastructure.intent.jev_classifier import JevIntentClassifier
    from backend.infrastructure.morphology.janome_keyword_extractor import (
        JanomeKeywordExtractor,
    )
    from fastapi import FastAPI

    engine = SimpleNamespace(dispose=Mock())
    runtime = object()

    class Classifier(JevIntentClassifier):
        def __init__(self, **kwargs):
            self.closed = False

        @property
        def is_available(self):
            return False

        async def aclose(self):
            self.closed = True

    class Keywords(JanomeKeywordExtractor):
        def __init__(self, **kwargs):
            pass

    workers = SimpleNamespace(run=AsyncMock(), aclose=AsyncMock())
    monkeypatch.setattr(app_lifespan, "create_postgres_engine", lambda *a, **k: engine)
    monkeypatch.setattr(app_lifespan, "ReadWorkers", lambda **k: workers)
    monkeypatch.setattr(app_lifespan, "PostgresRuntime", lambda *a, **k: runtime)

    def provider_factory(_):
        return RecordingProvider()

    received = []

    def adapter_factory(*, application_service, defaults):
        received.append(application_service)
        return AppChatService(
            application_service=application_service, defaults=defaults
        )

    lifespan = app_lifespan.create_app_lifespan(
        definitions=get_package_insert_definitions(),
        settings=PostgresDatabaseSettings("postgresql://unused"),
        chat_service_factory=adapter_factory,
        llm_provider_factory=provider_factory,
        intent_classifier_cls=Classifier,
        keyword_extractor_cls=Keywords,
        janome_initializer=lambda: None,
        readonly_probe=True,
    )
    app = FastAPI()
    async with lifespan(app):
        application = received[0]
        assert isinstance(application, ChatApplicationService)
        classifier = application.intent_classifier
        assert isinstance(classifier, Classifier)
        assert isinstance(application.keyword_extractor, Keywords)
        assert application.provider_factory is provider_factory
        assert application.snapshot_provider is runtime
        assert app.state.chat_service.is_jev_available is False
    assert classifier.closed is True
    workers.aclose.assert_awaited_once()
    engine.dispose.assert_called_once()
