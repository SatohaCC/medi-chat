"""B01-B04/B10-B13/B17-B18: real routes, auth guard and trace ownership."""

from collections.abc import AsyncGenerator
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import Mock
from uuid import uuid4

import pytest
from backend.application.authentication.errors import AuthenticationRequired
from backend.application.chat.commands.submit_feedback import SubmitFeedback
from backend.application.chat.errors import FeedbackTimeout, FeedbackUnavailable
from backend.application.chat.queries.chat import ChatQueries
from backend.application.chat.queries.models import ChatResponse
from backend.application.medicine.errors import InvalidMedicineInput
from backend.infrastructure.observability.feedback_tokens import SignedFeedbackTokens
from backend.presentation.access_control import AccessControlMiddleware
from backend.presentation.chat_routes import router
from backend.presentation.chat_service import AppChatService
from backend.presentation.chat_websocket_routes import router as ws_router
from backend.tests.presentation.test_chat_websocket_lifecycle import completed, request
from fastapi import FastAPI
from fastapi.testclient import TestClient
from langsmith import Client, traceable, tracing_context

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


class Writer:
    def __init__(self):
        self.writes = []
        self.failure = None

    async def save(self, target, rating):
        if self.failure:
            raise self.failure
        self.writes.append((target, rating))


def app_for(writer, codec):
    app = FastAPI()
    app.state.allowed_origins = ["https://test.invalid"]

    def authenticate(token, now):
        if not token:
            raise AuthenticationRequired()
        return SimpleNamespace(user_id="user", expires_at=now + 100)

    app.state.authentication = SimpleNamespace(
        authenticate=SimpleNamespace(execute=authenticate)
    )
    app.state.feedback_command = SubmitFeedback(tokens=codec, writer=writer)
    app.add_middleware(AccessControlMiddleware)
    app.include_router(router)
    return app


def headers():
    return {
        "Origin": "https://test.invalid",
        "X-Medi-Chat-CSRF": "1",
        "Cookie": "medi_chat_access_token=test",
    }


def test_B10_B11_B12_B13_api_contract():
    codec = SignedFeedbackTokens(secret=b"s" * 32, audience="test", clock=lambda: 100)
    writer = Writer()
    app = app_for(writer, codec)
    payload = {
        "feedback_token": codec.issue(uuid4(), "test-project", "user"),
        "rating": "up",
    }
    with TestClient(app) as client:
        response = client.put("/api/chat/feedback", json=payload, headers=headers())
        assert response.status_code == 200
        assert response.json() == {"rating": "up"}
        assert response.headers["cache-control"] == "private, no-store"
        assert len(writer.writes) == 1
        assert (
            client.put(
                "/api/chat/feedback",
                json=payload,
                headers={"Origin": "https://test.invalid", "X-Medi-Chat-CSRF": "1"},
            ).status_code
            == 401
        )
        for body, expected in [
            ({**payload, "rating": "bad"}, 422),
            ({**payload, "feedback_token": ""}, 422),
            ({**payload, "feedback_token": "tampered"}, 403),
            (
                {
                    **payload,
                    "feedback_token": codec.issue(uuid4(), "test-project", "other"),
                },
                403,
            ),
            ({**payload, "run_id": str(uuid4())}, 422),
        ]:
            assert (
                client.put(
                    "/api/chat/feedback", json=body, headers=headers()
                ).status_code
                == expected
            )
        for bad_headers in [
            {},
            {"Origin": "https://evil.invalid", "X-Medi-Chat-CSRF": "1"},
            {"Origin": "https://test.invalid"},
        ]:
            assert (
                client.put(
                    "/api/chat/feedback", json=payload, headers=bad_headers
                ).status_code
                == 403
            )
        assert len(writer.writes) == 1
        for failure, code in [(FeedbackTimeout(), 504), (FeedbackUnavailable(), 503)]:
            writer.failure = failure
            result = client.put("/api/chat/feedback", json=payload, headers=headers())
            assert result.status_code == code
            assert "traceback" not in result.text.lower()
        app.state.feedback_command = None
        assert (
            client.put(
                "/api/chat/feedback", json=payload, headers=headers()
            ).status_code
            == 503
        )


