"""各層が所有する型付き定義の組立。JSON読込・旧形式変換を持たない。"""

from dataclasses import dataclass
from functools import lru_cache

from backend.application.chat.queries.models import AnswerPromptPolicy
from backend.application.chat.queries.policies.standard import (
    build_answer_prompt_policy,
)
from backend.application.retrieval.queries.models import IntentPolicy, TextSearchPolicy
from backend.application.retrieval.queries.policies.standard import (
    DEFAULT_INTENT_POLICY,
    DEFAULT_RETRIEVAL_POLICY,
    EvidenceRetrievalPolicy,
    build_text_search_policy,
)
from backend.domain.attachment.value_objects import (
    STANDARD_INTERACTION_COLUMNS,
    STANDARD_SECTION_TAXONOMY,
    InteractionColumnDefinition,
    SectionTaxonomy,
)
from backend.infrastructure.package_insert_definitions.definition_settings import (
    JanomeMorphologySettings,
    JevClassificationSettings,
    PmdaXmlSettings,
)
from backend.infrastructure.package_insert_definitions.jev_settings import (
    build_jev_settings,
)
from backend.infrastructure.package_insert_definitions.xml_settings import (
    DEFAULT_MORPHOLOGY_SETTINGS,
    build_xml_settings,
)


@dataclass(frozen=True, slots=True, kw_only=True)
class PackageInsertDefinitions:
    """組立地点専用の束。利用先へは用途別の型だけを注入する。"""

    taxonomy: SectionTaxonomy
    interaction_columns: tuple[InteractionColumnDefinition, ...]
    intent_policy: IntentPolicy
    retrieval_policy: EvidenceRetrievalPolicy
    text_search_policy: TextSearchPolicy
    answer_prompt_policy: AnswerPromptPolicy
    xml_settings: PmdaXmlSettings
    jev_settings: JevClassificationSettings
    morphology_settings: JanomeMorphologySettings


def build_package_insert_definitions(
    *,
    taxonomy: SectionTaxonomy = STANDARD_SECTION_TAXONOMY,
    interaction_columns: tuple[
        InteractionColumnDefinition, ...
    ] = STANDARD_INTERACTION_COLUMNS,
    intent_policy: IntentPolicy = DEFAULT_INTENT_POLICY,
    retrieval_policy: EvidenceRetrievalPolicy = DEFAULT_RETRIEVAL_POLICY,
    text_search_policy: TextSearchPolicy | None = None,
    answer_prompt_policy: AnswerPromptPolicy | None = None,
    xml_settings: PmdaXmlSettings | None = None,
    jev_settings: JevClassificationSettings | None = None,
    morphology_settings: JanomeMorphologySettings = DEFAULT_MORPHOLOGY_SETTINGS,
) -> PackageInsertDefinitions:
    codes = {s.code.value for s in taxonomy.sections}
    referenced = {c.value for i in intent_policy.intents for c in i.section_codes}
    referenced.update(c.value for c in retrieval_policy.always_retrieved_sections)
    if referenced - codes:
        raise ValueError(f"unknown policy sections: {sorted(referenced - codes)}")
    return PackageInsertDefinitions(
        taxonomy=taxonomy,
        interaction_columns=interaction_columns,
        intent_policy=intent_policy,
        retrieval_policy=retrieval_policy,
        text_search_policy=text_search_policy
        if text_search_policy is not None
        else build_text_search_policy(intent_policy),
        answer_prompt_policy=answer_prompt_policy
        if answer_prompt_policy is not None
        else build_answer_prompt_policy(taxonomy, interaction_columns, intent_policy),
        xml_settings=xml_settings
        if xml_settings is not None
        else build_xml_settings(taxonomy, interaction_columns),
        jev_settings=jev_settings
        if jev_settings is not None
        else build_jev_settings(taxonomy),
        morphology_settings=morphology_settings,
    )


@lru_cache(maxsize=1)
def get_package_insert_definitions() -> PackageInsertDefinitions:
    return build_package_insert_definitions()
