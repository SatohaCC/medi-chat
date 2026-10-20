import hashlib
import hmac
import time

import pytest
from backend.config.access_settings import read_access_secret
from backend.presentation.access_control import AccessControlMiddleware
from fastapi import FastAPI, WebSocket
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

SECRET = "test-access-key-for-issue-29-only-123456"


def token(secret=SECRET, *, expires=None):
    unsigned = f"v1.{expires or int(time.time()) + 3600}.{'a' * 32}"
    digest = hmac.new(
        secret.encode(), f"medi-chat-access:{unsigned}".encode(), hashlib.sha256
    ).hexdigest()
    return f"{unsigned}.{digest}"


def test_hosted_configuration_fails_closed_and_local_is_opt_in():
    assert read_access_secret({}) is None
    assert read_access_secret({"APP_SECRET_KEY": SECRET}) == SECRET
    with pytest.raises(ValueError):
        read_access_secret({}, required=True)
    for env in (
        {"VERCEL": "1"},
        {"APP_SECRET_KEY": "short"},
        {"VERCEL": "1", "APP_SECRET_KEY": ""},
    ):
        with pytest.raises(ValueError):
            read_access_secret(env)


@pytest.fixture
def protected():
    calls = []
    app = FastAPI()

    @app.api_route("/{path:path}", methods=["GET", "POST"])
    async def endpoint(path: str):
        calls.append(path)
        return {"ok": True}

    @app.websocket("/api/ws")
    async def socket(ws: WebSocket):
        calls.append("socket")
        await ws.accept()
        await ws.send_json({"type": "pong"})

    app.add_middleware(AccessControlMiddleware, secret=SECRET)
    with TestClient(app) as client:
        yield client, calls


@pytest.mark.parametrize(
    "path", ["/api/chat", "/api/attachment-imports", "/api/search", "/api", "/health"]
)
def test_unauthenticated_requests_never_reach_application(protected, path):
    client, calls = protected
    response = client.post(path + "?key=" + SECRET)
    assert response.status_code == 401
    assert calls == []
    assert "no-store" in response.headers["cache-control"]


@pytest.mark.parametrize(
    "cookie",
    [
        "bad",
        token(secret="wrong"),
        token(expires=1),
        token(expires=int(time.time()) + 40 * 86400),
    ],
)
def test_invalid_and_expired_tokens_are_denied(protected, cookie):
    client, calls = protected
    client.cookies.set("medi_chat_access", cookie)
    assert client.get("/api/chat").status_code == 401
    assert calls == []


def test_authenticated_http_and_websocket(protected):
    client, calls = protected
    client.cookies.set("medi_chat_access", token())
    assert client.get("/api/search").status_code == 200
    with client.websocket_connect("/api/ws") as ws:
        assert ws.receive_json() == {"type": "pong"}
    assert calls == ["api/search", "socket"]


def test_unauthenticated_websocket_never_reaches_application(protected):
    client, calls = protected
    with pytest.raises(WebSocketDisconnect), client.websocket_connect("/api/ws"):
        pass
    assert calls == []
