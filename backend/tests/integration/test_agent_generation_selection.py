"""DB-free request selection through the real Presentation/Application boundary."""

import asyncio
import json
from contextlib import asynccontextmanager

import httpx2
import pytest
from backend.application.chat.queries.chat import ChatQueries
from backend.config.generation_settings import GenerationDefaults
from backend.infrastructure.agent.langgraph_chat_agent_adapter import (
    LangGraphChatAgentAdapter,
    LLMProviderChatModelAdapter,
)
from backend.infrastructure.llm import agent_model_factory
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
from langchain_openai import ChatOpenAI
from langchain_openai.chat_models import _client_utils as openai_client_utils


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


def test_websocket_runs_two_sequential_agent_requests():
    service, calls = service_and_calls()
    request_ids = [
        "a871f25a-1eb7-4c5e-8c6e-4511dce60280",
        "b871f25a-1eb7-4c5e-8c6e-4511dce60280",
    ]

    with client(service).websocket_connect("/api/ws") as socket:
        for request_id in request_ids:
            socket.send_json(
                request(
                    request_id,
                    provider="gemini",
                    model="gemini-2.5-flash",
                )
            )
            events = completed(socket, request_id)
            assert events[-1]["type"] == "text_done"

    assert calls == [
        ["gemini", "gemini-2.5-flash"],
        ["gemini", "gemini-2.5-flash"],
    ]


def test_websocket_uses_fresh_openai_clients_for_sequential_agent_requests(
    monkeypatch,
):
    requests = []
    async_clients = []
    sync_clients = []
    models = []

    async def respond(request):
        body = json.loads(request.content)
        requests.append(body)
        if len(requests) == 1:
            await asyncio.sleep(0.1)
        return httpx2.Response(
            200,
            json={
                "id": f"chatcmpl-{len(requests)}",
                "model": "gpt-6-luna",
                "object": "chat.completion",
                "created": 1,
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": f"回答{len(requests)}",
                        },
                        "finish_reason": "stop",
                    }
                ],
            },
        )

    def create_openai_model(**kwargs):
        model = ChatOpenAI(**kwargs)
        models.append(model)
        return model

    def build_async_http_client(base_url, timeout, socket_options=()):
        http_client = openai_client_utils._AsyncHttpxClientWrapper(
            base_url=base_url or "https://api.openai.com/v1",
            timeout=timeout,
            transport=httpx2.MockTransport(respond),
        )
        async_clients.append(http_client)
        return http_client

    def build_sync_http_client(base_url, timeout, socket_options=()):
        http_client = openai_client_utils._SyncHttpxClientWrapper(
            base_url=base_url or "https://api.openai.com/v1",
            timeout=timeout,
            transport=httpx2.MockTransport(
                lambda request: httpx2.Response(200, json={})
            ),
        )
        sync_clients.append(http_client)
        return http_client

    openai_client_utils._cached_async_httpx_client.cache_clear()
    openai_client_utils._cached_sync_httpx_client.cache_clear()
    monkeypatch.setattr(
        openai_client_utils, "_build_async_httpx_client", build_async_http_client
    )
    monkeypatch.setattr(
        openai_client_utils, "_build_sync_httpx_client", build_sync_http_client
    )
    monkeypatch.setattr(agent_model_factory, "ChatOpenAI", create_openai_model)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    definitions = get_package_insert_definitions()

    class Provider:
        async def stream_response(self, messages, model=None):
            yield "回答"

    agent = LangGraphChatAgentAdapter(
        [MockMedicalTool("required", [make_evidence("test")], is_mandatory=True)],
        model_factory=agent_model_factory.create_agent_model,
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
    service = AppChatService(
        application_service=queries,
        defaults=lambda: GenerationDefaults("openai", "gpt-6-luna"),
    )
    request_ids = [
        "a871f25a-1eb7-4c5e-8c6e-4511dce60280",
        "b871f25a-1eb7-4c5e-8c6e-4511dce60280",
    ]

    try:
        with client(service).websocket_connect("/api/ws") as socket:
            first_payload = request(
                request_ids[0], provider="openai", model="gpt-6-luna"
            )
            socket.send_json(first_payload)
            first_events = completed(socket, request_ids[0])
            assert not any(event["type"] == "error" for event in first_events)
            assert [
                event["content"]
                for event in first_events
                if event["type"] == "text_delta"
            ] == ["回答1"]

            second_payload = request(
                request_ids[1],
                provider="openai",
                model="gpt-6-luna",
            )
            second_payload["messages"] = [
                {"role": "user", "content": "質問1"},
                {"role": "assistant", "content": "回答1"},
                {"role": "user", "content": "質問2"},
            ]
            socket.send_json(second_payload)
            second_events = completed(socket, request_ids[1])

        assert not any(event["type"] == "error" for event in second_events)
        assert [
            event["content"] for event in second_events if event["type"] == "text_delta"
        ] == ["回答2"]
        assert len(requests) == len(models) == 2
        assert len(async_clients) == len(sync_clients) == 2
        assert models[0] is not models[1]
        assert async_clients[0] is not async_clients[1]
        assert sync_clients[0] is not sync_clients[1]
        assert all(http_client.is_closed for http_client in async_clients)
        assert all(http_client.is_closed for http_client in sync_clients)
        assert all(model.root_async_client.is_closed() for model in models)
    finally:

        async def close_async_clients():
            await asyncio.gather(
                *(http_client.aclose() for http_client in async_clients)
            )

        asyncio.run(close_async_clients())
        for http_client in sync_clients:
            http_client.close()
        openai_client_utils._cached_async_httpx_client.cache_clear()
        openai_client_utils._cached_sync_httpx_client.cache_clear()
