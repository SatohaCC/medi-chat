"""HTTP/WS authentication boundary, including direct API requests."""

import time
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from backend.application.authentication.commands.models import LoginResult
from backend.application.authentication.errors import (
    AuthenticationRequired,
    AuthenticationUnavailable,
)
from backend.application.authentication.queries.authenticate import Authenticate
from backend.domain.identity.identifiers import UserId
from backend.presentation import access_control
from backend.presentation.access_control import AccessControlMiddleware
from backend.presentation.authentication_routes import (
    register_authentication_errors,
    router,
)
from backend.tests.infrastructure.test_authentication_tokens import (
    signing_keys as signing_keys,
)
from backend.tests.infrastructure.test_authentication_tokens import tokens as tokens
from fastapi import FastAPI, WebSocket
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

ORIGIN = "http://testserver"
HEADERS = {"Origin": ORIGIN, "X-Medi-Chat-CSRF": "1"}


@pytest.fixture
def protected(tokens):
    app = FastAPI()
    app.state.allowed_origins = [ORIGIN]
    app.state.auth_secure_cookies = False
    app.state.authentication = SimpleNamespace(
        authenticate=Authenticate(tokens), login=Mock(), refresh=Mock(), logout=Mock()
    )
    app.add_middleware(AccessControlMiddleware)
    app.include_router(router)
    register_authentication_errors(app)
    calls = []

    @app.get("/api/search")
    async def search():
        calls.append("search")
        return {"ok": True}

    @app.websocket("/api/ws")
    async def stream(socket: WebSocket):
        await socket.accept()
        calls.append("ws")
        await socket.receive_text()

    return app, TestClient(app), calls


def signed_client(protected, tokens, *, expiry=1800):
    app, client, calls = protected
    now = int(time.time())
    client.cookies.set(
        "medi_chat_access_token",
        tokens.issue(str(UserId.generate()), now, now + expiry),
    )
    return app, client, calls


def test_direct_api_is_closed_and_legacy_credentials_do_not_work(protected):
    app, client, calls = protected
    client.cookies.set("medi_chat_access", "old-secret-cookie")
    for path in (
        "/api/search",
        "/api/chat",
        "/api/attachment-imports",
        "/health",
        "/api?key=old",
    ):
        assert client.get(path).status_code == 401
    assert not calls


def test_normal_api_and_me_never_call_session_storage(protected, tokens):
    app, client, calls = signed_client(protected, tokens)
    assert client.get("/api/search").status_code == 200
    result = client.get("/api/auth/me")
    assert result.status_code == 200
    assert result.headers["cache-control"] == "private, no-store"
    app.state.authentication.login.execute.assert_not_called()
    app.state.authentication.refresh.execute.assert_not_called()


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"Origin": "https://evil.invalid", "X-Medi-Chat-CSRF": "1"},
        {"Origin": ORIGIN},
    ],
)
def test_login_requires_origin_and_csrf(protected, headers):
    app, client, calls = protected
    assert (
        client.post(
            "/api/auth/login",
            headers=headers,
            json={"login_id": "test", "password": "long enough password"},
        ).status_code
        == 403
    )
    app.state.authentication.login.execute.assert_not_called()


def test_login_sets_cookies_without_exposing_tokens(protected):
    app, client, calls = protected
    now = int(time.time())
    app.state.authentication.login.execute.return_value = LoginResult(
        "test-user", now + 1800, now + 604800, "signed", "opaque"
    )
    result = client.post(
        "/api/auth/login",
        headers=HEADERS,
        json={"login_id": "test", "password": "long enough password"},
    )
    assert result.status_code == 200
    assert "signed" not in result.text and "opaque" not in result.text
    cookies = result.headers.get_list("set-cookie")
    assert all(
        "HttpOnly" in cookie and "SameSite=lax" in cookie and "Domain=" not in cookie
        for cookie in cookies
    )
    assert any("Path=/api/auth" in cookie for cookie in cookies)
    assert client.cookies["medi_chat_refresh_token"] == "opaque"


