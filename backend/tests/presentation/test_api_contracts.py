"""REST/WSおよびOpenAPI公開契約のベースライン一致を検証する。"""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from copy import deepcopy
from typing import Any
from unittest.mock import patch

import httpx
import pytest
from backend.main import create_app
from backend.presentation.chat_models import ChatResponse
from backend.presentation.dependencies import get_chat_service
from backend.tests.support.paths import FIXTURES_ROOT, PROJECT_ROOT
from backend.tests.support.postgres_fixtures import pg_api as pg_api
from backend.tests.support.postgres_fixtures import pg_engines as pg_engines
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

REPO_ROOT = PROJECT_ROOT
LEGACY_OPENAPI_PATH = FIXTURES_ROOT / "current-openapi-reference.json"


def test_openapi_contracts_match_baseline() -> None:
    # Schema generation does not need database engines or a running lifespan.
    reference_data = json.loads(LEGACY_OPENAPI_PATH.read_text(encoding="utf-8"))
    expected_openapi = reference_data["schema"]
    app = create_app(database_url="postgresql+psycopg://unused@127.0.0.1:1/unused")
    actual_openapi = deepcopy(app.openapi())
    feedback = actual_openapi["paths"].pop("/api/chat/feedback")["put"]
    assert feedback["requestBody"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/FeedbackRequest"
    }
    assert feedback["responses"]["200"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/FeedbackResponse"
    }
    schemas = actual_openapi["components"]["schemas"]
    assert schemas["FeedbackRequest"]["properties"]["rating"]["anyOf"] == [
        {"type": "string", "enum": ["up", "down"]},
        {"type": "null"},
    ]
    assert schemas["FeedbackRequest"]["additionalProperties"] is False
    for name in ("FeedbackRequest", "FeedbackResponse"):
        del schemas[name]
    token = schemas["ChatResponse"]["properties"].pop("feedback_token")
    assert token["anyOf"] == [{"type": "string"}, {"type": "null"}]
    assert "feedback_token" not in schemas["ChatResponse"].get("required", [])
    # Authentication is an explicit additive contract; keep existing API shapes frozen.
    for path, method in (
        ("login", "post"),
        ("refresh", "post"),
        ("logout", "post"),
        ("me", "get"),
    ):
        operation = actual_openapi["paths"].pop(f"/api/auth/{path}")
        assert method in operation
    for name in ("LoginInput", "LoginResponse", "PrincipalResponse"):
        del actual_openapi["components"]["schemas"][name]
    for path in (
        "/api/attachment-imports/uploads",
        "/api/attachment-imports/uploads/{upload_id}/parts/{index}",
        "/api/attachment-imports/uploads/{upload_id}/complete",
    ):
        assert "post" in actual_openapi["paths"].pop(path)
    del actual_openapi["components"]["schemas"]["UploadResponse"]
    # The history list is an explicit additive API, covered with real PG in
    # test_import_history.py. Keep the frozen pre-existing contracts exact.
    history_get = actual_openapi["paths"]["/api/attachment-imports"].pop("get")
    assert history_get["responses"]["200"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/ImportListResponse"
    }
    for name in ("ImportListResponse", "ImportSummaryResponse"):
        assert name in actual_openapi["components"]["schemas"]
        del actual_openapi["components"]["schemas"][name]
    assert actual_openapi == expected_openapi


@pytest.mark.asyncio
async def test_rest_contracts_match_baseline(pg_api) -> None:
    app = pg_api()
    actual_openapi = app.openapi()
    # REST behavior still uses the explicitly owned real PostgreSQL database.
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client,
    ):
        # 軽量プローブ
        res_probe1 = await client.get("/api")
        assert res_probe1.status_code == 200
        assert res_probe1.json() == {"status": "ok"}

        res_probe2 = await client.get("/api/")
        assert res_probe2.status_code == 200
        assert res_probe2.json() == {"status": "ok"}

        # /health
        res_health = await client.get("/health")
        assert res_health.status_code == 200
        health_json = res_health.json()
        assert health_json["status"] == "ok"
        assert health_json["document_count"] == 1
        assert health_json["unit_count"] == 1

        # /api/medicines 省略
        res_med_default = await client.get("/api/medicines")
        assert res_med_default.status_code == 200
        items = res_med_default.json()["items"]
        assert len(items) >= 1

        parameters = actual_openapi["paths"]["/api/medicines"]["get"].get(
            "parameters", []
        )
        assert not any(parameter["name"] == "query" for parameter in parameters)

        # /api/chat 未知YJでの確認応答
        res_chat = await client.post(
            "/api/chat",
            json={
                "message": "頭痛の薬",
                "product_yj_codes": ["999999999999"],
            },
        )
        assert res_chat.status_code == 200
        chat_json = res_chat.json()
        assert chat_json["needs_clarification"] is True
        assert (
            "指定されたYJコード" in chat_json["answer"]
            or "検索データ" in chat_json["answer"]
        )
        # DB内部例外が漏洩していないこと
        assert "sqlite" not in chat_json["answer"].lower()
        assert "traceback" not in chat_json["answer"].lower()


