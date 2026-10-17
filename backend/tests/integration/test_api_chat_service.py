"""DM-22/23/24: 実組立経路の所有終了と設定優先順位。"""

import asyncio
from collections.abc import AsyncGenerator

import pytest
from backend.application.chat.chat_models import ChatResponse
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
        medicine_reader=MedicineReader(),
        evidence_reader=RecordingReader(),
        intent_classifier=UnusedIntentClassifier(),
        keyword_extractor=UnusedKeywordExtractor(),
        intent_policy=get_package_insert_definitions().intent_policy,
        answer_prompt_policy=get_package_insert_definitions().answer_prompt_policy,
        provider_factory=factory,
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


def test_application_lifespan_closes_owned_intent_sdk(tmp_path, monkeypatch):
    from backend import main
    from backend.infrastructure.persistence.index_writer import SqlAlchemyIndexWriter
    from backend.infrastructure.persistence.sqlite_engine import create_sqlite_engine
    from backend.infrastructure.sources.file_index_source import FileIndexSourceReader
    from backend.tests.infrastructure.persistence.test_alembic_migrations import (
        _migrate_database,
    )
    from backend.tests.support.storage_fixtures import write_structured_document
    from fastapi.testclient import TestClient
    from sqlalchemy.engine import URL

    class OwnedClassifier(UnusedIntentClassifier):
        is_available = False
        closed = False

        async def aclose(self):
            self.closed = True

    classifier = OwnedClassifier()
    monkeypatch.setattr(main, "JevIntentClassifier", lambda **kwargs: classifier)
    source = write_structured_document(tmp_path)
    index = tmp_path / "index.sqlite3"
    _migrate_database(index, source)
    engine = create_sqlite_engine(
        URL.create("sqlite", database=index.as_posix()).render_as_string(
            hide_password=False
        )
    )
    try:
        SqlAlchemyIndexWriter(engine).replace(
            FileIndexSourceReader(source).read_snapshot()
        )
    finally:
        engine.dispose()
    from backend.tests.support.registration_runtime_fixtures import (
        register_synthetic_prepared_index,
    )

    register_synthetic_prepared_index(source, index)
    with TestClient(
        main.create_app(source, index, import_directory=tmp_path / "imports")
    ) as client:
        assert client.get("/health").status_code == 200
        assert classifier.closed is False
    assert classifier.closed is True


@pytest.mark.asyncio
async def test_prepared_application_reply_is_retained_until_generation(monkeypatch):
    from unittest.mock import AsyncMock

    definitions = get_package_insert_definitions()
    service = AppChatService(
        medicine_reader=MedicineReader(),
        evidence_reader=RecordingReader(),
        intent_classifier=UnusedIntentClassifier(),
        keyword_extractor=UnusedKeywordExtractor(),
        intent_policy=definitions.intent_policy,
        answer_prompt_policy=definitions.answer_prompt_policy,
        provider_factory=lambda _: RecordingProvider(),
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
