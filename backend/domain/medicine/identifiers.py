"""医薬品コンテキストが所有する公開ID。"""

from dataclasses import dataclass

from ..foundation.primitives.identifiers import EntityStringId


@dataclass(frozen=True, slots=True)
class YjCode(EntityStringId):
    """医薬品製品を識別するYJコード。他コンテキストはこのIDで参照する。"""
