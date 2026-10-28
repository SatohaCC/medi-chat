"""Own the optional feedback SDK client and its application capabilities."""

from langsmith import Client
from langsmith.utils import get_env_var, tracing_is_enabled
from urllib3.util.retry import Retry

from backend.config.feedback_settings import read_feedback_settings
from backend.infrastructure.observability.feedback_tokens import SignedFeedbackTokens
from backend.infrastructure.observability.langsmith_feedback_adapter import (
    LangSmithFeedback,
)


def compose_feedback() -> tuple[SignedFeedbackTokens, LangSmithFeedback] | None:
    settings = read_feedback_settings()
    if (
        settings is None
        or tracing_is_enabled() is not True
        or not get_env_var("API_KEY")
        or get_env_var("TRACING_SAMPLING_RATE", "1") not in {"1", "1.0"}
    ):
        return None
    client = Client(
        api_url=settings.endpoint,
        auto_batch_tracing=False,
        tracing_sampling_rate=1,
        timeout_ms=(2000, 3000),
        retry_config=Retry(total=0),
    )
    return (
        SignedFeedbackTokens(secret=settings.secret, audience=settings.endpoint),
        LangSmithFeedback(client),
    )
