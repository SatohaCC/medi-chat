"""DB-free tests of the real WebSocket boundary and request ownership."""

import asyncio
import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress

import pytest
from backend.application.chat.queries.models import ChatResponse
from backend.presentation.chat_service import AppChatService
from backend.presentation.chat_websocket_routes import router
from backend.presentation.dependencies import get_chat_service
from backend.tests.application.retrieval.test_evidence_collection import make_evidence
from fastapi import FastAPI
from fastapi.testclient import TestClient

A = "a871f25a-1eb7-4c5e-8c6e-4511dce60280"
B = "b871f25a-1eb7-4c5e-8c6e-4511dce60280"
P = "c871f25a-1eb7-4c5e-8c6e-4511dce60280"


def request(request_id=A, **changes):
    return {
        "type": "message",
        "request_id": request_id,
        "product_yj_codes": ["123456789012"],
        "messages": [{"role": "user", "content": "テスト質問"}],
        **changes,
    }


class Service:
    is_jev_available = True
    sources_to_api = staticmethod(AppChatService.sources_to_api)

    async def prepare_reply(self, *args, **kwargs):
        return ChatResponse(
            answer="",
            intent="other",
            retrieval_strategy="three_detectors",
            needs_clarification=False,
            sources=[make_evidence(product_name="テスト薬", generic_name="テスト成分")],
            jev_response={"test": True},
            notices=["テスト通知"],
        )

    async def stream_answer(self, *args, **kwargs) -> AsyncIterator[str]:
        yield "テスト回答"


def client(service=None):
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_chat_service] = lambda: service or Service()
    return TestClient(app)


def completed(ws, request_id=A):
    events = []
    while True:
        event = ws.receive_json()
        events.append(event)
        assert event["request_id"] == request_id
        if event["type"] in {"text_done", "error", "aborted"}:
            return events


@pytest.mark.parametrize("path", ["/api/ws", "/ws/chat"])
def test_WR001_correlates_all_events(path):
    with client().websocket_connect(path) as ws:
        ws.send_json(request())
        events = completed(ws)
        assert [e["type"] for e in events] == [
            "retrieval_status",
            "sources",
            "jev_response",
            "notices",
            "retrieval_status",
            "text_delta",
            "text_done",
        ]
        assert events[-2]["content"] == "テスト回答"
        assert events[1]["sources"][0]["excerpt"] == "原文\n本文"


@pytest.mark.parametrize(
    "value", [None, "", "invalid", "a871f25a-1eb7-1c5e-8c6e-4511dce60280", 123]
)
def test_WR002_invalid_id_then_valid(value):
    with client().websocket_connect("/api/ws") as ws:
        data = request(value)
        if value is None:
            data.pop("request_id")
        ws.send_json(data)
        assert ws.receive_json()["type"] == "connection_error"
        ws.send_json(request(B))
        assert completed(ws, B)[-1]["type"] == "text_done"


@pytest.mark.parametrize(
    "wire,code",
    [
        ("broken", "invalid_payload"),
        ("null", "invalid_payload"),
        ("[]", "invalid_payload"),
        ("4", "invalid_payload"),
        ('{"type":"unknown"}', "unsupported_type"),
    ],
)
def test_WR003_invalid_wire_then_valid(wire, code):
    with client().websocket_connect("/api/ws") as ws:
        ws.send_text(wire)
        event = ws.receive_json()
        assert (event["type"], event["code"]) == ("connection_error", code)
        ws.send_json(request(B))
        assert completed(ws, B)[-1]["type"] == "text_done"


def test_WR004_valid_id_invalid_content():
    with client().websocket_connect("/api/ws") as ws:
        ws.send_json(request(messages=[]))
        event = ws.receive_json()
        assert (event["type"], event["request_id"]) == ("error", A)
        ws.send_json(request(B))
        assert completed(ws, B)[-1]["type"] == "text_done"


def test_WR005_ping_echo_and_invalid_control():
    with client().websocket_connect("/api/ws") as ws:
        ws.send_json({"type": "ping", "ping_id": P})
        assert ws.receive_json() == {"type": "pong", "ping_id": P}
        ws.send_json({"type": "ping", "ping_id": "invalid"})
        assert ws.receive_json()["type"] == "connection_error"


