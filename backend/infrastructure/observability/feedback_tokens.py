"""Short-lived, purpose-bound feedback capabilities; no server-side registry."""

import base64
import hashlib
import hmac
import json
import time
from collections.abc import Callable
from uuid import UUID

from backend.application.chat.errors import FeedbackForbidden
from backend.application.chat.values import FeedbackTarget


class SignedFeedbackTokens:
    def __init__(
        self, *, secret: bytes, audience: str, clock: Callable[[], float] = time.time
    ) -> None:
        if len(secret) < 32:
            raise ValueError("Feedback signing secret must have at least 32 bytes")
        self._secret = secret
        self._audience = audience
        self._clock = clock

    def issue(self, run_id: UUID, project_name: str, user_id: str) -> str:
        now = int(self._clock())
        body = (
            base64.urlsafe_b64encode(
                json.dumps(
                    {
                        "purpose": "chat-feedback-v1",
                        "aud": self._audience,
                        "run": str(run_id),
                        "project": project_name,
                        "sub": user_id,
                        "iat": now,
                        "exp": now + 86400,
                    },
                    separators=(",", ":"),
                ).encode()
            )
            .decode()
            .rstrip("=")
        )
        signature = hmac.new(self._secret, body.encode(), hashlib.sha256).hexdigest()
        return body + "." + signature

    def verify(self, token: str, user_id: str) -> FeedbackTarget:
        try:
            if len(token) > 4096:
                raise ValueError()
            body, signature = token.split(".")
            expected = hmac.new(self._secret, body.encode(), hashlib.sha256).hexdigest()
            if not hmac.compare_digest(signature, expected):
                raise ValueError()
            claims = json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))
            if (
                claims["purpose"] != "chat-feedback-v1"
                or claims["aud"] != self._audience
                or not user_id
                or claims["sub"] != user_id
                or type(claims["iat"]) is not int
                or type(claims["exp"]) is not int
                or not claims["iat"] <= self._clock() < claims["exp"]
                or claims["exp"] - claims["iat"] != 86400
                or not isinstance(claims["project"], str)
                or not claims["project"]
            ):
                raise ValueError()
            return FeedbackTarget(UUID(claims["run"]), claims["project"], user_id)
        except ValueError, TypeError, KeyError, UnicodeError:
            raise FeedbackForbidden() from None
