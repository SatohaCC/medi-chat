"""Cryptography and entropy stay outside use cases."""

from typing import Protocol


class TokenIssuer(Protocol):
    def issue(self, user_id: str, now: int, absolute_expiry: int) -> str: ...


class TokenVerifier(Protocol):
    def verify(self, token: str, now: int) -> tuple[str, int, int]: ...


class TokenSecrets(Protocol):
    def generate(self) -> str: ...
    def digest(self, token: str) -> str: ...
