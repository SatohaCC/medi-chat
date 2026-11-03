"""LangGraph エージェントの内部 State とデータ構造。"""

from __future__ import annotations

from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

from backend.application.medicine.queries.models import ResolvedMedicine
from backend.application.retrieval.queries.models import Evidence
from backend.domain.foundation.json_types import JsonValue


class AgentGraphState(TypedDict, total=False):
    """LangGraph グラフ内で引き回される状態"""

    messages: Annotated[list[BaseMessage], add_messages]
    collected_sources: list[Evidence]
    collected_medicines: list[ResolvedMedicine]
    collected_notices: list[str]
    needs_clarification: bool
    clarification_message: str
    intent: str
    jev_response: dict[str, JsonValue] | None
    qualifying_intents: tuple[str, ...]
    tool_rounds: int
