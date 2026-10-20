"""Verify the private-link cookie before any HTTP/WS application work."""

import hashlib
import hmac
import re
import time

from starlette.datastructures import MutableHeaders
from starlette.requests import HTTPConnection
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

COOKIE_NAME = "medi_chat_access"
TOKEN_TTL = 30 * 86400


def valid_access_token(token: str, secret: str, *, now: int | None = None) -> bool:
    match = re.fullmatch(r"v1\.([0-9]{1,12})\.([0-9a-f]{32})\.([0-9a-f]{64})", token)
    if match is None:
        return False
    current = int(time.time()) if now is None else now
    expires = int(match[1])
    if not current < expires <= current + TOKEN_TTL + 60:
        return False
    unsigned = token.rsplit(".", 1)[0]
    expected = hmac.new(
        secret.encode(), f"medi-chat-access:{unsigned}".encode(), hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, match[3])


class AccessControlMiddleware:
    def __init__(self, app: ASGIApp, *, secret: str | None) -> None:
        self.app = app
        self._secret = secret

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if self._secret is None or scope["type"] not in {"http", "websocket"}:
            await self.app(scope, receive, send)
            return
        token = HTTPConnection(scope).cookies.get(COOKIE_NAME, "")
        if not valid_access_token(token, self._secret):
            if scope["type"] == "websocket":
                await send({"type": "websocket.close", "code": 1008})
            else:
                response = JSONResponse(
                    {
                        "detail": {
                            "code": "access_required",
                            "message": "専用リンクからアクセスしてください。",
                        }
                    },
                    status_code=401,
                    headers={
                        "Cache-Control": "private, no-store",
                        "Vary": "Cookie",
                        "Referrer-Policy": "no-referrer",
                    },
                )
                await response(scope, receive, send)
            return

        async def private_send(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers["Cache-Control"] = "private, no-store"
                headers.add_vary_header("Cookie")
                headers["Referrer-Policy"] = "no-referrer"
            await send(message)

        await self.app(scope, receive, private_send)
