"""DB-free request selection through the real Presentation/Application boundary."""

from contextlib import asynccontextmanager

import pytest
from backend.application.chat.queries.chat import ChatQueries
from backend.config.generation_settings import GenerationDefaults
from backend.infrastructure.agent.langgraph_chat_agent_adapter import (
    LangGraphChatAgentAdapter,
    LLMProviderChatModelAdapter,
)
from backend.presentation.chat_models import ChatMessage
from backend.presentation.chat_service import AppChatService
from backend.tests.infrastructure.agent.test_langgraph_chat_agent import (
    MockMedicalTool,
    get_package_insert_definitions,
    make_evidence,
)
from backend.tests.integration.test_langgraph_chat_integration import (
    DummyEvidenceReader,
    DummyIntentClassifier,
    DummyKeywordExtractor,
    DummyMedicineReader,
)
from backend.tests.presentation.test_chat_websocket_lifecycle import (
    client,
    completed,
    request,
)
from backend.tests.support.retrieval_snapshot import FixedSnapshotProvider


def service_and_calls():
    calls = []

    class Provider:
        async def stream_response(self, messages, model=None):
            calls[-1].append(model)
            yield "テスト回答"

    @asynccontextmanager
    async def model_factory(provider, model):
        calls.append([provider])
        yield LLMProviderChatModelAdapter(Provider(), model)

    definitions = get_package_insert_definitions()
    agent = LangGraphChatAgentAdapter(
        [MockMedicalTool("required", [make_evidence("test")], is_mandatory=True)],
        model_factory=model_factory,
        answer_prompt_policy=definitions.answer_prompt_policy,
    )
    queries = ChatQueries(
        intent_classifier=DummyIntentClassifier(),
        keyword_extractor=DummyKeywordExtractor(),
        intent_policy=definitions.intent_policy,
        answer_prompt_policy=definitions.answer_prompt_policy,
        provider_factory=lambda _: Provider(),
        snapshot_provider=FixedSnapshotProvider(
            DummyMedicineReader(), DummyEvidenceReader()
        ),
        agent_orchestrator=agent,
    )
    return AppChatService(
        application_service=queries,
        defaults=lambda: GenerationDefaults("openai", "default-model"),
    ), calls


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "provider,model,expected",
    [
        (None, None, ["openai", "default-model"]),
        ("gemini", "explicit-model", ["gemini", "explicit-model"]),
        ("gemini", None, ["gemini", "gemini-3.8-flash"]),
    ],
)
async def test_http_and_prepared_reply_resolve_same_generation(
    provider, model, expected
):
    service, calls = service_and_calls()
    conversation = [ChatMessage(role="user", content="テスト質問")]
    http_reply = await service.answer_question(conversation, [], provider, model)
    reply = await service.prepare_reply(
        conversation, [], provider_name=provider, model_name=model
    )
    chunks = [
        c async for c in service.stream_answer(reply, conversation, provider, model)
    ]
    assert http_reply.answer == "".join(chunks) == "テスト回答"
    assert calls == [expected, expected]


def test_websocket_passes_selection_before_generation():
    service, calls = service_and_calls()
    with client(service).websocket_connect("/api/ws") as socket:
        socket.send_json(request(provider="gemini", model="gemini-2.5-flash"))
        events = completed(socket)
    assert events[-1]["type"] == "text_done"
    assert calls == [["gemini", "gemini-2.5-flash"]]
