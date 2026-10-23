"""SDK所有adapterの終了を実SDKと同形の境界Fakeで観測する。"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncGenerator, AsyncIterator
from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock, Mock

import pytest
from backend.application.chat.answer_preparation import prepare_reply
from backend.application.chat.answer_stream import stream_answer
from backend.application.chat.chat_models import ChatMessage
from backend.application.retrieval.intent_contracts import IntentRequest, IntentResult
from backend.infrastructure.intent import jev_classifier
from backend.infrastructure.llm import gemini_provider, openai_provider
from backend.infrastructure.llm.provider_factory import create_llm_provider
from backend.infrastructure.package_insert_definitions.assembly import (
    get_package_insert_definitions,
)
from backend.presentation import chat_websocket_routes
from backend.presentation.chat_models import ChatResponse as ApiChatResponse
from backend.tests.integration.test_application_port_contracts import (
    RecordingEvidenceReader,
    RecordingKeywordExtractor,
    RecordingMedicineReader,
)
from backend.tests.support.retrieval_snapshot import FixedSnapshotProvider
from fastapi import FastAPI, WebSocketDisconnect
from starlette.types import Message, Scope


class LifecycleStream:
    """OpenAI AsyncStream相当。Geminiにはiterate()のasyncgeneratorを返す。"""

    def __init__(self, provider: str, path: str) -> None:
        self.provider = provider
        self.path = path
        self.index = 0
        self.closed = False
        self.waiting = asyncio.Event()

    def __aiter__(self) -> LifecycleStream:
        return self

    async def __anext__(self) -> SimpleNamespace:
        if self.index == 1:
            if self.path == "error":
                raise RuntimeError("SDK lifecycle failure")
            if self.path == "cancel":
                self.waiting.set()
                await asyncio.Event().wait()
        if self.index == 2:
            raise StopAsyncIteration
        value = ("first", "second")[self.index]
        self.index += 1
        if self.provider == "openai":
            return SimpleNamespace(
                choices=[SimpleNamespace(delta=SimpleNamespace(content=value))]
            )
        return SimpleNamespace(text=value)

    async def aclose(self) -> None:
        self.closed = True

    async def iterate(self) -> AsyncIterator[SimpleNamespace]:
        try:
            async for chunk in self:
                yield chunk
        finally:
            await self.aclose()


def _install_llm(monkeypatch: pytest.MonkeyPatch, provider: str, path: str):
    response = LifecycleStream(provider, path)
    client_close = AsyncMock()
    sync_close = Mock()
    if provider == "openai":
        client = SimpleNamespace(
            close=client_close,
            chat=SimpleNamespace(
                completions=SimpleNamespace(create=AsyncMock(return_value=response))
            ),
        )
        monkeypatch.setattr(openai_provider, "AsyncOpenAI", lambda **kwargs: client)
    else:
        chat = SimpleNamespace(
            send_message_stream=AsyncMock(return_value=response.iterate())
        )
        client = SimpleNamespace(
            close=sync_close,
            aio=SimpleNamespace(
                aclose=client_close,
                chats=SimpleNamespace(create=Mock(return_value=chat)),
            ),
        )
        monkeypatch.setattr(
            gemini_provider, "genai", SimpleNamespace(Client=lambda **kwargs: client)
        )
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    return response, client_close, sync_close


class LifecycleTypeSafeClient:
    def __init__(self, path: str) -> None:
        self.path = path
        self.calls = 0
        self.active = 0
        self.finished = 0
        self.closed = 0
        self.started = asyncio.Event()
        self.release = asyncio.Event()
        self.request_tasks: list[asyncio.Task[object]] = []

    async def system_one(
        self, *, state: object, questions: object
    ) -> dict[str, object]:
        assert not self.closed
        self.calls += 1
        self.active += 1
        self.started.set()
        current = asyncio.current_task()
        assert current is not None
        self.request_tasks.append(cast(asyncio.Task[object], current))
        try:
            if self.path in ("cancel", "consumer_stop"):
                await self.release.wait()
            if self.path == "error":
                raise RuntimeError("SDK lifecycle failure")
            return {"intent": {"predictions": []}}
        finally:
            self.active -= 1
            self.finished += 1

    async def aclose(self) -> None:
        assert not self.active, "shared client closed during an active request"
        self.closed += 1


async def _assert_ws_closes_stream(
    monkeypatch: pytest.MonkeyPatch, provider: str
) -> None:
    response, close, sync_close = _install_llm(monkeypatch, provider, "consumer_stop")
    app = FastAPI()
    app.include_router(chat_websocket_routes.router)
    reply = ApiChatResponse(
        answer="", intent="other", retrieval_strategy="three_detectors"
    )
    app.state.chat_service = SimpleNamespace(
        is_jev_available=False,
        prepare_reply=AsyncMock(return_value=reply),
        stream_answer=lambda *args: stream_answer(
            create_llm_provider(provider), [{"role": "user", "content": "質問"}]
        ),
    )
    incoming: asyncio.Queue[Message] = asyncio.Queue()
    await incoming.put({"type": "websocket.connect"})
    await incoming.put(
        {
            "type": "websocket.receive",
            "text": json.dumps(
                {
                    "type": "message",
                    "product_yj_codes": ["1234567A0000"],
                    "messages": [{"role": "user", "content": "質問"}],
                    "provider": provider,
                }
            ),
        }
    )
    sent: list[Message] = []

    async def receive() -> Message:
        return await incoming.get()

    async def send(message: Message) -> None:
        sent.append(message)
        if (
            message["type"] == "websocket.send"
            and json.loads(message["text"])["type"] == "text_delta"
        ):
            raise WebSocketDisconnect(code=1000)

    scope: Scope = {
        "type": "websocket",
        "asgi": {"version": "3.0"},
        "scheme": "ws",
        "path": "/ws/chat",
        "raw_path": b"/ws/chat",
        "root_path": "",
        "query_string": b"",
        "headers": [],
        "client": ("test", 123),
        "server": ("test", 80),
        "subprotocols": [],
    }
    await asyncio.wait_for(app(scope, receive, send), 10)
    assert any(
        item["type"] == "websocket.send" and "first" in item["text"] for item in sent
    )
    assert response.closed, "WS send disconnect left SDK stream open"
    close.assert_awaited_once()
    if provider == "gemini":
        sync_close.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("provider_name", ["openai", "gemini", "typesafe"])
@pytest.mark.parametrize("path", ["normal", "error", "cancel", "consumer_stop"])
async def test_owned_sdk_resources_close_on_all_exit_paths(
    monkeypatch: pytest.MonkeyPatch,
    provider_name: str,
    path: str,
) -> None:
    if provider_name == "typesafe":
        client = LifecycleTypeSafeClient(path)
        monkeypatch.setattr(
            jev_classifier.ts, "AsyncTypeSafeClient", lambda **kwargs: client
        )
        classifier = jev_classifier.JevIntentClassifier(api_key="test-key")
        task = None
        closing: asyncio.Task[None] | None = None
        try:
            if path == "consumer_stop":
                task = asyncio.create_task(
                    prepare_reply(
                        [ChatMessage(role="user", content="質問")],
                        [],
                        snapshot_provider=FixedSnapshotProvider(
                            RecordingMedicineReader(()), RecordingEvidenceReader([], [])
                        ),
                        intent_classifier=classifier,
                        keyword_extractor=RecordingKeywordExtractor(()),
                        intent_policy=get_package_insert_definitions().intent_policy,
                    )
                )
            else:
                task = asyncio.create_task(classifier.classify(IntentRequest("質問")))
            await asyncio.wait_for(client.started.wait(), 10)
            assert client.closed == 0
            if path in ("cancel", "consumer_stop"):
                task.cancel()
                with pytest.raises(asyncio.CancelledError):
                    await task
                assert client.active == 0, (
                    "consumer exited leaving its SDK request running"
                )
            else:
                result = await task
                assert isinstance(result, IntentResult)
                assert result.is_available
                if path == "error":
                    assert result.raw_response == {"error": "SDK lifecycle failure"}
                else:
                    assert result.raw_response == {"intent": {"predictions": []}}
                    client.path = "cancel"
                    client.started.clear()
                    task = asyncio.create_task(
                        classifier.classify(IntentRequest("同じ共有clientへの次の質問"))
                    )
                    await asyncio.wait_for(client.started.wait(), 10)
                    exit_started = asyncio.Event()

                    async def close_owner() -> None:
                        exit_started.set()
                        await classifier.aclose()

                    closing = asyncio.create_task(close_owner())
                    await exit_started.wait()
                    assert not closing.done()
                    assert client.closed == 0 and client.active == 1
                    client.release.set()
                    await task
                    await closing
                    assert client.calls == 2
                    assert client.closed == 1
                if path == "error":
                    assert client.closed == 0
            await classifier.aclose()
            assert client.closed == 1
            assert client.finished == client.calls
        finally:
            client.release.set()
            if task is not None:
                await asyncio.gather(task, return_exceptions=True)
            # Red時の残った子taskもテストのloopへ持ち越さない。
            remaining = [
                item
                for item in client.request_tasks
                if item is not asyncio.current_task() and not item.done()
            ]
            for item in remaining:
                item.cancel()
            await asyncio.gather(*remaining, return_exceptions=True)
            if closing is not None:
                await asyncio.gather(closing, return_exceptions=True)
        return

    response, client_close, sync_close = _install_llm(monkeypatch, provider_name, path)
    output = stream_answer(
        create_llm_provider(provider_name), [{"role": "user", "content": "質問"}]
    )
    assert isinstance(output, AsyncGenerator)
    task = None
    try:
        assert await anext(output) == "first"
        client_close.assert_not_awaited()
        if path == "consumer_stop":
            await output.aclose()
        elif path == "cancel":
            task = asyncio.create_task(anext(output))
            await asyncio.wait_for(response.waiting.wait(), 10)
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
        elif path == "error":
            tail = [chunk async for chunk in output]
            assert len(tail) == 1 and "SDK lifecycle failure" in tail[0]
        else:
            assert [chunk async for chunk in output] == ["second"]
        assert response.closed, "owned SDK stream was left open"
        client_close.assert_awaited_once()
        if provider_name == "gemini":
            sync_close.assert_called_once()
        if path == "consumer_stop":
            await _assert_ws_closes_stream(monkeypatch, provider_name)
    finally:
        if task is not None:
            await asyncio.gather(task, return_exceptions=True)
        await output.aclose()
