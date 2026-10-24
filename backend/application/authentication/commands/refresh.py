"""Rotate refresh credentials without extending the login's absolute lifetime."""

from backend.application.authentication.commands.models import LoginResult
from backend.application.authentication.errors import AuthenticationRequired
from backend.application.authentication.interfaces.sessions import Sessions
from backend.application.authentication.interfaces.tokens import (
    TokenIssuer,
    TokenSecrets,
)


class Refresh:
    def __init__(
        self, sessions: Sessions, tokens: TokenIssuer, secrets: TokenSecrets
    ) -> None:
        self.sessions, self.tokens, self.secrets = sessions, tokens, secrets

    def execute(self, token: str, now: int) -> LoginResult:
        if not token or len(token) > 256:
            raise AuthenticationRequired()
        replacement = self.secrets.generate()
        # Failed delivery is deliberately not retried with a consumed credential.
        session = self.sessions.rotate(
            self.secrets.digest(token), self.secrets.digest(replacement), now
        )
        if session is None:
            raise AuthenticationRequired()
        access = self.tokens.issue(session.user_id, now, session.expires_at)
        return LoginResult(
            session.user_id,
            min(now + 1800, session.expires_at),
            session.expires_at,
            access,
            replacement,
        )
