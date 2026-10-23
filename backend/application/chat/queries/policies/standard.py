"""添付文書の項目体系から回答用表示と指示を組み立てる。"""

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from backend.application.chat.queries.models import (
    AnswerColumn,
    AnswerGuidance,
    AnswerPromptPolicy,
)
from backend.application.retrieval.queries.models import IntentPolicy
from backend.application.retrieval.queries.policies.section_titles import (
    project_section_titles,
    render_section_titles,
)
from backend.application.retrieval.queries.policies.standard import (
    DEFAULT_DISPLAY_TITLES,
)
from backend.domain.attachment.value_objects import (
    InteractionColumnDefinition,
    SectionTaxonomy,
)


@dataclass(frozen=True, slots=True, kw_only=True)
class AnswerGuidanceTemplate:
    intent_id: str
    minimum_medicines: int
    template: str


DEFAULT_GUIDANCE = (
    AnswerGuidanceTemplate(
        intent_id="interaction",
        minimum_medicines=2,
        template="【複数薬剤の{section:10}に関する指示】\n   - 指定された薬剤同士を直接指定する{section:10.1}・{section:10.2}の記載があるかを確認し、明確に回答してください。\n   - 直接の{section:10.1}・{section:10.2}の記載がない場合でも、「互いを直接指定する記載がないことのみをもって併用可能（{section:10}が一切ない）とは判断できない」旨を明記した上で、提供された各薬剤の{section:10}（代謝酵素、排泄経路、{section:10.2}薬の傾向など）の要点を整理して説明してください。\n",
    ),
)

DEFAULT_CITATION_SECTIONS = ("2", "6", "10.1", "16")
DEFAULT_MULTIPLE_INTENTS_TEMPLATE = "【複合質問の回答指示】本質問は複数の項目（例: {section:16}と{section:6}など）にまたがる複合的な質問です。提供されたすべての関連セクションの記載（{section:16}だけでなく、{section:6}や{section:7}など該当する全項目）を必ず漏れなく確認し、それぞれの項目に基づいて総合的に照合して回答してください。\n"


def build_answer_prompt_policy(
    taxonomy: SectionTaxonomy,
    columns: tuple[InteractionColumnDefinition, ...],
    intent_policy: IntentPolicy,
    *,
    display_titles: Mapping[str, str] = DEFAULT_DISPLAY_TITLES,
    guidance: tuple[AnswerGuidanceTemplate, ...] = DEFAULT_GUIDANCE,
    citation_sections: tuple[str, ...] = DEFAULT_CITATION_SECTIONS,
    multiple_intents_template: str = DEFAULT_MULTIPLE_INTENTS_TEMPLATE,
) -> AnswerPromptPolicy:
    titles = project_section_titles(taxonomy)
    labels = {
        intent.id.value: (
            display_titles.get(
                intent.section_codes[0].value, titles[intent.section_codes[0].value]
            )
            if intent.section_codes
            else intent.id.value
        )
        for intent in intent_policy.intents
    }
    return AnswerPromptPolicy(
        intent_labels=MappingProxyType(labels),
        interaction_columns=tuple(
            AnswerColumn(id=c.id.value, title=c.title.value) for c in columns
        ),
        guidance=MappingProxyType(
            {
                g.intent_id: AnswerGuidance(
                    minimum_medicines=g.minimum_medicines,
                    text=render_section_titles(g.template, titles),
                )
                for g in guidance
            }
        ),
        citation_examples="、".join(
            f"{code}{'.' if '.' not in code else ''} {titles[code]}"
            for code in citation_sections
        ),
        multiple_intents_template=render_section_titles(
            multiple_intents_template, titles
        ),
    )
