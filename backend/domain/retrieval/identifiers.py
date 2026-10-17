"""検索コンテキストの公開ID。"""

from dataclasses import dataclass

from ..foundation.primitives.identifiers import EntityStringId


@dataclass(frozen=True, slots=True)
class SearchUnitId(EntityStringId):
    """原文から派生する検索・根拠単位のID。文書自体のIDとは区別する。"""
