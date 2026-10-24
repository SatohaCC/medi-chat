"""共通の会話処理とREST / WebSocketの契約を検証する。"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from unittest.mock import Mock, patch

import pytest
from backend.application.chat.interfaces.llm_provider import LLMProvider
from backend.presentation.chat_models import ChatMessage
from backend.tests.support.postgres_fixtures import pg_api as pg_api
from backend.tests.support.postgres_fixtures import pg_engines as pg_engines
from fastapi.testclient import TestClient


class RecordingProvider(LLMProvider):
    def __init__(self) -> None:
        self.calls: list[tuple[list[dict[str, str]], str | None]] = []

    async def stream_response(
        self, messages: list[dict[str, str]], model: str | None = None
    ) -> AsyncIterator[str]:
        self.calls.append((messages, model))
        yield "同じ"
        yield "回答"


def test_RESTとWebSocketで回答と根拠とLLM入力が一致する(pg_api) -> None:
    provider = RecordingProvider()
    app = pg_api(llm_provider_factory=lambda _: provider)
    with (
        patch.dict(os.environ, {"TYPESAFE_API_KEY": "", "JEV_API_KEY": ""}),
        TestClient(app) as client,
    ):
        rest = client.post(
            "/api/chat",
            json={
                "message": "副作用の頭痛について",
                "product_yj_codes": ["1234567A0000"],
                "provider": "openai",
                "model": "gpt-6-luna",
            },
        )
        with client.websocket_connect("/api/ws") as socket:
            socket.send_json(
                {
                    "type": "message",
                    "request_id": "a871f25a-1eb7-4c5e-8c6e-4511dce60280",
                    "messages": [{"role": "user", "content": "副作用の頭痛について"}],
                    "product_yj_codes": ["1234567A0000"],
                    "provider": "openai",
                    "model": "gpt-6-luna",
                }
            )
            events = []
            while True:
                event = socket.receive_json()
                events.append(event)
                if event["type"] == "text_done":
                    break
    assert rest.status_code == 200
    assert (
        rest.json()["answer"]
        == "同じ回答"
        == "".join(
            event["content"] for event in events if event["type"] == "text_delta"
        )
    )
    source_events = [event for event in events if event["type"] == "sources"]
    assert rest.json()["sources"] == source_events[-1]["sources"]
    assert len(source_events) >= 2

    assert len(provider.calls) == 2
    assert provider.calls[0] == provider.calls[1]
    assert [event["type"] for event in events] == [
        "retrieval_status",
        *["sources"] * len(source_events),
        "text_delta",
        "text_delta",
        "text_done",
    ]


@pytest.mark.asyncio
async def test_対象薬が見つからない場合はLLMを作成しない(pg_api) -> None:
    factory = Mock(side_effect=AssertionError("LLMを作成してはいけない"))
    app = pg_api(llm_provider_factory=factory)
    async with app.router.lifespan_context(app):
        service = app.state.chat_service
        messages = [ChatMessage(role="user", content="副作用について")]
        reply = await service.prepare_reply(messages, ["0000000A0000"])
        chunks = [chunk async for chunk in service.stream_answer(reply, messages)]
    assert reply.needs_clarification
    assert "YJコード" in reply.answer
    assert chunks == [reply.answer]
    factory.assert_not_called()
