"""検索コンテキストの公開ID。"""

from dataclasses import dataclass

from ..foundation.primitives.identifiers import EntityStringId


@dataclass(frozen=True, slots=True)
class SearchUnitId(EntityStringId):
    """原文から派生する検索・根拠単位のID。文書自体のIDとは区別する。"""


@dataclass(frozen=True, slots=True)
class SearchGenerationId(EntityStringId):
    """根拠と掲載製品を一貫して読む公開世代のID。"""
