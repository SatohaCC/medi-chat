"""共通カタログの不変モデルと、利用先に合わせた定義の組み立て。"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass

SECTION_REFERENCE = re.compile(r"\{section:([0-9]+(?:\.[0-9]+)*)\}")


@dataclass(frozen=True)
class SectionDefinition:
    code: str
    title: str
    display_title: str
    classification_title: str
    parent_code: str | None


@dataclass(frozen=True)
class IntentKeyword:
    text: str
    exclude_from_text_search: bool


@dataclass(frozen=True)
class AnswerGuidance:
    minimum_medicines: int
    template: str


@dataclass(frozen=True)
class IntentDefinition:
    id: str
    section_codes: tuple[str, ...]
    keywords: tuple[IntentKeyword, ...]
    keyword_priority: int | None
    classification_description: str | None
    classification_sections: tuple[str, ...]
    answer_guidance: AnswerGuidance | None


@dataclass(frozen=True)
class InteractionColumn:
    id: str
    xml_tag: str
    title: str


@dataclass(frozen=True)
class TextSearchDefinition:
    stop_words: frozenset[str]
    ignored_noun_suffixes: frozenset[str]
    symptom_keywords_by_adjective: Mapping[str, tuple[str, ...]]
    scope_heading_texts: frozenset[str]


@dataclass(frozen=True)
class XmlDefinition:
    header_tags: frozenset[str]
    reference_tags: frozenset[str]
    atomic_units: Mapping[str, str]


@dataclass(frozen=True)
class AnswerPromptDefinition:
    citation_examples: tuple[str, ...]
    multiple_intents_template: str


@dataclass(frozen=True)
class PackageInsertCatalog:
    sections: Mapping[str, SectionDefinition]
    sections_by_xml_tag: Mapping[str, SectionDefinition]
    sections_by_xml_context: Mapping[tuple[str, str], SectionDefinition]
    intents: Mapping[str, IntentDefinition]
    keyword_intents: tuple[IntentDefinition, ...]
    fallback_intent: str
    general_intent: str
    text_search: TextSearchDefinition
    interaction_columns: tuple[InteractionColumn, ...]
    xml: XmlDefinition
    answer_prompt: AnswerPromptDefinition

    def section_codes_for_intent(self, intent_id: str) -> tuple[str, ...]:
        intent = self.intents.get(intent_id)
        return intent.section_codes if intent else ()

    def intent_display_name(self, intent_id: str) -> str:
        codes = self.section_codes_for_intent(intent_id)
        return self.sections[codes[0]].display_title if codes else intent_id

    def build_classification_criteria(self) -> dict[str, str]:
        """SDKへ渡す独立した辞書を生成する。共有カタログ自体は変更しない。"""
        criteria = {}
        for intent in self.intents.values():
            if intent.classification_description is None:
                continue
            if not intent.classification_sections:
                criteria[intent.id] = intent.classification_description
                continue
            codes = intent.classification_sections
            section = self.sections[codes[0]]
            number = "/".join(codes)
            suffix = "" if "." in number else "."
            criteria[intent.id] = (
                f"{number}{suffix} {section.classification_title}："
                f"{intent.classification_description}"
            )
        return criteria

    def render_section_titles(self, template: str) -> str:
        """検証済みの {section:番号} を正式な項目名に置き換える。"""
        return SECTION_REFERENCE.sub(
            lambda match: self.sections[match.group(1)].title, template
        )

    def citation_examples_text(self) -> str:
        return "、".join(
            f"{code}{'.' if '.' not in code else ''} {self.sections[code].title}"
            for code in self.answer_prompt.citation_examples
        )

    def answer_guidance_for_intent(self, intent_id: str, medicine_count: int) -> str:
        intent = self.intents.get(intent_id)
        guidance = intent.answer_guidance if intent else None
        if guidance is None or medicine_count < guidance.minimum_medicines:
            return ""
        return self.render_section_titles(guidance.template)
