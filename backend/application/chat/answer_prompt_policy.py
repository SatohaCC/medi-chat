"""回答に必要な表示スナップショットと指示。IOやSDK設定は含まない。"""

from collections.abc import Mapping
from dataclasses import dataclass


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
