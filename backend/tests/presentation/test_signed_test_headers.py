"""Business regression actors exercise the actual authentication middleware."""

from types import SimpleNamespace

from backend.application.authentication.queries.authenticate import Authenticate
from backend.config.authentication_settings import read_authentication_settings
from backend.config.origin_settings import read_allowed_origins
from backend.infrastructure.authentication.access_refresh_tokens import JwtTokens
from backend.presentation.access_control import AccessControlMiddleware
from backend.tests.support.authentication import signed_test_headers
from fastapi import FastAPI, WebSocket
from fastapi.testclient import TestClient


def test_explicit_signed_actor_passes_http_mutation_and_websocket_boundary():
    settings = read_authentication_settings()
    tokens = JwtTokens(
        private_key=settings.private_key.get_secret_value(),
        public_keys=settings.public_keys,
        key_id=settings.key_id,
        issuer=settings.issuer,
        audience=settings.audience,
    )
    app = FastAPI()
    app.state.allowed_origins = read_allowed_origins()
    app.state.authentication = SimpleNamespace(authenticate=Authenticate(tokens))
    app.add_middleware(AccessControlMiddleware)

    @app.post("/api/test")
    async def mutate():
        return {"ok": True}

    @app.websocket("/api/ws")
    async def stream(socket: WebSocket):
        await socket.accept()
        await socket.send_json({"ok": True})
        await socket.close()

    with TestClient(app) as client:
        assert client.post("/api/test").status_code == 403
        response = client.post("/api/test", headers=signed_test_headers())
        assert response.status_code == 200
        with client.websocket_connect("/api/ws", headers=signed_test_headers()) as ws:
            assert ws.receive_json() == {"ok": True}
