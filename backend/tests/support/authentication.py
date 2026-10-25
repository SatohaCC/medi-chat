"""Explicit test-only signing identity, never imported by production code."""

import json
import time
from functools import lru_cache

from backend.config.authentication_settings import read_authentication_settings
from backend.config.origin_settings import read_allowed_origins
from backend.domain.identity.identifiers import UserId
from backend.infrastructure.authentication.access_refresh_tokens import JwtTokens
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


@lru_cache(maxsize=1)
def authentication_environment() -> dict[str, str]:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()
    public = (
        key.public_key()
        .public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
        )
        .decode()
    )
    return {
        "AUTH_ISSUER": "https://test.invalid",
        "AUTH_AUDIENCE": "medi-chat-test",
        "AUTH_KEY_ID": "test",
        "AUTH_PRIVATE_KEY": private,
        "AUTH_PUBLIC_KEYS": json.dumps({"test": public}),
    }


def signed_test_headers() -> dict[str, str]:
    """Sign requests using this process's configured test keys, also inherited by children."""
    settings = read_authentication_settings()
    now = int(time.time())
    token = JwtTokens(
        private_key=settings.private_key.get_secret_value(),
        public_keys=settings.public_keys,
        key_id=settings.key_id,
        issuer=settings.issuer,
        audience=settings.audience,
    ).issue(str(UserId.generate()), now, now + 1800)
    return {
        "Cookie": "medi_chat_access_token=" + token,
        "Origin": read_allowed_origins()[0],
        "X-Medi-Chat-CSRF": "1",
    }


class SignedTestActor:
    """Authenticate business-regression fixtures; boundary tests do not install this."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] in {"http", "websocket"}:
            env = authentication_environment()
            now = int(time.time())
            value = JwtTokens(
                private_key=env["AUTH_PRIVATE_KEY"],
                public_keys=json.loads(env["AUTH_PUBLIC_KEYS"]),
                key_id=env["AUTH_KEY_ID"],
                issuer=env["AUTH_ISSUER"],
                audience=env["AUTH_AUDIENCE"],
            ).issue(str(UserId.generate()), now, now + 1800)
            headers = list(scope["headers"])
            if not any(key == b"cookie" for key, _ in headers):
                headers.append(
                    (b"cookie", ("medi_chat_access_token=" + value).encode())
                )
            if not any(key == b"origin" for key, _ in headers):
                origins = getattr(
                    scope["app"].state, "allowed_origins", ["http://localhost:3000"]
                )
                headers.append((b"origin", origins[0].encode()))
            if not any(key == b"x-medi-chat-csrf" for key, _ in headers):
                headers.append((b"x-medi-chat-csrf", b"1"))
            scope = {**scope, "headers": headers}
        await self.app(scope, receive, send)
