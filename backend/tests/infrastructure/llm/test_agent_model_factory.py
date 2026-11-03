"""Exercise actual LangChain and SDK codecs against a local HTTP transport."""

import asyncio
import json
from unittest.mock import AsyncMock, Mock

import httpx
import httpx2
import pytest
from backend.application.chat.queries.models import ChatMessage
from backend.infrastructure.agent.langgraph_chat_agent_adapter import (
    LangGraphChatAgentAdapter,
)
from backend.infrastructure.llm import agent_model_factory
from backend.tests.infrastructure.agent.test_langgraph_chat_agent import (
    MockMedicalTool,
    get_package_insert_definitions,
    make_evidence,
)
from google import genai
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_google_genai import chat_models as google_models
from langchain_openai import ChatOpenAI
from pydantic import SecretStr


@pytest.mark.asyncio
@pytest.mark.parametrize("provider", ["openai", "gemini"])
@pytest.mark.parametrize("outcome", ["success", "error", "cancel"])
async def test_native_tool_roundtrip_preserves_grounding_and_closes_clients(
    monkeypatch, provider, outcome
):
    requests = []
    request_started = asyncio.Event()

    async def respond(request):
        body = json.loads(request.content)
        requests.append(body)
        if outcome == "cancel":
            request_started.set()
            await asyncio.Event().wait()
        if outcome == "error":
            return httpx.Response(
                401,
                json={
                    "error": {
                        "message": "test authorization failure",
                        "code": 401,
                        "status": "UNAUTHENTICATED",
                    }
                },
            )
        if provider == "openai":
            message = (
                {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call_test",
                            "type": "function",
                            "function": {
                                "name": "lookup",
                                "arguments": '{"query":"test question"}',
                            },
                        }
                    ],
                }
                if len(requests) == 1
                else {"role": "assistant", "content": "テスト回答"}
            )
            payload = {
                "id": "test-completion",
                "model": "test-model",
                "object": "chat.completion",
                "created": 1,
                "choices": [
                    {
                        "index": 0,
                        "message": message,
                        "finish_reason": "tool_calls" if len(requests) == 1 else "stop",
                    }
                ],
            }
        else:
            parts = (
                [
                    {
                        "functionCall": {
                            "name": "lookup",
                            "args": {"query": "test question"},
                        },
                        "thoughtSignature": "dGVzdA==",
                    }
                ]
                if len(requests) == 1
                else [{"text": "テスト回答"}]
            )
            payload = {
                "candidates": [
                    {
                        "content": {"role": "model", "parts": parts},
                        "finishReason": "STOP",
                    }
                ]
            }
        return httpx.Response(200, json=payload)

    transport = httpx.MockTransport(respond)
    http_client = httpx.AsyncClient(transport=transport)
    models = []
    if provider == "openai":

        def create(**kwargs):
            model = ChatOpenAI(
                **kwargs, api_key=SecretStr("test-key"), http_async_client=http_client
            )
            models.append(model)
            return model

        monkeypatch.setattr(agent_model_factory, "ChatOpenAI", create)
    else:

        def client(**kwargs):
            kwargs["http_options"].httpx_async_client = http_client
            instance = genai.Client(**kwargs)
            monkeypatch.setattr(
                instance.aio, "aclose", AsyncMock(wraps=instance.aio.aclose)
            )
            monkeypatch.setattr(instance, "close", Mock(wraps=instance.close))
            return instance

        def create_google(**kwargs):
            model = ChatGoogleGenerativeAI(**kwargs)
            models.append(model)
            return model

        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        monkeypatch.setattr(google_models, "Client", client)
        monkeypatch.setattr(
            agent_model_factory, "ChatGoogleGenerativeAI", create_google
        )

    evidence = make_evidence("native_evidence", excerpt="NATIVE_GROUNDING")
    tool = MockMedicalTool("lookup", [evidence])
    agent = LangGraphChatAgentAdapter(
        [tool],
        model_factory=agent_model_factory.create_agent_model,
        answer_prompt_policy=get_package_insert_definitions().answer_prompt_policy,
    )

    async def run():
        return await agent.run(
            [ChatMessage(role="user", content="test question")],
            provider_name=provider,
            model_name="test-model",
        )

    if outcome == "success":
        reply = await run()
        assert tool.executed
        assert reply.answer == "テスト回答"
        assert reply.sources == [evidence]
        assert len(requests) == 2
        assert "lookup" in json.dumps(requests[0]["tools"])
        assert "NATIVE_GROUNDING" in json.dumps(requests[1])
    elif outcome == "cancel":
        task = asyncio.create_task(run())
        await asyncio.wait_for(request_started.wait(), 2)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert not tool.executed
        assert len(requests) == 1
    else:
        with pytest.raises(Exception, match="test authorization failure"):
            await run()
        assert not tool.executed
        assert len(requests) == 1
    if provider == "openai":
        assert requests[0]["model"] == "test-model"
        if outcome == "success":
            tool_result = next(
                m for m in requests[1]["messages"] if m["role"] == "tool"
            )
            assert tool_result["tool_call_id"] == "call_test"
        assert models[0].root_async_client.is_closed()
        assert models[0].root_client.is_closed()
    else:
        if outcome == "success":
            parts = [p for m in requests[1]["contents"] for p in m["parts"]]
            assert any("functionResponse" in p for p in parts)
            assert any(p.get("thoughtSignature") == "dGVzdA==" for p in parts)
        models[0].client.aio.aclose.assert_awaited_once()
        models[0].client.close.assert_called_once()
        # google-genai deliberately leaves a caller-supplied HTTP client to its owner.
        await http_client.aclose()
    assert http_client.is_closed


