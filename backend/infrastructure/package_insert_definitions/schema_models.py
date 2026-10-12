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
    display_title: str | None
    classification_title: str | None
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
class ValidatedDefinitionSource:
    sections: Mapping[str, SectionDefinition]
    sections_by_xml_tag: Mapping[str, SectionDefinition]
    sections_by_xml_context: Mapping[tuple[str, str], SectionDefinition]
    intents: Mapping[str, IntentDefinition]
    fallback_intent: str
    general_intent: str
    text_search: TextSearchDefinition
    interaction_columns: tuple[InteractionColumn, ...]
    xml: XmlDefinition
    answer_prompt: AnswerPromptDefinition