def test_ws_public_events_match_baseline(
    pg_api,
) -> None:

    app = pg_api()
    client = TestClient(app)
    with client:
        # 1. Ping-pong
        with client.websocket_connect("/ws/chat") as ws:
            ws.send_json(
                {"type": "ping", "ping_id": "a871f25a-1eb7-4c5e-8c6e-4511dce60280"}
            )
            pong = ws.receive_json()
            assert pong == {
                "type": "pong",
                "ping_id": "a871f25a-1eb7-4c5e-8c6e-4511dce60280",
            }

        # 2. Input validation error (missing product_yj_codes)
        with client.websocket_connect("/ws/chat") as ws:
            ws.send_json(
                {
                    "type": "message",
                    "request_id": "a871f25a-1eb7-4c5e-8c6e-4511dce60280",
                    "messages": [{"role": "user", "content": "こんにちは"}],
                }
            )
            err = ws.receive_json()
            assert err["type"] == "error"
            assert "product_yj_codes" in err["content"]

        # 3. Input validation error (empty messages)
        with client.websocket_connect("/ws/chat") as ws:
            ws.send_json(
                {
                    "type": "message",
                    "request_id": "a871f25a-1eb7-4c5e-8c6e-4511dce60280",
                    "product_yj_codes": ["1234567A0000"],
                    "messages": [],
                }
            )
            err = ws.receive_json()
            assert err["type"] == "error"

        # 4. Clarification response for unknown YJ code
        with client.websocket_connect("/ws/chat") as ws:
            ws.send_json(
                {
                    "type": "message",
                    "request_id": "a871f25a-1eb7-4c5e-8c6e-4511dce60280",
                    "product_yj_codes": ["999999999999"],
                    "messages": [{"role": "user", "content": "薬の飲み方"}],
                }
            )
            events: list[dict[str, Any]] = []
            while True:
                msg = ws.receive_json()
                events.append(msg)
                if msg["type"] in ("text_done", "error"):
                    break
            types = [e["type"] for e in events]
            assert "retrieval_status" in types
            assert "text_delta" in types
            assert "text_done" in types

        # 5. Normal chat with fallback provider
        with (
            patch.dict(os.environ, {"OPENAI_API_KEY": ""}),
            client.websocket_connect("/ws/chat") as ws,
        ):
            ws.send_json(
                {
                    "type": "message",
                    "request_id": "a871f25a-1eb7-4c5e-8c6e-4511dce60280",
                    "provider": "openai",
                    "product_yj_codes": ["1234567A0000"],
                    "messages": [{"role": "user", "content": "頭痛"}],
                }
            )
            normal_events: list[dict[str, Any]] = []
            while True:
                msg = ws.receive_json()
                normal_events.append(msg)
                if msg["type"] in ("text_done", "error"):
                    break
            normal_types = [e["type"] for e in normal_events]
            assert "retrieval_status" in normal_types
            assert "sources" in normal_types
            assert "text_delta" in normal_types
            assert "text_done" in normal_types
            assert normal_events[-1]["type"] == "text_done"

        # 6. Reject unauthorized origin
        with (
            pytest.raises(WebSocketDisconnect) as cm,
            client.websocket_connect(
                "/ws/chat", headers={"origin": "http://evil.example.com"}
            ),
        ):
            pass
        assert cm.value.code == 1008


@pytest.fixture
def overridden_chat_service():
    class FakeChatService:
        def __init__(self) -> None:
            self.calls = 0
            self.user_ids: list[str] = []
            self.completions = 0

        @property
        def is_jev_available(self) -> bool:
            return False

        async def answer_question(
            self,
            conversation: Any,
            product_yj_codes: Any,
            provider_name: Any = None,
            model_name: Any = None,
            *,
            user_id: str = "",
        ) -> ChatResponse:
            self.calls += 1
            self.user_ids.append(user_id)
            return ChatResponse(
                answer="FAKE_HTTP_ANSWER",
                intent="general",
                retrieval_strategy="mock",
                resolved_medicines=[],
                sources=[],
                needs_clarification=False,
                notices=["fake_notice"],
                jev_response=None,
            )

        async def prepare_reply(
            self, conversation: Any, product_yj_codes: Any, **kwargs: Any
        ) -> Any:
            from backend.application.chat.queries.models import (
                ChatResponse as PreparedReply,
            )

            self.calls += 1
            return PreparedReply(
                answer="FAKE_WS_ANSWER",
                intent="general",
                retrieval_strategy="mock",
                resolved_medicines=[],
                sources=[],
                needs_clarification=False,
                notices=[],
                jev_response=None,
            )

        async def stream_answer(
            self,
            reply: Any,
            conversation: Any,
            provider_name: Any = None,
            model_name: Any = None,
            *,
            user_id: str = "",
            on_completed: Callable[[str | None], None] | None = None,
        ) -> Any:
            self.user_ids.append(user_id)
            yield "FAKE_CHUNK_1"
            yield "FAKE_CHUNK_2"
            if on_completed is not None:
                on_completed(None)
                self.completions += 1

    return FakeChatService()


