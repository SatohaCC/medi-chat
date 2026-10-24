"""準備済み回答を生成または確認応答としてstreamへ渡すユースケース。"""

from collections.abc import AsyncIterator, Callable, Sequence

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
from backend.application.chat.queries.services.stream_lifetime import closing_stream


async def stream_reply(
    reply: ChatResponse,
    conversation: Sequence[ChatMessage],
    *,
    answer_prompt_policy: AnswerPromptPolicy,
    provider_factory: Callable[[str | None], LLMProvider],
    provider_name: str | None,
    model_name: str | None,
) -> AsyncIterator[str]:
    if reply.needs_clarification:
        yield reply.answer
        return
    provider = provider_factory(provider_name)
    messages = build_answer_messages(
        reply, conversation, answer_prompt_policy=answer_prompt_policy
    )
    async with closing_stream(
        stream_answer(provider, messages, model=model_name)
    ) as response:
        async for chunk in response:
            yield chunk
