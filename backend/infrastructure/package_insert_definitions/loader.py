"""単一JSONを検証し、compositionで展開する用途別定義を組み立てる。"""

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from types import MappingProxyType

from ...application.chat.answer_prompt_policy import (
    AnswerColumn,
    AnswerGuidance,
    AnswerPromptPolicy,
)
from ...application.retrieval.definition_projection import (
    project_section_titles,
    render_section_titles,
)
from ...domain.attachment.primitives import (
    DefinitionTitle,
    InteractionColumnId,
    NumberedSectionCode,
)
from ...domain.attachment.value_objects import (
    InteractionColumnDefinition,
    SectionDefinition,
    SectionTaxonomy,
)
from ...domain.retrieval.primitives import (
    IntentKeywordText,
    IntentName,
    SearchSectionCode,
)
from ...domain.retrieval.value_objects import (
    IntentKeyword,
    IntentPolicy,
    SearchIntentDefinition,
    TextSearchPolicy,
)
from .definition_settings import (
    JanomeMorphologySettings,
    JevClassificationSettings,
    PmdaXmlSettings,
    XmlColumnBinding,
    XmlSectionBinding,
)
from .schema_validation import read_validated_source

DEFINITIONS_PATH = Path(__file__).with_name("package_insert_catalog.json")


@dataclass(frozen=True, slots=True, kw_only=True)
class PackageInsertDefinitions:
    """Infrastructure組立地点専用。サービスへこの束を渡さない。"""

    taxonomy: SectionTaxonomy
    interaction_columns: tuple[InteractionColumnDefinition, ...]
    intent_policy: IntentPolicy
    text_search_policy: TextSearchPolicy
    answer_prompt_policy: AnswerPromptPolicy
    xml_settings: PmdaXmlSettings
    jev_settings: JevClassificationSettings
    morphology_settings: JanomeMorphologySettings


def load_package_insert_definitions(path: Path) -> PackageInsertDefinitions:
    source = read_validated_source(path)
    taxonomy = SectionTaxonomy(
        sections=tuple(
            SectionDefinition(
                code=NumberedSectionCode(section.code),
                title=DefinitionTitle(section.title),
            )
            for section in source.sections.values()
        )
    )
    titles = project_section_titles(taxonomy)
    columns = tuple(
        InteractionColumnDefinition(
            id=InteractionColumnId(column.id), title=DefinitionTitle(column.title)
        )
        for column in source.interaction_columns
    )
    intent_policy = IntentPolicy(
        intents=tuple(
            SearchIntentDefinition(
                id=IntentName(intent.id),
                section_codes=tuple(
                    SearchSectionCode(code) for code in intent.section_codes
                ),
                keywords=tuple(
                    IntentKeyword(
                        text=IntentKeywordText(keyword.text),
                        exclude_from_text_search=keyword.exclude_from_text_search,
                    )
                    for keyword in intent.keywords
                ),
                keyword_priority=intent.keyword_priority,
            )
            for intent in source.intents.values()
        ),
        fallback_intent=IntentName(source.fallback_intent),
        general_intent=IntentName(source.general_intent),
    )
    labels = {
        intent.id: (
            source.sections[intent.section_codes[0]].display_title
            or titles[intent.section_codes[0]]
        )
        if intent.section_codes
        else intent.id
        for intent in source.intents.values()
    }
    guidance = {
        intent.id: AnswerGuidance(
            minimum_medicines=intent.answer_guidance.minimum_medicines,
            text=render_section_titles(intent.answer_guidance.template, titles),
        )
        for intent in source.intents.values()
        if intent.answer_guidance is not None
    }
    criteria = {}
    for intent in source.intents.values():
        if intent.classification_description is None:
            continue
        if not intent.classification_sections:
            criteria[intent.id] = intent.classification_description
            continue
        codes = intent.classification_sections
        number = "/".join(codes)
        suffix = "" if "." in number else "."
        title = source.sections[codes[0]].classification_title or titles[codes[0]]
        criteria[intent.id] = (
            f"{number}{suffix} {title}：{intent.classification_description}"
        )
    xml_sections = {
        code: XmlSectionBinding(code=code, title=title)
        for code, title in titles.items()
    }
    return PackageInsertDefinitions(
        taxonomy=taxonomy,
        interaction_columns=columns,
        intent_policy=intent_policy,
        text_search_policy=TextSearchPolicy(
            stop_words=source.text_search.stop_words,
            symptom_keywords_by_adjective=source.text_search.symptom_keywords_by_adjective,
            scope_heading_texts=source.text_search.scope_heading_texts,
        ),
        answer_prompt_policy=AnswerPromptPolicy(
            intent_labels=MappingProxyType(labels),
            interaction_columns=tuple(
                AnswerColumn(id=column.id.value, title=column.title.value)
                for column in columns
            ),
            guidance=MappingProxyType(guidance),
            citation_examples="、".join(
                f"{code}{'.' if '.' not in code else ''} {titles[code]}"
                for code in source.answer_prompt.citation_examples
            ),
            multiple_intents_template=render_section_titles(
                source.answer_prompt.multiple_intents_template, titles
            ),
        ),
        xml_settings=PmdaXmlSettings(
            sections_by_xml_tag=MappingProxyType(
                {
                    tag: xml_sections[section.code]
                    for tag, section in source.sections_by_xml_tag.items()
                }
            ),
            sections_by_xml_context=MappingProxyType(
                {
                    key: xml_sections[section.code]
                    for key, section in source.sections_by_xml_context.items()
                }
            ),
            interaction_columns=tuple(
                XmlColumnBinding(
                    id=column.id.value,
                    title=column.title.value,
                    xml_tag=binding.xml_tag,
                )
                for column, binding in zip(
                    columns, source.interaction_columns, strict=True
                )
            ),
            header_tags=source.xml.header_tags,
            reference_tags=source.xml.reference_tags,
            atomic_units=source.xml.atomic_units,
        ),
        jev_settings=JevClassificationSettings(criteria=MappingProxyType(criteria)),
        morphology_settings=JanomeMorphologySettings(
            ignored_noun_suffixes=source.text_search.ignored_noun_suffixes
        ),
    )


@lru_cache(maxsize=1)
def get_package_insert_definitions() -> PackageInsertDefinitions:
    return load_package_insert_definitions(DEFINITIONS_PATH)
