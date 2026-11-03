"""Bounded native tool-calling graph with one source of grounding state."""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from dataclasses import replace
from typing import Any

from langchain_core.messages import AIMessage, SystemMessage, ToolMessage
from langchain_core.runnables import RunnableConfig, ensure_config
from langchain_core.tools import BaseTool, StructuredTool
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode

from backend.application.chat.interfaces.medical_tool import (
    MedicalTool,
    MedicalToolProvider,
    ToolExecutionInput,
    ToolExecutionResult,
)
from backend.application.chat.queries.models import AnswerPromptPolicy
from backend.application.chat.queries.policies.answer_prompt import (
    build_answer_system_prompt,
)
from backend.application.retrieval.queries.models import Evidence
from backend.application.retrieval.queries.policies.selection import (
    evidence_section_sort_key,
)
from backend.infrastructure.agent.agent_payloads import AgentGraphState


async def execute_medical_tool(
    tool: MedicalTool, query: str, config: RunnableConfig
) -> ToolExecutionResult:
    context = config.get("configurable", {})
    on_sources = context.get("on_sources")
    published = False

    async def publish(sources: list[Evidence]) -> None:
        nonlocal published
        published = True
        if on_sources is not None:
            await on_sources(sources)

    result = await tool.execute(
        ToolExecutionInput(
            message=query,
            conversation=context.get("conversation", ()),
            product_yj_codes=context.get("product_yj_codes", ()),
            on_sources=publish if on_sources is not None else None,
        )
    )
    if on_sources is not None and result.sources and not published:
        await on_sources(list(result.sources))
    return result


def to_langchain_tool(tool_item: MedicalTool | BaseTool) -> BaseTool:
    if isinstance(tool_item, BaseTool):
        return tool_item

    async def search(query: str) -> tuple[str, ToolExecutionResult]:
        result = await execute_medical_tool(tool_item, query, ensure_config())
        summary = "\n".join(
            f"[{s.unit_id.value}] {s.section.get('title', '')}: {s.excerpt.value}"
            for s in result.sources
        )
        return f"【{tool_item.name}】\n{summary or '該当する根拠なし'}", result

    return StructuredTool.from_function(
        coroutine=search,
        name=tool_item.name,
        description=tool_item.description,
        response_format="content_and_artifact",
    )


def merge_results(
    state: AgentGraphState, results: Sequence[ToolExecutionResult]
) -> dict[str, Any]:
    sources = {s.unit_id.value: s for s in state.get("collected_sources", [])}
    medicines = {m.yj_codes: m for m in state.get("collected_medicines", [])}
    notices = list(state.get("collected_notices", []))
    clarification = state.get("needs_clarification", False)
    message = state.get("clarification_message", "")
    intent = state.get("intent", "general")
    jev_response = state.get("jev_response")
    qualifying = state.get("qualifying_intents", ())
    for result in results:
        for source in result.sources:
            existing = sources.get(source.unit_id.value)
            sources[source.unit_id.value] = (
                replace(
                    existing, retrieved_by=existing.retrieved_by | source.retrieved_by
                )
                if existing is not None
                else source
            )
        medicines.update((m.yj_codes, m) for m in result.resolved_medicines)
        notices.extend(result.notices)
        if result.intent != "general":
            intent = result.intent
        if result.jev_response is not None:
            jev_response = result.jev_response
        if result.qualifying_intents:
            qualifying = tuple(dict.fromkeys((*qualifying, *result.qualifying_intents)))
        if result.needs_clarification:
            clarification = True
            message = message or next(
                iter(result.notices), "対象医薬品を@医薬品から選択してください。"
            )
    if qualifying:
        intent = ", ".join(qualifying)
    return {
        "collected_sources": sorted(sources.values(), key=evidence_section_sort_key),
        "collected_medicines": list(medicines.values()),
        "collected_notices": list(dict.fromkeys(notices)),
        "needs_clarification": clarification,
        "clarification_message": message,
        "intent": intent,
        "jev_response": jev_response,
        "qualifying_intents": qualifying,
    }


