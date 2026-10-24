"""User lifecycle owned by the application."""

from dataclasses import dataclass, replace

from .identifiers import UserId
from .primitives import LoginId


@dataclass(frozen=True, slots=True, kw_only=True)
class User:
    user_id: UserId
    login_id: LoginId
    active: bool = True

    def stop(self) -> User:
        return replace(self, active=False)
