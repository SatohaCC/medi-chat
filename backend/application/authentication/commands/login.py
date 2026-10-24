"""Authenticate and create a seven-day refresh family."""

from backend.application.authentication.commands.models import LoginResult
from backend.application.authentication.errors import (
    AuthenticationRequired,
    LoginLimited,
)
from backend.application.authentication.interfaces.credentials import CredentialProvider
from backend.application.authentication.interfaces.sessions import Sessions
from backend.application.authentication.interfaces.tokens import (
    TokenIssuer,
    TokenSecrets,
)
from backend.domain.identity.primitives import LoginId, Password


class Login:
    def __init__(
        self,
        provider: CredentialProvider,
        sessions: Sessions,
        tokens: TokenIssuer,
        secrets: TokenSecrets,
    ) -> None:
        self.provider, self.sessions, self.tokens, self.secrets = (
            provider,
            sessions,
            tokens,
            secrets,
        )

    def execute(
        self, login_id: str, password: str, address: str, now: int
    ) -> LoginResult:
        try:
            normalized = LoginId(login_id).value
        except ValueError:
            raise AuthenticationRequired() from None
        if not self.sessions.admit_login(normalized, address, now):
            raise LoginLimited()
        try:
            Password(password)
        except ValueError:
            raise AuthenticationRequired() from None
        verified = self.provider.authenticate(normalized, password)
        if verified is None:
            raise AuthenticationRequired()
        user_id, revision = verified
        refresh = self.secrets.generate()
        absolute = now + 7 * 86400
        access = self.tokens.issue(user_id, now, absolute)
        if not self.sessions.start(
            user_id, revision, self.secrets.digest(refresh), now, absolute
        ):
            raise AuthenticationRequired()
        return LoginResult(
            user_id, min(now + 1800, absolute), absolute, access, refresh
        )
