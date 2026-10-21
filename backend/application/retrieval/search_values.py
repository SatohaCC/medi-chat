"""根拠取得の型とポリシー。"""

from __future__ import annotations

from dataclasses import dataclass

from backend.application.indexing.search_values import SearchUnitText
from backend.domain.foundation.exceptions import DomainValidationError
from backend.domain.foundation.primitives.base import DomainPrimitive
from backend.domain.foundation.primitives.enums import ValidatedStrEnum
from backend.domain.foundation.primitives.primitives import (
    BaseFiniteFloat,
    BaseString,
)


class DetectionSource(ValidatedStrEnum):
    """検索条件を作った検出元。"""

    LOGIC = "logic"
    JEV = "jev"
    KEYWORD = "keyword"


@dataclass(frozen=True, slots=True)
class _OriginalTerm(DomainPrimitive[str]):
    """非空の原表記を変更せず保持する。"""

    def validate(self) -> None:
        if not isinstance(self.value, str) or not self.value.strip():
            raise DomainValidationError("original term must be nonempty text")


@dataclass(frozen=True, slots=True)
class IntentName(BaseString):
    """判定された質問意図の名前。"""


@dataclass(frozen=True, slots=True)
class IntentKeywordText(DomainPrimitive[str]):
    """意図判定に使う固定キーワード文字列。空文字・空白のみは拒否する。"""

    def validate(self) -> None:
        if not isinstance(self.value, str) or not self.value.strip():
            raise DomainValidationError("intent keyword must be nonempty")


@dataclass(frozen=True, slots=True)
class Probability(BaseFiniteFloat):
    """0以上1以下の有限な確率。"""

    def validate(self) -> None:
        if not 0.0 <= self.value <= 1.0:
            raise DomainValidationError("Probability must be between 0 and 1")


@dataclass(frozen=True, slots=True)
class SearchKeyword(BaseString):
    """全文検索に使うキーワード。"""


@dataclass(frozen=True, slots=True)
class EvidenceBrandName(_OriginalTerm):
    """原表記を保持する根拠値。"""


@dataclass(frozen=True, slots=True)
class EvidenceGenericName(_OriginalTerm):
    """原表記を保持する根拠値。"""


@dataclass(frozen=True, slots=True)
class EvidenceSourceUrl(_OriginalTerm):
    """原表記を保持する根拠値。"""


@dataclass(frozen=True, slots=True)
class KeywordPriority(DomainPrimitive[int]):
    """固定検索意図の正の優先順位。"""

    def validate(self) -> None:
        if type(self.value) is not int or self.value < 1:
            raise DomainValidationError("priority must be a positive integer")


@dataclass(frozen=True, slots=True)
class EvidenceProductName(_OriginalTerm):
    """補完・連結を含む根拠の表示製品名。"""


@dataclass(frozen=True, slots=True)
class EvidenceExcerpt(SearchUnitText):
    """空本文も含め保持する根拠本文。"""


@dataclass(frozen=True, slots=True)
class SearchPolicyTerm(_OriginalTerm):
    """検索ポリシーの非空語彙。"""
