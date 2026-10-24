"""Enforce authentication before any HTTP/WS application work."""

import asyncio
import time

from starlette.datastructures import MutableHeaders
from starlette.requests import HTTPConnection
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from backend.application.authentication.errors import AuthenticationRequired

from .authentication_models import ACCESS_COOKIE

PUBLIC_AUTH = frozenset({"/api/auth/login", "/api/auth/refresh", "/api/auth/logout"})


class AccessControlMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] not in {"http", "websocket"}:
            await self.app(scope, receive, send)
            return
        connection = HTTPConnection(scope)
        origin = connection.headers.get("origin")
        allowed = getattr(connection.app.state, "allowed_origins", [])
        websocket = scope["type"] == "websocket"
        modifying = not websocket and scope["method"] not in {"GET", "HEAD", "OPTIONS"}

        async def private_send(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers["Cache-Control"] = "private, no-store"
                headers.add_vary_header("Cookie")
                headers["Referrer-Policy"] = "no-referrer"
            await send(message)

        async def deny(code: str, status: int = 401) -> None:
            if websocket:
                await send({"type": "websocket.close", "code": 1008})
            else:
                await JSONResponse({"detail": {"code": code}}, status_code=status)(
                    scope, receive, private_send
                )

        if (websocket or modifying) and (not origin or origin not in allowed):
            await deny("origin_not_allowed", 403)
            return
        if modifying and connection.headers.get("x-medi-chat-csrf") != "1":
            await deny("csrf_required", 403)
            return
        if not websocket and scope["path"] in PUBLIC_AUTH and scope["method"] == "POST":
            await self.app(scope, receive, private_send)
            return
        authentication = getattr(connection.app.state, "authentication", None)
        if authentication is None:
            await deny("authentication_unavailable", 503)
            return
        try:
            principal = authentication.authenticate.execute(
                connection.cookies.get(ACCESS_COOKIE, ""), int(time.time())
            )
        except AuthenticationRequired as error:
            await deny(error.code)
            return
        scope["auth_principal"] = principal
        if not websocket:
            await self.app(scope, receive, private_send)
            return
        accepted = False
        closed = False

        async def ws_send(message: Message) -> None:
            nonlocal accepted, closed
            accepted |= message["type"] == "websocket.accept"
            closed |= message["type"] == "websocket.close"
            await send(message)

        try:
            async with asyncio.timeout(max(0, principal.expires_at - time.time())):
                await self.app(scope, receive, ws_send)
        except TimeoutError:
            if not closed:
                await send(
                    {
                        "type": "websocket.close",
                        "code": 4001 if accepted else 1008,
                        "reason": "access_expired",
                    }
                )
