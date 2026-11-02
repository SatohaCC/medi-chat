"""Request-scoped LangGraph orchestration and stream-provider adaptation."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Sequence
from contextlib import AbstractAsyncContextManager, AsyncExitStack
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.tools import BaseTool

from backend.application.chat.interfaces.llm_provider import LLMProvider
from backend.application.chat.interfaces.medical_tool import (
    MedicalTool,
    MedicalToolProvider,
)
from backend.application.chat.queries.models import (
    AnswerPromptPolicy,
    ChatMessage,
    ChatResponse,
)
from backend.application.chat.queries.services.stream_lifetime import closing_stream
from backend.application.retrieval.queries.models import Evidence
from backend.infrastructure.agent.agent_graph_builder import build_chat_agent_graph
from backend.infrastructure.agent.agent_payloads import AgentGraphState


class LLMProviderChatModelAdapter:
    """Adapt a text-only provider; reject unsupported native tool calling."""

    def __init__(self, provider: LLMProvider, default_model: str | None = None) -> None:
        self.provider = provider
        self.default_model = default_model

    async def ainvoke(
        self, messages: Sequence[BaseMessage], config: Any = None
    ) -> AIMessage:
        converted = []
        for message in messages:
            if isinstance(message, SystemMessage):
                role = "system"
            elif isinstance(message, HumanMessage):
                role = "user"
            elif isinstance(message, AIMessage) and not message.tool_calls:
                role = "assistant"
            else:
                raise ValueError("Text-only LLMProvider cannot carry tool messages")
            converted.append({"role": role, "content": message.text})
        async with closing_stream(
            self.provider.stream_response(converted, model=self.default_model)
        ) as stream:
            return AIMessage(content="".join([chunk async for chunk in stream]))

    def bind_tools(self, tools: Sequence[BaseTool]) -> Any:
        raise ValueError(
            "Text-only LLMProvider does not support tool calling; use a native chat model"
        )


class LangGraphChatAgentAdapter:
    """Run one bounded graph with isolated model ownership for each request."""

    def __init__(
        self,
        tools: Sequence[MedicalTool | BaseTool] = (),
        *,
        model: Any = None,
        model_factory: Callable[
            [str | None, str | None], AbstractAsyncContextManager[Any]
        ]
        | None = None,
        answer_prompt_policy: AnswerPromptPolicy | None = None,
        timeout_seconds: float = 120,
        max_tool_rounds: int = 4,
        mandatory_tool_provider: MedicalToolProvider | None = None,
    ) -> None:
        if timeout_seconds <= 0 or max_tool_rounds < 1:
            raise ValueError("Agent execution limits must be positive")
        if model is not None and model_factory is not None:
            raise ValueError("Choose a model or a request model factory")
        self.timeout_seconds = timeout_seconds
        self.graph = build_chat_agent_graph(
            tools,
            model=model,
            model_factory=model_factory,
            answer_prompt_policy=answer_prompt_policy,
            max_tool_rounds=max_tool_rounds,
            mandatory_tool_provider=mandatory_tool_provider,
        )
        self.recursion_limit = 2 * max_tool_rounds + 5

    async def run(
        self,
        conversation: Sequence[ChatMessage],
        product_yj_codes: Sequence[str] = (),
        *,
        provider_name: str | None = None,
        model_name: str | None = None,
        on_sources: Callable[[list[Evidence]], Awaitable[None]] | None = None,
    ) -> ChatResponse:
        # Client-supplied system messages cannot override the grounding policy.
        messages: list[BaseMessage] = [
            HumanMessage(content=m.content)
            if m.role == "user"
            else AIMessage(content=m.content)
            for m in conversation
            if m.role != "system"
        ]
        initial: AgentGraphState = {
            "messages": messages,
            "collected_sources": [],
            "collected_medicines": [],
            "collected_notices": [],
            "needs_clarification": False,
            "clarification_message": "",
            "intent": "general",
            "jev_response": None,
            "qualifying_intents": (),
            "tool_rounds": 0,
        }
        async with AsyncExitStack() as stack:
            async with asyncio.timeout(self.timeout_seconds):
                final = await self.graph.ainvoke(
                    initial,
                    config={
                        "recursion_limit": self.recursion_limit,
                        "configurable": {
                            "conversation": conversation,
                            "product_yj_codes": product_yj_codes,
                            "on_sources": on_sources,
                            "provider_name": provider_name,
                            "model_name": model_name,
                            "model_holder": [],
                            "model_stack": stack,
                        },
                    },
                )
        last = final["messages"][-1]
        if not isinstance(last, AIMessage) or last.tool_calls or not last.text.strip():
            raise ValueError("Agent did not produce a final text answer")
        return ChatResponse(
            answer=last.text,
            intent=final.get("intent", "general"),
            retrieval_strategy="langgraph_agent",
            resolved_medicines=final.get("collected_medicines", []),
            sources=final.get("collected_sources", []),
            needs_clarification=final.get("needs_clarification", False),
            notices=final.get("collected_notices", []),
            qualifying_intents=final.get("qualifying_intents", ()),
            jev_response=final.get("jev_response"),
        )
