"""Janomeの品詞処理に固有の設定。"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True, kw_only=True)
class JanomeMorphologySettings:
    ignored_noun_suffixes: frozenset[str]
