"""添付文書カタログを一度読み込み、型・重複・参照の整合性を検証する。"""

from __future__ import annotations

import json
import re
from pathlib import Path
from types import MappingProxyType
from typing import Any

from .schema_models import (
    SECTION_REFERENCE,
    AnswerGuidance,
    AnswerPromptDefinition,
    IntentDefinition,
    IntentKeyword,
    InteractionColumn,
    SectionDefinition,
    TextSearchDefinition,
    ValidatedDefinitionSource,
    XmlDefinition,
)


def _object(value: Any, path: str, required: str, optional: str = "") -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected an object")
    missing = set(required.split()) - value.keys()
    unknown = value.keys() - set((required + " " + optional).split())
    if missing or unknown:
        raise ValueError(
            f"{path}: missing fields {sorted(missing)}, unknown fields {sorted(unknown)}"
        )
    return value


def _mapping(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict) or not value:
        raise ValueError(f"{path}: expected a nonempty object")
    return value


def _text(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{path}: expected nonempty text")
    return value


def _strings(value: Any, path: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ValueError(f"{path}: expected a list")
    result = tuple(_text(item, path) for item in value)
    if len(result) != len(set(result)):
        raise ValueError(f"{path}: duplicate values")
    return result


def _positive_integer(value: Any, path: str) -> int:
    if type(value) is not int or value < 1:
        raise ValueError(f"{path}: expected a positive integer")
    return value


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def read_validated_source(path: Path) -> ValidatedDefinitionSource:
    """指定JSONを検証して読み込む。構成ミスは利用開始前に ValueError にする。"""
    data = _object(
        json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_unique_object),
        "catalog",
        "schema_version sections intents fallback_intent general_intent text_search interaction_columns xml answer_prompt",
    )
    if type(data["schema_version"]) is not int or data["schema_version"] != 1:
        raise ValueError("schema_version: unsupported catalog version")

    sections: dict[str, SectionDefinition] = {}
    tags: dict[str, SectionDefinition] = {}
    contexts: dict[tuple[str, str], SectionDefinition] = {}
    for code, raw in _mapping(data["sections"], "sections").items():
        if not re.fullmatch(r"[1-9][0-9]*(?:\.[1-9][0-9]*)*", code):
            raise ValueError(f"sections.{code}: invalid section code")
        entry = _object(
            raw,
            f"sections.{code}",
            "title",
            "display_title classification_title xml_tags xml_contexts",
        )
        title = _text(entry["title"], f"sections.{code}.title")
        section = SectionDefinition(
            code=code,
            title=title,
            display_title=_text(
                entry["display_title"], f"sections.{code}.display_title"
            )
            if "display_title" in entry
            else None,
            classification_title=_text(
                entry["classification_title"],
                f"sections.{code}.classification_title",
            )
            if "classification_title" in entry
            else None,
            parent_code=code.rpartition(".")[0] or None,
        )
        sections[code] = section
        for tag in _strings(entry.get("xml_tags", []), f"sections.{code}.xml_tags"):
            if tag in tags:
                raise ValueError(f"sections.{code}: duplicate XML tag {tag}")
            tags[tag] = section
        raw_contexts = entry.get("xml_contexts", [])
        if not isinstance(raw_contexts, list):
            raise ValueError(f"sections.{code}.xml_contexts: expected a list")
        for raw_context in raw_contexts:
            context = _object(
                raw_context, f"sections.{code}.xml_contexts", "parent_tag tag"
            )
            key = (
                _text(context["parent_tag"], "parent_tag"),
                _text(context["tag"], "tag"),
            )
            if key in contexts:
                raise ValueError(f"sections.{code}: duplicate XML context {key}")
            contexts[key] = section
    for section in sections.values():
        if section.parent_code and section.parent_code not in sections:
            raise ValueError(
                f"sections.{section.code}: unknown parent section {section.parent_code}"
            )
    for (parent_tag, tag), section in contexts.items():
        if parent_tag not in tags or tags[parent_tag].code != section.parent_code:
            raise ValueError(
                f"sections.{section.code}: invalid parent XML tag {parent_tag}"
            )
        if tag in tags:
            raise ValueError(
                f"sections.{section.code}: contextual XML tag is also global: {tag}"
            )

    def section_codes(value: Any, label: str) -> tuple[str, ...]:
        codes = _strings(value, label)
        unknown = set(codes) - sections.keys()
        if unknown:
            raise ValueError(f"{label}: unknown section codes {sorted(unknown)}")
        return codes

    def template(value: Any, label: str) -> str:
        text = _text(value, label)
        for code in SECTION_REFERENCE.findall(text):
            if code not in sections:
                raise ValueError(f"{label}: unknown section reference {code}")
        remaining = SECTION_REFERENCE.sub("", text)
        if "{" in remaining or "}" in remaining:
            raise ValueError(f"{label}: invalid section reference")
        return text

    intents = {}
    priorities: set[int] = set()
    keyword_texts: set[str] = set()
    for intent_id, raw in _mapping(data["intents"], "intents").items():
        if not re.fullmatch(r"[a-z][a-z0-9_]*", intent_id):
            raise ValueError(f"intents.{intent_id}: invalid intent ID")
        label = f"intents.{intent_id}"
        entry = _object(
            raw,
            label,
            "sections",
            "keywords keyword_priority classification answer_guidance",
        )
        codes = section_codes(entry["sections"], label + ".sections")
        keywords = []
        raw_keywords = entry.get("keywords", [])
        if not isinstance(raw_keywords, list):
            raise ValueError(f"{label}.keywords: expected a list")
        for raw_keyword in raw_keywords:
            keyword = _object(
                raw_keyword, label + ".keywords", "text exclude_from_text_search"
            )
            word = _text(keyword["text"], label + ".keywords.text")
            if word in keyword_texts:
                raise ValueError(f"{label}: duplicate keyword {word}")
            keyword_texts.add(word)
            exclude = keyword["exclude_from_text_search"]
            if type(exclude) is not bool:
                raise ValueError(
                    f"{label}.exclude_from_text_search: expected a boolean"
                )
            keywords.append(IntentKeyword(word, exclude))
        priority = None
        if keywords:
            priority = _positive_integer(
                entry.get("keyword_priority"), label + ".keyword_priority"
            )
            if priority in priorities:
                raise ValueError(f"{label}: duplicate keyword priority {priority}")
            if not codes:
                raise ValueError(f"{label}: keywords require search sections")
            priorities.add(priority)
        elif "keyword_priority" in entry:
            raise ValueError(f"{label}: keyword_priority requires keywords")
        description = None
        classification_sections: tuple[str, ...] = ()
        if "classification" in entry:
            classification = _object(
                entry["classification"],
                label + ".classification",
                "description",
                "sections",
            )
            description = _text(
                classification["description"], label + ".classification.description"
            )
            classification_sections = section_codes(
                classification.get("sections", list(codes[:1])),
                label + ".classification.sections",
            )
            if not set(classification_sections).issubset(codes) or bool(
                classification_sections
            ) != bool(codes):
                raise ValueError(
                    f"{label}: classification sections must refer to search sections"
                )
        guidance = None
        if "answer_guidance" in entry:
            raw_guidance = _object(
                entry["answer_guidance"],
                label + ".answer_guidance",
                "minimum_medicines template",
            )
            guidance = AnswerGuidance(
                _positive_integer(
                    raw_guidance["minimum_medicines"], label + ".minimum_medicines"
                ),
                template(raw_guidance["template"], label + ".answer_guidance.template"),
            )
        intents[intent_id] = IntentDefinition(
            intent_id,
            codes,
            tuple(keywords),
            priority,
            description,
            classification_sections,
            guidance,
        )

    fallback = _text(data["fallback_intent"], "fallback_intent")
    general = _text(data["general_intent"], "general_intent")
    for name in (fallback, general):
        if name not in intents or intents[name].section_codes:
            raise ValueError(
                f"{name}: fallback/general intent must exist without sections"
            )
    if (
        fallback == general
        or intents[general].classification_description is None
        or intents[fallback].classification_description is not None
    ):
        raise ValueError("fallback/general intent: invalid classification roles")
    if any(
        not intent.section_codes
        for key, intent in intents.items()
        if key not in (fallback, general)
    ):
        raise ValueError("intents: only fallback/general intents may omit sections")

    search = _object(
        data["text_search"],
        "text_search",
        "additional_stop_words ignored_noun_suffixes symptom_keywords_by_adjective scope_heading_texts",
    )
    additional_stop_words = _strings(
        search["additional_stop_words"], "additional_stop_words"
    )
    if set(additional_stop_words) & keyword_texts:
        raise ValueError(
            "additional_stop_words: define keyword exclusions on the keyword itself"
        )
    stop_words = frozenset(additional_stop_words) | frozenset(
        keyword.text
        for intent in intents.values()
        for keyword in intent.keywords
        if keyword.exclude_from_text_search
    )
    symptom_keywords = {
        word: _strings(values, f"symptom_keywords_by_adjective.{word}")
        for word, values in _mapping(
            search["symptom_keywords_by_adjective"], "symptom_keywords_by_adjective"
        ).items()
    }
    if any(not word.strip() or not words for word, words in symptom_keywords.items()):
        raise ValueError(
            "symptom_keywords_by_adjective: empty mappings are not allowed"
        )

    columns = []
    column_ids: set[str] = set()
    column_tags: set[str] = set()
    if (
        not isinstance(data["interaction_columns"], list)
        or not data["interaction_columns"]
    ):
        raise ValueError("interaction_columns: expected a nonempty list")
    for raw in data["interaction_columns"]:
        column = _object(raw, "interaction_columns", "id xml_tag title")
        column_id = _text(column["id"], "interaction_columns.id")
        xml_tag = _text(column["xml_tag"], "interaction_columns.xml_tag")
        if column_id in column_ids or xml_tag in column_tags:
            raise ValueError("interaction_columns: duplicate column ID or XML tag")
        column_ids.add(column_id)
        column_tags.add(xml_tag)
        columns.append(
            InteractionColumn(
                column_id, xml_tag, _text(column["title"], "interaction_columns.title")
            )
        )

    xml = _object(data["xml"], "xml", "header_tags reference_tags atomic_units")
    header_tags = frozenset(_strings(xml["header_tags"], "xml.header_tags"))
    if header_tags & tags.keys():
        raise ValueError("xml.header_tags: section tags cannot be document headers")
    atomic_units = {
        tag: _text(kind, f"xml.atomic_units.{tag}")
        for tag, kind in _mapping(xml["atomic_units"], "xml.atomic_units").items()
    }
    prompt = _object(
        data["answer_prompt"],
        "answer_prompt",
        "citation_examples multiple_intents_template",
    )
    examples = section_codes(
        prompt["citation_examples"], "answer_prompt.citation_examples"
    )
    if not examples:
        raise ValueError(
            "answer_prompt.citation_examples: expected at least one section"
        )

    return ValidatedDefinitionSource(
        sections=MappingProxyType(sections),
        sections_by_xml_tag=MappingProxyType(tags),
        sections_by_xml_context=MappingProxyType(contexts),
        intents=MappingProxyType(intents),
        fallback_intent=fallback,
        general_intent=general,
        text_search=TextSearchDefinition(
            stop_words,
            frozenset(
                _strings(search["ignored_noun_suffixes"], "ignored_noun_suffixes")
            ),
            MappingProxyType(symptom_keywords),
            frozenset(_strings(search["scope_heading_texts"], "scope_heading_texts")),
        ),
        interaction_columns=tuple(columns),
        xml=XmlDefinition(
            header_tags,
            frozenset(_strings(xml["reference_tags"], "xml.reference_tags")),
            MappingProxyType(atomic_units),
        ),
        answer_prompt=AnswerPromptDefinition(
            examples,
            template(
                prompt["multiple_intents_template"],
                "answer_prompt.multiple_intents_template",
            ),
        ),
    )