def test_cancel_api_accepts_explicit_null_and_acknowledges_it():
    codec = SignedFeedbackTokens(secret=b"s" * 32, audience="test")
    writer = Writer()
    token = codec.issue(uuid4(), "test-project", "user")
    with TestClient(app_for(writer, codec)) as client:
        for rating in ("up", None, None):
            response = client.put(
                "/api/chat/feedback",
                headers=headers(),
                json={"feedback_token": token, "rating": rating},
            )
            assert response.status_code == 200
            assert response.json() == {"rating": rating}
            assert writer.writes[-1][1] == rating


class Answers:
    is_jev_available = False

    async def answer_question(self, *args, **kwargs):
        return ChatResponse(
            answer="テスト回答", intent="other", retrieval_strategy="test"
        )

    async def prepare_reply(self, *args, **kwargs):
        return await self.answer_question()

    async def stream_answer(self, *args, **kwargs):
        yield "テスト回答"


def test_B01_B02_B17_rest_and_ws_target_actual_answer_run():
    codec = SignedFeedbackTokens(secret=b"s" * 32, audience="test")
    writer = Writer()
    app = app_for(writer, codec)
    app.state.chat_service = AppChatService(
        application_service=cast(ChatQueries, Answers()),
        feedback_token_issuer=codec.issue,
    )
    app.include_router(ws_router)
    trace_client = Mock(spec=Client)
    with (
        tracing_context(enabled=True, client=trace_client, project_name="test-project"),
        TestClient(app) as client,
    ):
        rest = client.post(
            "/api/chat",
            headers=headers(),
            json={"message": "テスト質問", "product_yj_codes": ["123456789012"]},
        )
        assert rest.status_code == 200
        rest_target = codec.verify(rest.json()["feedback_token"], "user")
        assert rest.json()["answer"] == "テスト回答"
        with client.websocket_connect("/api/ws", headers=headers()) as ws:
            ws.send_json(request())
            events = completed(ws)
            ws_target = codec.verify(events[-1]["feedback_token"], "user")
            assert events[-2]["content"] == "テスト回答"
        assert ws_target.run_id != rest_target.run_id
        recorded = {
            call.kwargs["id"]: call.kwargs
            for call in trace_client.create_run.call_args_list
        }
        assert recorded[rest_target.run_id]["name"] == "medi_chat.answer_question"
        assert recorded[ws_target.run_id]["name"] == "medi_chat.stream_answer"
        ws_root = next(
            run for run in recorded.values() if run["name"] == "medi_chat.chat_turn"
        )
        assert ws_root["run_type"] == "chain"
        assert recorded[ws_target.run_id]["parent_run_id"] == ws_root["id"]
        prepare_run = next(
            run for run in recorded.values() if run["name"] == "medi_chat.prepare_reply"
        )
        assert prepare_run["parent_run_id"] == ws_root["id"]
        for target in (rest_target, ws_target):
            assert any(
                call.kwargs.get("run_id") == target.run_id
                and call.kwargs.get("outputs", {}).get("answer") == "テスト回答"
                for call in trace_client.update_run.call_args_list
            )
        assert any(
            call.kwargs.get("run_id") == ws_root["id"]
            and call.kwargs.get("outputs")
            == {"status": "completed", "answer": "テスト回答"}
            for call in trace_client.update_run.call_args_list
        )