@pytest.mark.asyncio
async def test_sequential_agent_requests_get_fresh_openai_clients(monkeypatch):
    requests = []
    clients = []
    models = []

    async def respond(request):
        body = json.loads(request.content)
        requests.append(body)
        return httpx2.Response(
            200,
            json={
                "id": f"test-completion-{len(requests)}",
                "model": "test-model",
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
        http_client = httpx2.AsyncClient(transport=httpx2.MockTransport(respond))
        clients.append(http_client)
        model = ChatOpenAI(
            **kwargs,
            api_key=SecretStr("test-key"),
            http_async_client=http_client,
        )
        models.append(model)
        return model

    monkeypatch.setattr(agent_model_factory, "ChatOpenAI", create_openai_model)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    agent = LangGraphChatAgentAdapter(
        model_factory=agent_model_factory.create_agent_model
    )
    conversation = [ChatMessage(role="user", content="test question")]

    first = await agent.run(
        conversation, provider_name="openai", model_name="test-model"
    )
    assert first.answer == "回答1"
    assert clients[0].is_closed
    assert models[0].root_async_client.is_closed()

    second = await agent.run(
        conversation, provider_name="openai", model_name="test-model"
    )
    assert second.answer == "回答2"
    assert len(requests) == len(clients) == len(models) == 2
    assert clients[0] is not clients[1]
    assert models[0] is not models[1]
    assert all(http_client.is_closed for http_client in clients)
    assert all(model.root_async_client.is_closed() for model in models)


@pytest.mark.asyncio
async def test_unknown_provider_is_rejected():
    with pytest.raises(ValueError, match="Unsupported agent provider"):
        async with agent_model_factory.create_agent_model("invalid", "test-model"):
            pytest.fail("Invalid configuration must not yield a model")


@pytest.mark.asyncio
@pytest.mark.parametrize("provider", ["openai", "gemini"])
async def test_missing_api_key_does_not_produce_a_simulated_answer(
    monkeypatch, provider
):
    for key in ("OPENAI_API_KEY", "GOOGLE_API_KEY", "GEMINI_API_KEY"):
        monkeypatch.delenv(key, raising=False)
    with pytest.raises(Exception, match="api_key|API key"):
        async with agent_model_factory.create_agent_model(provider, "test-model"):
            pytest.fail("Missing API keys must fail before model execution")
