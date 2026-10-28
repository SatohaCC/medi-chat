"""Optional feedback capability configuration; no generated fallback secret."""

import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class FeedbackSettings:
    secret: bytes = field(repr=False)
    endpoint: str


def read_feedback_settings() -> FeedbackSettings | None:
    secret = os.environ.get("MEDI_CHAT_FEEDBACK_SECRET", "").encode()
    if len(secret) < 32:
        return None
    return FeedbackSettings(
        secret=secret,
        endpoint=os.environ.get("LANGSMITH_ENDPOINT")
        or os.environ.get("LANGCHAIN_ENDPOINT")
        or "https://api.smith.langchain.com",
    )
