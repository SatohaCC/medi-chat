"""添付文書定義カタログから投影される各技術アダプター向け設定モデル。"""

from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True, slots=True, kw_only=True)
class JevClassificationSettings:
    """TypeSafe分類入力の設定。可変SDK入力は呼出しごとに独立コピーする。"""

    criteria: Mapping[str, str]

    def build_classification_criteria(self) -> dict[str, str]:
        return dict(self.criteria)


@dataclass(frozen=True, slots=True, kw_only=True)
class JanomeMorphologySettings:
    """Janomeの品詞処理に固有の設定。"""

    ignored_noun_suffixes: frozenset[str]


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
    """PMDA XMLの技術設定と、Applicationが投影した名称スナップショット。"""

    sections_by_xml_tag: Mapping[str, XmlSectionBinding]
    sections_by_xml_context: Mapping[tuple[str, str], XmlSectionBinding]
    interaction_columns: tuple[XmlColumnBinding, ...]
    header_tags: frozenset[str]
    reference_tags: frozenset[str]
    atomic_units: Mapping[str, str]