@asynccontextmanager
async def session(service, send_hook=None):
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_chat_service] = lambda: service
    incoming, outgoing = asyncio.Queue(), asyncio.Queue()

    async def send(event):
        if send_hook:
            await send_hook(event)
        await outgoing.put(event)

    task = asyncio.create_task(
        app(
            {
                "type": "websocket",
                "asgi": {"version": "3.0"},
                "scheme": "ws",
                "path": "/api/ws",
                "raw_path": b"/api/ws",
                "query_string": b"",
                "headers": [],
                "client": ("test", 123),
                "server": ("test", 80),
                "subprotocols": [],
                "root_path": "",
            },
            incoming.get,
            send,
        )
    )
    await incoming.put({"type": "websocket.connect"})
    assert (await asyncio.wait_for(outgoing.get(), 1))["type"] == "websocket.accept"

    class Wire:
        handler = task

        async def send(self, data):
            await incoming.put({"type": "websocket.receive", "text": json.dumps(data)})

        async def disconnect(self):
            await incoming.put({"type": "websocket.disconnect", "code": 1000})

        async def receive(self):
            try:
                event = await asyncio.wait_for(outgoing.get(), 1)
            except TimeoutError:
                pytest.fail("Expected control response while generation is still held")
            return json.loads(event["text"])

    try:
        yield Wire()
    finally:
        service.release.set()
        if hasattr(service, "cleanup_release"):
            service.cleanup_release.set()
        await incoming.put({"type": "websocket.disconnect", "code": 1000})
        with suppress(asyncio.CancelledError):
            await asyncio.wait_for(task, 2)


class HeldService(Service):
    def __init__(self, stage="prepare"):
        self.stage = stage
        self.started = asyncio.Event()
        self.release = asyncio.Event()
        self.closed = asyncio.Event()
        self.calls = 0

    async def prepare_reply(self, *args, **kwargs):
        self.calls += 1
        if self.stage == "prepare":
            self.started.set()
            try:
                await self.release.wait()
            finally:
                self.closed.set()
        return await super().prepare_reply(*args, **kwargs)

    async def stream_answer(self, *args, **kwargs) -> AsyncIterator[str]:
        self.started.set()
        try:
            await self.release.wait()
            yield "テスト回答"
        finally:
            self.closed.set()


@pytest.mark.asyncio
@pytest.mark.parametrize("stage", ["prepare", "stream"])
async def test_WR011_busy_preserves_single_task(stage):
    service = HeldService(stage)
    async with session(service) as ws:
        await ws.send(request())
        await service.started.wait()
        await ws.send(request(B))
        while True:
            event = await ws.receive()
            if event["type"] == "control_error":
                break
        assert (event["code"], event["request_id"]) == ("busy", B)
        assert service.calls == 1
        await ws.send(request(A, messages=[]))
        event = await ws.receive()
        assert (event["type"], event.get("code")) == ("control_error", "busy")


@pytest.mark.asyncio
@pytest.mark.parametrize("stage", ["prepare", "stream"])
async def test_WR012_ping_while_generation_waits(stage):
    service = HeldService(stage)
    async with session(service) as ws:
        await ws.send(request())
        await service.started.wait()
        await ws.send({"type": "ping", "ping_id": P})
        while (event := await ws.receive())["type"] != "pong":
            pass
        assert event == {"type": "pong", "ping_id": P}
        assert not service.release.is_set()


class CleanupService(HeldService):
    def __init__(self, stage="prepare"):
        super().__init__(stage)
        self.cleaning = asyncio.Event()
        self.cleanup_release = asyncio.Event()

    async def hold(self):
        self.started.set()
        try:
            await self.release.wait()
        finally:
            self.cleaning.set()
            await self.cleanup_release.wait()
            self.closed.set()

    async def prepare_reply(self, *args, **kwargs):
        self.calls += 1
        if self.stage == "prepare":
            await self.hold()
        return await Service.prepare_reply(self, *args, **kwargs)

    async def stream_answer(self, *args, **kwargs) -> AsyncIterator[str]:
        if self.stage == "stream":
            yield "部分テスト回答"
            await self.hold()
        yield "テスト回答"


@pytest.mark.asyncio
@pytest.mark.parametrize("stage", ["prepare", "stream"])
async def test_WR014_aborted_only_after_cleanup(stage):
    service = CleanupService(stage)
    try:
        async with session(service) as ws:
            await ws.send(request())
            await asyncio.wait_for(service.started.wait(), 1)
            await ws.send({"type": "abort", "request_id": A})
            try:
                await asyncio.wait_for(service.cleaning.wait(), 1)
            except TimeoutError:
                pytest.fail("Abort must cancel the request and enter cleanup")
            await ws.send(request(B))
            while (event := await ws.receive())["type"] != "control_error":
                assert event["type"] != "aborted"
            assert event["code"] == "busy"
            await ws.send({"type": "ping", "ping_id": P})
            assert (await ws.receive())["type"] == "pong"
            assert not service.closed.is_set()
            service.cleanup_release.set()
            event = await ws.receive()
            assert event == {"type": "aborted", "request_id": A}
            assert service.closed.is_set()
            service.release.set()
            await ws.send(request(B))
            while (event := await ws.receive())["type"] != "text_done":
                assert event["request_id"] == B
    finally:
        service.cleanup_release.set()


