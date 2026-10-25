"""Domainの項目の意味とApplicationの分類方針をJev選択肢へ変換する。"""

from collections.abc import Mapping
from types import MappingProxyType

from backend.application.retrieval.queries.policies.standard import (
    DEFAULT_CLASSIFICATION_RULES,
    DEFAULT_CLASSIFICATION_TITLES,
    ClassificationRule,
)
from backend.domain.attachment.value_objects import SectionTaxonomy
from backend.infrastructure.package_insert_definitions.definition_settings import (
    JevClassificationSettings,
)


def build_jev_settings(
    taxonomy: SectionTaxonomy,
    rules: tuple[ClassificationRule, ...] = DEFAULT_CLASSIFICATION_RULES,
    *,
    classification_titles: Mapping[str, str] = DEFAULT_CLASSIFICATION_TITLES,
) -> JevClassificationSettings:
    sections = {s.code.value: s for s in taxonomy.sections}
    criteria = {}
    for rule in rules:
        if not rule.section_codes:
            if rule.fallback_description is None:
                raise ValueError("classification without sections requires description")
            criteria[rule.intent.value] = rule.fallback_description
            continue
        codes = tuple(code.value for code in rule.section_codes)
        for code in codes:
            if code not in sections:
                raise ValueError(f"unknown classification section {code}")
        section = sections[codes[0]]
        number = "/".join(codes)
        suffix = "" if "." in number else "."
        title = classification_titles.get(codes[0], section.title.value)
        # 親項目の選択肢にも子項目の意味を含め、広い名称だけで判定させない。
        relevant = tuple(
            item
            for item in taxonomy.sections
            if any(
                item.code.value == code or item.code.value.startswith(f"{code}.")
                for code in codes
            )
        )
        descriptions = [f"{number}{suffix} {title}：{section.scope.value}に関する質問"]
        descriptions.extend(
            f"{item.code.value} {item.title.value}：{item.scope.value}"
            for item in relevant
            if item.code.value != codes[0]
        )
        criteria[rule.intent.value] = "\n".join(descriptions)
    if len(criteria) != len(rules):
        raise ValueError("duplicate classification intent")
    return JevClassificationSettings(criteria=MappingProxyType(criteria))
