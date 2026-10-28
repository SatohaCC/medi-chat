"""Capabilities for signed feedback targets and acknowledged writes."""

from typing import Protocol
from uuid import UUID

from backend.application.chat.values import FeedbackTarget, Rating


class FeedbackTokens(Protocol):
    def issue(self, run_id: UUID, project_name: str, user_id: str) -> str: ...

    def verify(self, token: str, user_id: str) -> FeedbackTarget: ...


class FeedbackWriter(Protocol):
    async def save(self, target: FeedbackTarget, rating: Rating) -> None: ...