@pytest.mark.asyncio
@pytest.mark.parametrize("abort_first", [False, True])
async def test_WR015_terminal_race_and_WR017_idle_abort(abort_first):
    service = HeldService()
    async with session(service) as ws:
        await ws.send({"type": "abort", "request_id": B})
        assert (await ws.receive())["code"] == "not_active"
        await ws.send(request())
        await service.started.wait()
        await ws.send({"type": "abort", "request_id": B})
        while (event := await ws.receive())["type"] != "control_error":
            pass
        assert (event["code"], event["request_id"]) == ("not_active", B)
        if abort_first:
            await ws.send({"type": "abort", "request_id": A})
        else:
            service.release.set()
        terminals = []
        while True:
            event = await ws.receive()
            if event["type"] in {"text_done", "error", "aborted"}:
                terminals.append(event)
                break
        assert terminals[0]["type"] == ("aborted" if abort_first else "text_done")
        await ws.send({"type": "abort", "request_id": A})
        assert (await ws.receive())["code"] == "not_active"


@pytest.mark.asyncio
@pytest.mark.parametrize("stage", ["prepare", "stream"])
async def test_WR016_generation_exception_is_recovered(stage):
    class Failure(Service):
        release = asyncio.Event()
        fail = True

        async def prepare_reply(self, *args, **kwargs):
            if stage == "prepare" and self.fail:
                raise RuntimeError("secret test value")
            return await super().prepare_reply(*args, **kwargs)

        async def stream_answer(self, *args, **kwargs) -> AsyncIterator[str]:
            if stage == "stream" and self.fail:
                raise RuntimeError("secret test value")
            yield "テスト回答"

    service = Failure()
    service.fail = True
    async with session(service) as ws:
        await ws.send(request())
        while (event := await ws.receive())["type"] != "error":
            pass
        assert event["request_id"] == A
        assert "secret" not in event["content"]
        service.fail = False
        await ws.send(request(B))
        while (event := await ws.receive())["type"] != "text_done":
            assert event["type"] != "error"
        assert event["request_id"] == B


@pytest.mark.asyncio
async def test_WR018_repeated_abort_does_not_interrupt_cleanup():
    service = CleanupService()
    async with session(service) as ws:
        await ws.send(request())
        await service.started.wait()
        await ws.send({"type": "abort", "request_id": A})
        await asyncio.wait_for(service.cleaning.wait(), 1)
        for _ in range(3):
            await ws.send({"type": "abort", "request_id": A})
        await ws.send({"type": "ping", "ping_id": P})
        while (event := await ws.receive())["type"] != "pong":
            assert event["type"] != "aborted"
        assert not service.closed.is_set()
        service.cleanup_release.set()
        assert (await ws.receive())["type"] == "aborted"


@pytest.mark.asyncio
@pytest.mark.parametrize("stage", ["prepare", "stream"])
async def test_WR020_disconnect_joins_request(stage):
    service = HeldService(stage)
    async with session(service) as ws:
        await ws.send(request())
        await service.started.wait()
    assert service.closed.is_set()


@pytest.mark.asyncio
async def test_WR021_serializes_business_and_control_sends():
    entered = asyncio.Event()
    release_send = asyncio.Event()
    in_send = 0
    peak = 0

    async def hook(event):
        nonlocal in_send, peak
        if event["type"] != "websocket.send":
            return
        in_send += 1
        peak = max(peak, in_send)
        entered.set()
        await release_send.wait()
        in_send -= 1

    service = HeldService()
    try:
        async with session(service, hook) as ws:
            await ws.send(request())
            await entered.wait()
            await ws.send({"type": "ping", "ping_id": P})
            # Yield through receive and send; the first business send is held by a barrier.
            for _ in range(10):
                await asyncio.sleep(0)
            observed_peak = peak
            release_send.set()
            assert observed_peak == 1, "Concurrent ASGI sends must be serialized"
            while (await ws.receive())["type"] != "pong":
                pass
    finally:
        release_send.set()


