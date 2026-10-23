"""型付き定義の差し替えを通して各利用先への投影を検証するfixture。"""

from dataclasses import replace

from backend.application.chat.queries.policies.standard import (
    build_answer_prompt_policy,
)
from backend.application.indexing.values import SearchSectionCode
from backend.application.retrieval.queries.models import (
    IntentKeyword,
    SearchIntentDefinition,
)
from backend.application.retrieval.queries.policies.standard import (
    DEFAULT_CLASSIFICATION_RULES,
    DEFAULT_CLASSIFICATION_TITLES,
    DEFAULT_DISPLAY_TITLES,
    DEFAULT_INTENT_POLICY,
    ClassificationRule,
)
from backend.application.retrieval.values import (
    IntentKeywordText,
    IntentName,
    KeywordPriority,
)
from backend.domain.attachment.primitives import (
    DefinitionTitle,
    NumberedSectionCode,
    SectionScope,
)
from backend.domain.attachment.value_objects import (
    STANDARD_INTERACTION_COLUMNS,
    STANDARD_SECTION_TAXONOMY,
    SectionDefinition,
    SectionTaxonomy,
)
from backend.infrastructure.package_insert_definitions.assembly import (
    build_package_insert_definitions,
)
from backend.infrastructure.package_insert_definitions.jev_settings import (
    build_jev_settings,
)
from backend.infrastructure.package_insert_definitions.xml_settings import (
    DEFAULT_XML_TAGS,
    XmlTagMapping,
    build_xml_settings,
)


def renamed_definitions():
    titles = {"1": "  全角Ａ警告  ", "10": "  全角Ｂ相互作用  "}
    taxonomy = SectionTaxonomy(
        sections=tuple(
            replace(s, title=DefinitionTitle(titles[s.code.value]))
            if s.code.value in titles
            else s
            for s in STANDARD_SECTION_TAXONOMY.sections
        )
    )
    display = {**DEFAULT_DISPLAY_TITLES, "10": "表示別名"}
    classification = {**DEFAULT_CLASSIFICATION_TITLES, "10": "分類別名"}
    return build_package_insert_definitions(
        taxonomy=taxonomy,
        answer_prompt_policy=build_answer_prompt_policy(
            taxonomy,
            STANDARD_INTERACTION_COLUMNS,
            DEFAULT_INTENT_POLICY,
            display_titles=display,
        ),
        jev_settings=build_jev_settings(taxonomy, classification_titles=classification),
    )


def supplementary_definitions():
    taxonomy = SectionTaxonomy(
        sections=STANDARD_SECTION_TAXONOMY.sections
        + (
            SectionDefinition(
                code=NumberedSectionCode("27"),
                title=DefinitionTitle("追加項目の正式名称"),
                scope=SectionScope("追加項目の内容"),
            ),
        )
    )
    columns = tuple(
        replace(c, title=DefinitionTitle("注入薬剤列"))
        if c.id.value == "drug_name"
        else c
        for c in STANDARD_INTERACTION_COLUMNS
    )
    intent = SearchIntentDefinition(
        id=IntentName("supplementary"),
        section_codes=(SearchSectionCode("27"),),
        keywords=(
            IntentKeyword(
                text=IntentKeywordText("追補"), exclude_from_text_search=True
            ),
        ),
        keyword_priority=KeywordPriority(27),
    )
    policy = replace(
        DEFAULT_INTENT_POLICY, intents=DEFAULT_INTENT_POLICY.intents + (intent,)
    )
    return build_package_insert_definitions(
        taxonomy=taxonomy,
        interaction_columns=columns,
        intent_policy=policy,
        answer_prompt_policy=build_answer_prompt_policy(
            taxonomy, columns, policy, citation_sections=("2", "6", "10.1", "16", "27")
        ),
        xml_settings=build_xml_settings(
            taxonomy,
            columns,
            tags=DEFAULT_XML_TAGS
            + (XmlTagMapping(tag="SupplementarySection", section_code="27"),),
        ),
        jev_settings=build_jev_settings(
            taxonomy,
            DEFAULT_CLASSIFICATION_RULES
            + (
                ClassificationRule(
                    intent=IntentName("supplementary"),
                    section_codes=(SearchSectionCode("27"),),
                ),
            ),
        ),
    )
