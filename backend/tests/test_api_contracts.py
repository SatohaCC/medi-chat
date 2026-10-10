"""REST/WSおよびOpenAPI公開契約のベースライン一致を検証する。"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from unittest.mock import patch

import httpx
import pytest
from backend.infrastructure.persistence.index_writer import SqlAlchemyIndexWriter
from backend.infrastructure.sources.file_index_source import FileIndexSourceReader
from backend.main import create_app
from backend.presentation.chat_models import ChatResponse
from backend.presentation.dependencies import get_chat_service
from backend.tests.test_package_insert_index import migrated_index as migrated_index
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from starlette.websockets import WebSocketDisconnect

REPO_ROOT = Path(__file__).resolve().parents[2]
LEGACY_OPENAPI_PATH = (
    REPO_ROOT
    / "tmp"
    / "feature-pipeline"
    / "20261002-ddd-onion-sqlalchemy-alembic"
    / "legacy-openapi-reference.json"
)


@pytest.mark.asyncio
async def test_rest_and_openapi_contracts_match_baseline(
    migrated_index: tuple[Path, Engine],
) -> None:
    source, engine = migrated_index
    SqlAlchemyIndexWriter(engine).replace(FileIndexSourceReader(source).read_snapshot())
    assert engine.url.database is not None
    index_path = Path(engine.url.database)

    # 1. OpenAPI契約比較
    reference_data = json.loads(LEGACY_OPENAPI_PATH.read_text(encoding="utf-8"))
    expected_openapi = reference_data["schema"]
    app = create_app(source, index_path)
    actual_openapi = app.openapi()
    assert actual_openapi == expected_openapi

    # 2. RESTエンドポイント比較
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
        assert health_json["unit_count"] == 3

        # /api/medicines 省略
        res_med_default = await client.get("/api/medicines")
        assert res_med_default.status_code == 200
        items = res_med_default.json()["items"]
        assert len(items) >= 1

        # /api/medicines 通常クエリ
        res_med_query = await client.get("/api/medicines?query=テスト薬")
        assert res_med_query.status_code == 200
        assert len(res_med_query.json()["items"]) >= 1

        # /api/medicines 200文字境界
        res_med_200 = await client.get(f"/api/medicines?query={'a' * 200}")
        assert res_med_200.status_code == 200

        # /api/medicines 201文字超過 -> 422
        res_med_201 = await client.get(f"/api/medicines?query={'a' * 201}")
        assert res_med_201.status_code == 422

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
    migrated_index: tuple[Path, Engine],
) -> None:
    source, engine = migrated_index
    SqlAlchemyIndexWriter(engine).replace(FileIndexSourceReader(source).read_snapshot())
    assert engine.url.database is not None
    index_path = Path(engine.url.database)

    app = create_app(source, index_path)
    client = TestClient(app)
    with client:
        # 1. Ping-pong
        with client.websocket_connect("/ws/chat") as ws:
            ws.send_json({"type": "ping"})
            pong = ws.receive_json()
            assert pong == {"type": "pong"}

        # 2. Input validation error (missing product_yj_codes)
        with client.websocket_connect("/ws/chat") as ws:
            ws.send_json(
                {
                    "type": "message",
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


def test_http_and_ws_dependencies_can_be_overridden(
    migrated_index: tuple[Path, Engine],
) -> None:
    source, engine = migrated_index
    SqlAlchemyIndexWriter(engine).replace(FileIndexSourceReader(source).read_snapshot())
    assert engine.url.database is not None
    index_path = Path(engine.url.database)

    app = create_app(source, index_path)

    class FakeChatService:
        def __init__(self) -> None:
            self.calls = 0

        @property
        def is_jev_available(self) -> bool:
            return False

        async def answer_question(
            self,
            conversation: Any,
            product_yj_codes: Any,
            provider_name: Any = None,
            model_name: Any = None,
        ) -> ChatResponse:
            self.calls += 1
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
            self, conversation: Any, product_yj_codes: Any
        ) -> ChatResponse:
            self.calls += 1
            return ChatResponse(
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
        ) -> Any:
            yield "FAKE_CHUNK_1"
            yield "FAKE_CHUNK_2"

    fake_service = FakeChatService()
    app.dependency_overrides[get_chat_service] = lambda: fake_service

    client = TestClient(app)
    with client:
        # 1. HTTP override
        res = client.post(
            "/api/chat",
            json={
                "message": "テスト",
                "product_yj_codes": ["1234567A0000"],
            },
        )
        assert res.status_code == 200
        assert res.json()["answer"] == "FAKE_HTTP_ANSWER"

        # 2. WS override
        with client.websocket_connect("/ws/chat") as ws:
            ws.send_json(
                {
                    "type": "message",
                    "product_yj_codes": ["1234567A0000"],
                    "messages": [{"role": "user", "content": "テスト"}],
                }
            )
            chunks: list[str] = []
            while True:
                msg = ws.receive_json()
                if msg["type"] == "text_delta":
                    chunks.append(msg["content"])
                elif msg["type"] == "text_done":
                    break
            assert "".join(chunks) == "FAKE_CHUNK_1FAKE_CHUNK_2"

        assert fake_service.calls == 2


def test_create_app_retains_existing_arguments(
    migrated_index: tuple[Path, Engine],
) -> None:
    source, engine = migrated_index
    SqlAlchemyIndexWriter(engine).replace(FileIndexSourceReader(source).read_snapshot())
    assert engine.url.database is not None
    index_path = Path(engine.url.database)

    def fake_factory(name: str | None) -> Any:
        return object()

    # 1. 3 positional arguments: (structured_dir, index_path, llm_provider_factory)
    app1 = create_app(source, index_path, fake_factory)
    assert app1 is not None

    # 2. database_url as keyword argument
    db_url = f"sqlite:///{index_path.as_posix()}"
    app2 = create_app(source, index_path, fake_factory, database_url=db_url)
    assert app2 is not None

    # 3. database_url passed positionally must raise TypeError (keyword-only)
    with pytest.raises(TypeError):
        create_app(source, index_path, fake_factory, db_url)  # type: ignore[misc]

    # Verify factory is set on chat_service during lifespan
    client = TestClient(app1)
    with client:
        assert app1.state.chat_service.provider_factory is fake_factory


def test_existing_provider_and_invalid_ws_behaviors_are_preserved(
    migrated_index: tuple[Path, Engine],
) -> None:
    source, engine = migrated_index
    SqlAlchemyIndexWriter(engine).replace(FileIndexSourceReader(source).read_snapshot())
    assert engine.url.database is not None
    index_path = Path(engine.url.database)

    app = create_app(source, index_path)
    client = TestClient(app)
    with client:
        # 1. Unsupported provider returns validation error
        with client.websocket_connect("/ws/chat") as ws:
            ws.send_json(
                {
                    "type": "message",
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
            assert data["type"] == "error"
            assert "Payload must be a JSON object" in data["content"]
            # Connection stays open to send ping
            ws.send_json({"type": "ping"})
            pong = ws.receive_json()
            assert pong == {"type": "pong"}

        # 4. Fallback mock responses when API key is unset
        with (
            patch.dict(os.environ, {"OPENAI_API_KEY": ""}),
            client.websocket_connect("/ws/chat") as ws,
        ):
            ws.send_json(
                {
                    "type": "message",
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
