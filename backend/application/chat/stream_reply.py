"""準備済み回答を生成または確認応答としてstreamへ渡すユースケース。"""

from collections.abc import AsyncIterator, Callable, Sequence

from .answer_prompt_builder import build_answer_messages
from .answer_prompt_policy import AnswerPromptPolicy
from .answer_stream import stream_answer
from .chat_models import ChatMessage, ChatResponse
from .llm_contracts import LLMProvider
from .stream_closing import closing_stream


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