@pytest.mark.asyncio
async def test_WR021_send_failure_ends_handler_and_stream():
    service = HeldService("stream")

    async def fail(event):
        if (
            event["type"] == "websocket.send"
            and json.loads(event["text"])["type"] == "text_delta"
        ):
            raise OSError("Test broken send")

    async with session(service, fail) as ws:
        await ws.send(request())
        await service.started.wait()
        service.release.set()
        try:
            await asyncio.wait_for(asyncio.shield(ws.handler), 1)
        except TimeoutError:
            pytest.fail(
                "A failed sender must invalidate the socket and end the receive loop"
            )
        assert service.closed.is_set()


@pytest.mark.asyncio
async def test_WR018_handler_cancellation_does_not_cancel_cleanup_twice():
    service = CleanupService()
    async with session(service) as ws:
        await ws.send(request())
        await service.started.wait()
        await ws.send({"type": "abort", "request_id": A})
        await asyncio.wait_for(service.cleaning.wait(), 1)
        ws.handler.cancel()
        for _ in range(10):
            await asyncio.sleep(0)
        ws.handler.cancel()
        for _ in range(10):
            await asyncio.sleep(0)
        assert not service.closed.is_set()
        service.cleanup_release.set()
        with pytest.raises(asyncio.CancelledError):
            await asyncio.wait_for(ws.handler, 1)
        assert service.closed.is_set()


@pytest.mark.asyncio
@pytest.mark.parametrize("stage", ["prepare", "stream"])
async def test_WR020_handler_exit_joins_request(stage):
    service = HeldService(stage)
    async with session(service) as ws:
        await ws.send(request())
        await service.started.wait()
        ws.handler.cancel()
        with pytest.raises(asyncio.CancelledError):
            await asyncio.wait_for(ws.handler, 1)
        assert service.closed.is_set()


def test_WR020_WR042_authenticated_expiry_joins_real_route_request(monkeypatch):
    import threading
    from types import SimpleNamespace

    from backend.application.authentication.queries.authenticate import Principal
    from backend.presentation import access_control
    from starlette.websockets import WebSocketDisconnect

    closed = threading.Event()

    class ExpiryService(Service):
        async def prepare_reply(self, *args, **kwargs) -> ChatResponse:
            try:
                await asyncio.Event().wait()
                raise AssertionError("Expiry fixture unexpectedly resumed")
            finally:
                closed.set()

    app = FastAPI()
    app.state.allowed_origins = ["http://testserver"]
    app.state.authentication = SimpleNamespace(
        authenticate=SimpleNamespace(
            execute=lambda token, now: Principal("test-user", 1001)
        )
    )
    monkeypatch.setattr(access_control, "time", SimpleNamespace(time=lambda: 1000))
    app.add_middleware(access_control.AccessControlMiddleware)
    app.include_router(router)
    app.dependency_overrides[get_chat_service] = lambda: ExpiryService()
    with TestClient(app).websocket_connect(
        "/api/ws", headers={"Origin": "http://testserver"}
    ) as ws:
        ws.send_json(request())
        assert ws.receive_json()["type"] == "retrieval_status"
        with pytest.raises(WebSocketDisconnect) as failure:
            ws.receive_json()
        assert failure.value.code == 4001
        assert closed.is_set()


@pytest.mark.asyncio
@pytest.mark.parametrize("stage", ["prepare", "stream"])
@pytest.mark.parametrize("abort_first", [False, True])
async def test_WR016_abort_failure_order_preserves_one_terminal(stage, abort_first):
    class Failure(HeldService):
        fail = True

        async def prepare_reply(self, *args, **kwargs):
            if stage == "prepare":
                await self.wait_or_fail()
            return await Service.prepare_reply(self, *args, **kwargs)

        async def wait_or_fail(self):
            self.started.set()
            try:
                await self.release.wait()
                if self.fail:
                    raise RuntimeError("Test generation failure")
            finally:
                self.closed.set()

        async def stream_answer(self, *args, **kwargs) -> AsyncIterator[str]:
            if stage == "stream":
                await self.wait_or_fail()
            yield "テスト回答"

    service = Failure(stage)
    async with session(service) as ws:
        await ws.send(request())
        await asyncio.wait_for(service.started.wait(), 1)
        if abort_first:
            await ws.send({"type": "abort", "request_id": A})
        else:
            service.release.set()
        while (frame := await ws.receive())["type"] not in {
            "text_done",
            "error",
            "aborted",
        }:
            pass
        assert frame["type"] == ("aborted" if abort_first else "error")
        assert service.closed.is_set()
        await ws.send({"type": "abort", "request_id": A})
        assert (await ws.receive())["code"] == "not_active"
        service.fail = False
        service.release.set()
        await ws.send(request(B))
        while (frame := await ws.receive())["type"] != "text_done":
            assert frame["request_id"] == B
            assert frame["type"] not in {"error", "aborted"}
