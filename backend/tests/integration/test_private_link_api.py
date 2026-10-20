"""Actual application routes remain closed even when Next.js is bypassed."""

import pytest
from backend.main import create_app
from backend.tests.presentation.test_access_control import SECRET, token
from backend.tests.support.postgres_fixtures import pg_api as pg_api
from backend.tests.support.postgres_fixtures import pg_engines as pg_engines
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect


def test_remote_database_requires_access_key_even_without_platform_flag(monkeypatch):
    monkeypatch.delenv("VERCEL", raising=False)
    monkeypatch.delenv("APP_SECRET_KEY", raising=False)
    monkeypatch.setenv("MEDI_CHAT_DATABASE_HOSTS", "test.example.neon.tech")
    with pytest.raises(ValueError, match="APP_SECRET_KEY"):
        create_app(
            database_url="postgresql://test:test@test.example.neon.tech/test?sslmode=require&channel_binding=require"
        )


def test_real_application_protects_http_and_websocket(pg_api, monkeypatch):
    monkeypatch.setenv("APP_SECRET_KEY", SECRET)
    app = pg_api()
    with TestClient(app) as client:
        for path in (
            "/api/chat",
            "/api/attachment-imports",
            "/api/attachment-imports/uploads",
        ):
            assert client.post(path, json={}).status_code == 401
        assert client.get("/api").status_code == 401
        assert client.get("/api?key=" + SECRET).status_code == 401
        with (
            pytest.raises(WebSocketDisconnect),
            client.websocket_connect(
                "/api/ws", headers={"origin": "http://localhost:3000"}
            ),
        ):
            pass
        client.cookies.set("medi_chat_access", token())
        assert client.get("/api").status_code == 200
        assert client.get("/api/search?q=頭痛").status_code == 200
        assert (
            client.options(
                "/api/attachment-imports/uploads/test/parts/0",
                headers={
                    "origin": "http://localhost:3000",
                    "access-control-request-method": "POST",
                    "access-control-request-headers": "content-type",
                },
            ).status_code
            == 200
        )
        with client.websocket_connect(
            "/api/ws", headers={"origin": "http://localhost:3000"}
        ) as ws:
            ws.send_json({"type": "ping"})
            assert ws.receive_json() == {"type": "pong"}