async def test_B19_agent_feedback_targets_trace_containing_generation():
    class AgentAnswers:
        is_jev_available = False

        @traceable(name="medi_chat.agent_generation", run_type="llm")
        async def prepare_reply(self, *args: Any, **kwargs: Any) -> ChatResponse:
            return ChatResponse(
                answer="Agent回答",
                intent="general",
                retrieval_strategy="langgraph_agent",
            )

        async def stream_answer(self, *args: Any, **kwargs: Any) -> AsyncGenerator[str]:
            yield "Agent回答"

    codec = SignedFeedbackTokens(secret=b"s" * 32, audience="test")
    app = app_for(Writer(), codec)
    app.state.chat_service = AppChatService(
        application_service=cast(ChatQueries, AgentAnswers()),
        feedback_token_issuer=codec.issue,
    )
    app.include_router(ws_router)
    trace_client = Mock(spec=Client)

    with (
        tracing_context(enabled=True, client=trace_client, project_name="test-project"),
        TestClient(app) as client,
        client.websocket_connect("/api/ws", headers=headers()) as ws,
    ):
        ws.send_json(request())
        events = completed(ws)
        target = codec.verify(events[-1]["feedback_token"], "user")

    runs = {
        call.kwargs["id"]: call.kwargs
        for call in trace_client.create_run.call_args_list
    }
    prepare_run = next(
        run for run in runs.values() if run["name"] == "medi_chat.prepare_reply"
    )
    generation_run = next(
        run for run in runs.values() if run["name"] == "medi_chat.agent_generation"
    )
    stream_run = next(
        run for run in runs.values() if run["name"] == "medi_chat.stream_answer"
    )
    chat_turn = next(
        run for run in runs.values() if run["name"] == "medi_chat.chat_turn"
    )

    assert generation_run["parent_run_id"] == prepare_run["id"]
    assert chat_turn["run_type"] == "chain"
    assert prepare_run["parent_run_id"] == chat_turn["id"]
    assert stream_run["parent_run_id"] == chat_turn["id"]
    assert target.run_id == prepare_run["id"]
    assert target.run_id != stream_run["id"]
    assert any(
        call.kwargs.get("run_id") == chat_turn["id"]
        and call.kwargs.get("outputs") == {"status": "completed", "answer": "Agent回答"}
        for call in trace_client.update_run.call_args_list
    )


async def test_B20_websocket_root_trace_marks_invalid_input_as_error():
    class RejectingAnswers:
        is_jev_available = False

        async def prepare_reply(self, *args: Any, **kwargs: Any) -> ChatResponse:
            raise InvalidMedicineInput("invalid input")

    codec = SignedFeedbackTokens(secret=b"s" * 32, audience="test")
    app = app_for(Writer(), codec)
    app.state.chat_service = AppChatService(
        application_service=cast(ChatQueries, RejectingAnswers())
    )
    app.include_router(ws_router)
    trace_client = Mock(spec=Client)

    with (
        tracing_context(enabled=True, client=trace_client, project_name="test-project"),
        TestClient(app) as client,
        client.websocket_connect("/api/ws", headers=headers()) as ws,
    ):
        ws.send_json(request())
        events = completed(ws)

    assert events[-1]["type"] == "error"
    chat_turn = next(
        call.kwargs
        for call in trace_client.create_run.call_args_list
        if call.kwargs["name"] == "medi_chat.chat_turn"
    )
    assert any(
        call.kwargs.get("run_id") == chat_turn["id"]
        and call.kwargs.get("outputs") == {"status": "invalid_input"}
        and call.kwargs.get("error") == "invalid_input"
        for call in trace_client.update_run.call_args_list
    )


async def test_B03_B04_no_token_when_disabled_or_incomplete():
    codec = SignedFeedbackTokens(secret=b"s" * 32, audience="test")
    service = AppChatService(
        application_service=cast(ChatQueries, Answers()),
        feedback_token_issuer=codec.issue,
    )
    from backend.presentation.chat_models import ChatMessage

    conversation = [ChatMessage(role="user", content="テスト質問")]
    with tracing_context(enabled=False):
        response = await service.answer_question(
            conversation, ["123456789012"], user_id="user"
        )
        assert response.feedback_token is None
    called = []
    stream = service.stream_answer(
        await Answers().prepare_reply(),
        conversation,
        user_id="user",
        on_completed=called.append,
    )
    assert await anext(stream) == "テスト回答"
    await stream.aclose()
    assert called == []