def test_authentication_input_errors_do_not_echo_password(protected):
    _, client, _ = protected
    response = client.post(
        "/api/auth/login",
        headers=HEADERS,
        json={"login_id": "test", "password": "secret"},
    )
    assert response.status_code == 422
    assert "secret" not in response.text


def test_logout_works_with_expired_access_and_storage_failure_is_503(protected):
    app, client, _ = protected
    client.cookies.set("medi_chat_refresh_token", "refresh")
    assert client.post("/api/auth/logout", headers=HEADERS).status_code == 204
    app.state.authentication.logout.execute.side_effect = AuthenticationUnavailable()
    assert client.post("/api/auth/logout", headers=HEADERS).status_code == 503


def test_refresh_rejection_clears_cookies(protected):
    app, client, _ = protected
    app.state.authentication.refresh.execute.side_effect = AuthenticationRequired()
    response = client.post("/api/auth/refresh", headers=HEADERS)
    assert response.status_code == 401
    assert len(response.headers.get_list("set-cookie")) == 2


def test_ws_unauthenticated_and_missing_origin_are_rejected(protected, tokens):
    app, client, calls = protected
    with (
        pytest.raises(WebSocketDisconnect),
        client.websocket_connect("/api/ws", headers={"Origin": ORIGIN}),
    ):
        pass
    signed_client(protected, tokens)
    with pytest.raises(WebSocketDisconnect), client.websocket_connect("/api/ws"):
        pass
    assert not calls


def test_ws_expires_while_waiting(protected, tokens, monkeypatch):
    # Freeze the verification clock so signing/scheduling cannot consume the
    # token's one-second lifetime before the handshake has even been accepted.
    # asyncio.timeout still uses the real monotonic event-loop clock.
    now = int(time.time())
    monkeypatch.setattr(access_control, "time", SimpleNamespace(time=lambda: now))
    _, client, calls = protected
    client.cookies.set(
        "medi_chat_access_token",
        tokens.issue(str(UserId.generate()), now, now + 1),
    )
    with client.websocket_connect("/api/ws", headers={"Origin": ORIGIN}) as ws:
        with pytest.raises(WebSocketDisconnect) as failure:
            ws.receive_text()
        assert failure.value.code == 4001
    assert calls == ["ws"]


def test_unconfigured_authentication_fails_closed(protected):
    app, client, _ = protected
    app.state.authentication = None
    assert client.get("/api/search").status_code == 503


def test_hosted_cookies_are_secure(protected):
    app, client, _ = protected
    app.state.auth_secure_cookies = True
    now = int(time.time())
    app.state.authentication.login.execute.return_value = LoginResult(
        "test-user", now + 1800, now + 604800, "signed", "opaque"
    )
    response = client.post(
        "/api/auth/login",
        headers=HEADERS,
        json={"login_id": "test", "password": "test password long enough"},
    )
    assert all("Secure" in cookie for cookie in response.headers.get_list("set-cookie"))


def test_ws_expiry_cancels_running_generation(tokens):
    import asyncio

    from backend.application.authentication.queries.authenticate import Principal

    app = FastAPI()
    app.state.allowed_origins = [ORIGIN]
    verifier = Mock()
    verifier.execute.return_value = Principal("test-user", int(time.time()) + 1)
    app.state.authentication = SimpleNamespace(authenticate=verifier)
    app.add_middleware(AccessControlMiddleware)
    cancelled = []

    @app.websocket("/api/ws")
    async def generation(socket: WebSocket):
        await socket.accept()
        try:
            await asyncio.Event().wait()
        finally:
            cancelled.append(True)

    with TestClient(app).websocket_connect("/api/ws", headers={"Origin": ORIGIN}) as ws:
        with pytest.raises(WebSocketDisconnect) as failure:
            ws.receive_text()
        assert failure.value.code == 4001
    assert cancelled == [True]
