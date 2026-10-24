"""Atomic shared refresh state, not a process-local login cache."""

from typing import Protocol

from backend.application.authentication.commands.models import RefreshSession


class Sessions(Protocol):
    def start(
        self, user_id: str, revision: int, digest: str, now: int, expires_at: int
    ) -> bool: ...
    def rotate(
        self, digest: str, replacement: str, now: int
    ) -> RefreshSession | None: ...
    def revoke(self, digest: str) -> None: ...
    def admit_login(self, login_id: str, address: str, now: int) -> bool: ...
