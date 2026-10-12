"""原本項目体系から利用側の文字列スナップショットへの明示投影。"""

import re
from collections.abc import Mapping
from types import MappingProxyType

from ...domain.attachment.value_objects import SectionTaxonomy

SECTION_REFERENCE = re.compile(r"\{section:([0-9]+(?:\.[0-9]+)*)\}")


def project_section_titles(taxonomy: SectionTaxonomy) -> Mapping[str, str]:
    return MappingProxyType(
        {section.code.value: section.title.value for section in taxonomy.sections}
    )


def render_section_titles(template: str, titles: Mapping[str, str]) -> str:
    return SECTION_REFERENCE.sub(lambda match: titles[match.group(1)], template)
