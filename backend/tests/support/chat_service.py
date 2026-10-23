"""Explicit service composition for API tests with selected test dependencies."""

from collections.abc import Callable

from backend.application.chat.interfaces.llm_provider import LLMProvider
from backend.application.chat.queries.chat import (
    ChatQueries,
)
from backend.application.retrieval.interfaces.intent_classifier import (
    IntentClassifier,
)
from backend.application.retrieval.interfaces.keyword_extractor import (
    KeywordExtractor,
)
from backend.presentation.chat_service import AppChatService


def compose_chat_service(
    original: AppChatService,
    *,
    intent_classifier: IntentClassifier | None = None,
    keyword_extractor: KeywordExtractor | None = None,
    provider_factory: Callable[[str | None], LLMProvider] | None = None,
) -> AppChatService:
    application = original._app_service
    return AppChatService(
        application_service=ChatQueries(
            intent_classifier=intent_classifier
            if intent_classifier is not None
            else application.intent_classifier,
            keyword_extractor=keyword_extractor
            if keyword_extractor is not None
            else application.keyword_extractor,
            intent_policy=application.intent_policy,
            answer_prompt_policy=application.answer_prompt_policy,
            provider_factory=provider_factory
            if provider_factory is not None
            else application.provider_factory,
            snapshot_provider=application.snapshot_provider,
        ),
        defaults=original.defaults,
    )
