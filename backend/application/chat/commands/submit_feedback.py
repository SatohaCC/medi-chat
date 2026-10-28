"""Submit or change one user's rating of a completed answer."""

from backend.application.chat.interfaces.feedback import FeedbackTokens, FeedbackWriter
from backend.application.chat.values import Rating


class SubmitFeedback:
    def __init__(self, *, tokens: FeedbackTokens, writer: FeedbackWriter) -> None:
        self._tokens = tokens
        self._writer = writer

    async def execute(self, token: str, user_id: str, rating: Rating) -> None:
        target = self._tokens.verify(token, user_id)
        await self._writer.save(target, rating)
