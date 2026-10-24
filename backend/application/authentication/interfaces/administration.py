"""Credential management capabilities used only by trusted administrative commands."""

from typing import Protocol


class UserAdministration(Protocol):
    def provision(
        self, user_id: str, login_id: str, password_hash: str, subject: str
    ) -> None: ...
    def manage(self, login_id: str, *, password_hash: str | None = None) -> bool: ...
    def cleanup(self, now: int) -> int: ...


class PasswordHashing(Protocol):
    def hash(self, password: str) -> str: ...