def build_chat_agent_graph(
    tools: Sequence[MedicalTool | BaseTool],
    model: Any,
    *,
    answer_prompt_policy: AnswerPromptPolicy | None = None,
    model_factory: Any = None,
    max_tool_rounds: int = 4,
    mandatory_tool_provider: MedicalToolProvider | None = None,
) -> Any:
    names = [tool.name for tool in tools]
    if len(set(names)) != len(names):
        raise ValueError("Agent tool names must be unique")
    mandatory = [t for t in tools if isinstance(t, MedicalTool) and t.is_mandatory]
    optional = [
        to_langchain_tool(t) for t in tools if not getattr(t, "is_mandatory", False)
    ]
    tool_node = ToolNode(optional, handle_tool_errors=False)
    workflow = StateGraph(AgentGraphState)

    async def mandatory_node(
        state: AgentGraphState, config: RunnableConfig
    ) -> dict[str, Any]:
        conversation = config.get("configurable", {})["conversation"]
        query = next(
            (m.content for m in reversed(conversation) if m.role == "user"), ""
        )

        async def execute_group(
            request_tools: Sequence[MedicalTool],
        ) -> list[ToolExecutionResult]:
            group_names = names + [t.name for t in request_tools]
            if len(group_names) != len(set(group_names)):
                raise ValueError("Agent tool names must be unique")
            if not all(t.is_mandatory for t in request_tools):
                raise ValueError("Request-scoped tools must be mandatory")
            tasks = [
                asyncio.create_task(execute_medical_tool(t, query, config))
                for t in request_tools
            ]
            try:
                return [await finished for finished in asyncio.as_completed(tasks)]
            finally:
                for task in tasks:
                    if not task.done():
                        task.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)

        results = [await execute_medical_tool(t, query, config) for t in mandatory]
        if mandatory_tool_provider is not None:
            context = config.get("configurable", {})
            request = ToolExecutionInput(
                message=query,
                conversation=conversation,
                product_yj_codes=context.get("product_yj_codes", ()),
                on_sources=context.get("on_sources"),
            )
            async with mandatory_tool_provider.acquire(request) as request_tools:
                results.extend(await execute_group(request_tools))
        merged = merge_results(state, results)
        on_retrieval_complete = config.get("configurable", {}).get(
            "on_retrieval_complete"
        )
        if on_retrieval_complete is not None:
            await on_retrieval_complete(merged["jev_response"])
        if answer_prompt_policy is None:
            merged["messages"] = [
                SystemMessage(
                    content="\n".join(
                        s.excerpt.value for r in results for s in r.sources
                    )
                )
            ]
        return merged

    async def clarification_node(state: AgentGraphState) -> dict[str, Any]:
        return {
            "messages": [
                AIMessage(
                    content=state.get("clarification_message")
                    or "対象医薬品を@医薬品から選択してください。"
                )
            ]
        }

    async def agent_node(
        state: AgentGraphState, config: RunnableConfig
    ) -> dict[str, Any]:
        context = config.get("configurable", {})
        holder = context["model_holder"]
        if not holder:
            selected = model
            if model_factory is not None:
                selected = await context["model_stack"].enter_async_context(
                    model_factory(
                        context.get("provider_name"), context.get("model_name")
                    )
                )
            if selected is None:
                raise RuntimeError("Agent model is not configured")
            holder.append(selected.bind_tools(optional) if optional else selected)
        messages = list(state.get("messages", []))
        if answer_prompt_policy is not None:
            prompt = build_answer_system_prompt(
                sources=state.get("collected_sources", []),
                resolved_medicines=state.get("collected_medicines", []),
                intent=state.get("intent", "general"),
                qualifying_intents=list(state.get("qualifying_intents", ())),
                answer_prompt_policy=answer_prompt_policy,
            )
            messages = [SystemMessage(content=prompt)] + [
                m for m in messages if not isinstance(m, SystemMessage)
            ]
        response = await holder[0].ainvoke(messages, config=config)
        if not isinstance(response, AIMessage) or response.invalid_tool_calls:
            raise ValueError("Agent model returned an invalid response")
        finish = str(response.response_metadata.get("finish_reason", "")).upper()
        if finish in {"LENGTH", "MAX_TOKENS", "MAX_OUTPUT_TOKENS"}:
            raise ValueError("Agent model output was truncated")
        if response.tool_calls and (
            len(response.tool_calls) > 8
            or state.get("tool_rounds", 0) >= max_tool_rounds
        ):
            raise RuntimeError("Agent tool execution limit exceeded")
        return {"messages": [response]}

    async def tools_node(
        state: AgentGraphState, config: RunnableConfig
    ) -> dict[str, Any]:
        output = await tool_node.ainvoke(state, config=config)
        messages = output["messages"]
        results = [
            m.artifact
            for m in messages
            if isinstance(m, ToolMessage)
            and isinstance(m.artifact, ToolExecutionResult)
        ]
        if any(isinstance(m, ToolMessage) and m.status == "error" for m in messages):
            raise RuntimeError("Agent tool execution failed")
        return {
            **merge_results(state, results),
            "messages": messages,
            "tool_rounds": state.get("tool_rounds", 0) + 1,
        }

    def after_retrieval(state: AgentGraphState) -> str:
        return "clarification" if state.get("needs_clarification") else "agent"

    def after_agent(state: AgentGraphState) -> str:
        last = state.get("messages", [])[-1]
        return "tools" if isinstance(last, AIMessage) and last.tool_calls else END

    workflow.add_node("agent", agent_node)
    workflow.add_node("clarification", clarification_node)
    workflow.add_edge("clarification", END)
    if mandatory or mandatory_tool_provider is not None:
        workflow.add_node("mandatory", mandatory_node)
        workflow.set_entry_point("mandatory")
        workflow.add_conditional_edges(
            "mandatory",
            after_retrieval,
            {"clarification": "clarification", "agent": "agent"},
        )
    else:
        workflow.set_entry_point("agent")
    if optional:
        workflow.add_node("tools", tools_node)
        workflow.add_conditional_edges(
            "agent", after_agent, {"tools": "tools", END: END}
        )
        workflow.add_conditional_edges(
            "tools",
            after_retrieval,
            {"clarification": "clarification", "agent": "agent"},
        )
    else:
        workflow.add_edge("agent", END)
    return workflow.compile()
