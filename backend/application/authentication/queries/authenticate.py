"""Translate a verified token to an application principal."""

from dataclasses import dataclass

from backend.application.authentication.errors import AuthenticationRequired
from backend.application.authentication.interfaces.tokens import TokenVerifier
from backend.domain.foundation.exceptions import DomainValidationError
from backend.domain.identity.identifiers import UserId


@dataclass(frozen=True, slots=True)
class Principal:
    user_id: str
    expires_at: int


class Authenticate:
    def __init__(self, verifier: TokenVerifier) -> None:
        self.verifier = verifier

    def execute(self, token: str, now: int) -> Principal:
        user_id, _, expires = self.verifier.verify(token, now)
        try:
            identity = UserId.parse(user_id)
        except DomainValidationError:
            raise AuthenticationRequired() from None
        return Principal(str(identity), expires)
