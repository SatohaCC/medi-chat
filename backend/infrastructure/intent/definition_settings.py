"""TypeSafe分類入力の設定。可変SDK入力は呼出しごとに独立コピーする。"""

from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True, slots=True, kw_only=True)
class JevClassificationSettings:
    criteria: Mapping[str, str]

    def build_classification_criteria(self) -> dict[str, str]:
        return dict(self.criteria)
