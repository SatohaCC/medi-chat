"""PMDA XMLの技術設定と、Applicationが投影した名称スナップショット。"""

from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True, slots=True, kw_only=True)
class XmlSectionBinding:
    code: str
    title: str


@dataclass(frozen=True, slots=True, kw_only=True)
class XmlColumnBinding:
    id: str
    xml_tag: str
    title: str


@dataclass(frozen=True, slots=True, kw_only=True)
class PmdaXmlSettings:
    sections_by_xml_tag: Mapping[str, XmlSectionBinding]
    sections_by_xml_context: Mapping[tuple[str, str], XmlSectionBinding]
    interaction_columns: tuple[XmlColumnBinding, ...]
    header_tags: frozenset[str]
    reference_tags: frozenset[str]
    atomic_units: Mapping[str, str]
