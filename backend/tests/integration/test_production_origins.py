"""Deployment origin defaults reach CORS and HTTP/WebSocket access control."""

import pytest
from backend.main import create_app
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect


@pytest.mark.parametrize("deployment", ["vercel", "production"])
def test_production_origin_policy_is_wired_to_http_and_websocket(
    monkeypatch, deployment
):
    monkeypatch.delenv("ALLOWED_ORIGINS", raising=False)
    monkeypatch.delenv("AUTH_TRUSTED_PROXIES", raising=False)
    monkeypatch.setenv("VERCEL", "1" if deployment == "vercel" else "0")
    monkeypatch.setenv("NODE_ENV", "production")
    monkeypatch.setenv("VERCEL_URL", "preview.vercel.app")
    monkeypatch.setenv("VERCEL_PROJECT_PRODUCTION_URL", "prod.vercel.app")
    monkeypatch.setenv("VERCEL_BRANCH_URL", "branch.vercel.app")
    app = create_app()
    client = TestClient(app)
    for origin in (
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ):
        assert origin not in app.state.allowed_origins
        response = client.options(
            "/api/auth/login",
            headers={"Origin": origin, "Access-Control-Request-Method": "POST"},
        )
        assert response.status_code == 400
        assert "access-control-allow-origin" not in response.headers
        response = client.post(
            "/api/auth/login",
            headers={"Origin": origin, "X-Medi-Chat-CSRF": "1"},
            json={"login_id": "test", "password": "long enough password"},
        )
        assert response.status_code == 403
        assert response.json() == {"detail": {"code": "origin_not_allowed"}}
        with (
            pytest.raises(WebSocketDisconnect) as error,
            client.websocket_connect("/api/ws", headers={"Origin": origin}),
        ):
            pytest.fail("Localhost WebSocket was accepted")
        assert error.value.code == 1008
    if deployment == "vercel":
        response = client.options(
            "/api/auth/login",
            headers={
                "Origin": "https://preview.vercel.app",
                "Access-Control-Request-Method": "POST",
            },
        )
        assert response.status_code == 200
        assert (
            response.headers["access-control-allow-origin"]
            == "https://preview.vercel.app"
        )
        assert response.headers["access-control-allow-credentials"] == "true"


def test_production_respects_explicit_localhost_origin(monkeypatch):
    monkeypatch.setenv("NODE_ENV", "production")
    monkeypatch.setenv("VERCEL", "0")
    monkeypatch.setenv("ALLOWED_ORIGINS", "http://localhost:3000")
    app = create_app()
    response = TestClient(app).options(
        "/api/auth/login",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
