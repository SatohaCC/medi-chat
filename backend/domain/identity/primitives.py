"""Validated local credential inputs; passwords are never normalized."""

from dataclasses import dataclass

from ..foundation.primitives.base import DomainPrimitive


@dataclass(frozen=True, slots=True)
class LoginId(DomainPrimitive[str]):
    def _normalize(self, value: str) -> str:
        return value.strip()

    def validate(self) -> None:
        if not 1 <= len(self.value) <= 128 or any(ord(c) < 32 for c in self.value):
            raise ValueError("Invalid login ID")


@dataclass(frozen=True, slots=True, repr=False)
class Password(DomainPrimitive[str]):
    def validate(self) -> None:
        if not 15 <= len(self.value) <= 128:
            raise ValueError("Password must contain 15 to 128 characters")

    def __repr__(self) -> str:
        return "Password(<redacted>)"

    def __str__(self) -> str:
        return "<redacted>"
