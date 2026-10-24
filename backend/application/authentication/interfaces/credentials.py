"""Replaceable credential provider contract."""

from typing import Protocol


class CredentialProvider(Protocol):
    def authenticate(self, login_id: str, password: str) -> tuple[str, int] | None:
        """Return an application UserId after trusted identity mapping."""
        ...
