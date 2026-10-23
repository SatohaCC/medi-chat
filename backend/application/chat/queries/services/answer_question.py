"""回答準備と回答生成をつなぐ技術非依存入口。"""

from collections.abc import Callable, Sequence

from backend.application.chat.interfaces.llm_provider import LLMProvider
from backend.application.chat.queries.models import (
    AnswerPromptPolicy,
    ChatMessage,
    ChatResponse,
)
from backend.application.chat.queries.policies.answer_prompt import (
    build_answer_messages,
)
from backend.application.chat.queries.services.answer_generation import stream_answer
from backend.application.chat.queries.services.reply_preparation import prepare_reply
from backend.application.retrieval.interfaces.intent_classifier import (
    IntentClassifier,
)
from backend.application.retrieval.interfaces.keyword_extractor import (
    KeywordExtractor,
)
from backend.application.retrieval.interfaces.snapshot_provider import (
    RetrievalSnapshotProvider,
)
from backend.application.retrieval.queries.models import IntentPolicy
from backend.application.retrieval.queries.policies.standard import (
    DEFAULT_RETRIEVAL_POLICY,
    EvidenceRetrievalPolicy,
)


async def answer_question(
    conversation: Sequence[ChatMessage],
    product_yj_codes: list[str],
    *,
    intent_classifier: IntentClassifier,
    keyword_extractor: KeywordExtractor,
    intent_policy: IntentPolicy,
    retrieval_policy: EvidenceRetrievalPolicy = DEFAULT_RETRIEVAL_POLICY,
    answer_prompt_policy: AnswerPromptPolicy,
    provider_factory: Callable[[str | None], LLMProvider],
    provider_name: str | None,
    model_name: str | None,
    snapshot_provider: RetrievalSnapshotProvider,
) -> ChatResponse:
    reply = await prepare_reply(
        conversation,
        product_yj_codes,
        intent_classifier=intent_classifier,
        keyword_extractor=keyword_extractor,
        intent_policy=intent_policy,
        retrieval_policy=retrieval_policy,
        snapshot_provider=snapshot_provider,
    )
    if reply.needs_clarification:
        return reply

    provider = provider_factory(provider_name)
    messages = build_answer_messages(
        reply, conversation, answer_prompt_policy=answer_prompt_policy
    )
    reply.answer = "".join(
        [chunk async for chunk in stream_answer(provider, messages, model=model_name)]
    )
    return reply