def test_chat_dependency_override_accepts_feedback_context_without_db(
    overridden_chat_service,
):
    from backend.presentation.chat_routes import router as chat_router
    from backend.presentation.chat_websocket_routes import router as ws_router
    from backend.presentation.dependencies import get_feedback_user_id
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(chat_router)
    app.include_router(ws_router)
    app.dependency_overrides[get_chat_service] = lambda: overridden_chat_service
    app.dependency_overrides[get_feedback_user_id] = lambda: "test-user"
    with TestClient(app) as client:
        response = client.post(
            "/api/chat",
            json={"message": "テスト", "product_yj_codes": ["1234567A0000"]},
        )
        assert response.status_code == 200
        assert response.json()["answer"] == "FAKE_HTTP_ANSWER"
        with client.websocket_connect("/ws/chat") as ws:
            ws.send_json(
                {
                    "type": "message",
                    "request_id": "a871f25a-1eb7-4c5e-8c6e-4511dce60280",
                    "product_yj_codes": ["1234567A0000"],
                    "messages": [{"role": "user", "content": "テスト"}],
                }
            )
            chunks = []
            while True:
                event = ws.receive_json()
                assert event["type"] != "error", event
                if event["type"] == "text_delta":
                    chunks.append(event["content"])
                if event["type"] == "text_done":
                    assert event["feedback_token"] is None
                    break
            assert "".join(chunks) == "FAKE_CHUNK_1FAKE_CHUNK_2"
    assert overridden_chat_service.calls == 2
    assert overridden_chat_service.user_ids == ["test-user", "test-user"]
    assert overridden_chat_service.completions == 1


def test_create_app_refuses_file_arguments_and_keeps_provider_injection(
    pg_api, tmp_path
):
    def fake_factory(name: str | None) -> Any:
        return object()

    with pytest.raises(ValueError, match="Legacy runtime file settings"):
        create_app(tmp_path, tmp_path / "old.sqlite3", fake_factory)
    with pytest.raises(TypeError):
        create_app(None, None, fake_factory, "postgresql://unused")  # type: ignore[misc]
    app = pg_api(llm_provider_factory=fake_factory)
    with TestClient(app):
        assert app.state.chat_service._app_service.provider_factory is fake_factory


def test_existing_provider_and_invalid_ws_behaviors_are_preserved(
    pg_api,
) -> None:

    app = pg_api()
    client = TestClient(app)
    with client:
        # 1. Unsupported provider returns validation error
        with client.websocket_connect("/ws/chat") as ws:
            ws.send_json(
                {
                    "type": "message",
                    "request_id": "a871f25a-1eb7-4c5e-8c6e-4511dce60280",
                    "provider": "unsupported_provider",
                    "product_yj_codes": ["1234567A0000"],
                    "messages": [{"role": "user", "content": "こんにちは"}],
                }
            )
            data = ws.receive_json()
            assert data["type"] == "error"
            assert "Unsupported provider" in data["content"]

        # 2. Unsupported model for valid provider returns validation error
        with client.websocket_connect("/ws/chat") as ws:
            ws.send_json(
                {
                    "type": "message",
                    "request_id": "a871f25a-1eb7-4c5e-8c6e-4511dce60280",
                    "provider": "openai",
                    "model": "unsupported_model_xyz",
                    "product_yj_codes": ["1234567A0000"],
                    "messages": [{"role": "user", "content": "こんにちは"}],
                }
            )
            data = ws.receive_json()
            assert data["type"] == "error"
            assert "Unsupported model" in data["content"]

        # 3. Non-object JSON does not terminate connection (FASTAPI-05 preserved)
        with client.websocket_connect("/ws/chat") as ws:
            ws.send_json("not a json dict")
            data = ws.receive_json()
            assert data["type"] == "connection_error"
            assert data["code"] == "invalid_payload"
            assert "Payload must be a JSON object" in data["content"]
            # Connection stays open to send ping
            ws.send_json(
                {"type": "ping", "ping_id": "a871f25a-1eb7-4c5e-8c6e-4511dce60280"}
            )
            pong = ws.receive_json()
            assert pong == {
                "type": "pong",
                "ping_id": "a871f25a-1eb7-4c5e-8c6e-4511dce60280",
            }

        # 4. Fallback mock responses when API key is unset
        with (
            patch.dict(os.environ, {"OPENAI_API_KEY": ""}),
            client.websocket_connect("/ws/chat") as ws,
        ):
            ws.send_json(
                {
                    "type": "message",
                    "request_id": "a871f25a-1eb7-4c5e-8c6e-4511dce60280",
                    "provider": "openai",
                    "product_yj_codes": ["1234567A0000"],
                    "messages": [{"role": "user", "content": "副作用について"}],
                }
            )
            deltas: list[str] = []
            while True:
                msg = ws.receive_json()
                if msg["type"] == "text_delta":
                    deltas.append(msg["content"])
                elif msg["type"] in ("text_done", "error"):
                    break
            full_text = "".join(deltas)
            assert "副作用について" in full_text
            assert "OpenAI" in full_text
