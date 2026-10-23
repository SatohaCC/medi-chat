from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Literal

from backend.application.medicine.queries.models import ResolvedMedicine
from backend.application.retrieval.queries.models import Evidence
from backend.domain.foundation.json_types import JsonValue


@dataclass
class ChatMessage:
    """チャット対話メッセージ。"""

    role: Literal["user", "assistant", "system"]
    content: str


@dataclass
class ChatResponse:
    """チャット応答と根拠。"""

    answer: str
    intent: str
    retrieval_strategy: str
    resolved_medicines: list[ResolvedMedicine] = field(default_factory=list)
    sources: list[Evidence] = field(default_factory=list)
    needs_clarification: bool = False
    notices: list[str] = field(default_factory=list)
    jev_response: dict[str, JsonValue] | None = None
    qualifying_intents: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True, kw_only=True)
class AnswerGuidance:
    minimum_medicines: int
    text: str


@dataclass(frozen=True, slots=True, kw_only=True)
class AnswerColumn:
    id: str
    title: str


@dataclass(frozen=True, slots=True, kw_only=True)
class AnswerPromptPolicy:
    intent_labels: Mapping[str, str]
    interaction_columns: tuple[AnswerColumn, ...]
    guidance: Mapping[str, AnswerGuidance]
    citation_examples: str
    multiple_intents_template: str

    def intent_display_name(self, intent_id: str) -> str:
        return self.intent_labels.get(intent_id, intent_id)

    def citation_examples_text(self) -> str:
        return self.citation_examples

    def answer_guidance_for_intent(self, intent_id: str, medicine_count: int) -> str:
        guidance = self.guidance.get(intent_id)
        return (
            guidance.text
            if guidance is not None and medicine_count >= guidance.minimum_medicines
            else ""
        )
