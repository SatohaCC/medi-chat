"""検索コンテキストのPrimitive。"""

import re
from dataclasses import dataclass

from ..foundation.exceptions import DomainValidationError
from ..foundation.primitives.base import DomainPrimitive
from ..foundation.primitives.enums import ValidatedStrEnum
from ..foundation.primitives.primitives import BaseFiniteFloat, BaseHttpUrl, BaseString


class DetectionSource(ValidatedStrEnum):
    """検索条件を作った検出元。"""

    LOGIC = "logic"
    JEV = "jev"
    KEYWORD = "keyword"


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
class SearchSectionCode(BaseString):
    """検索条件の項目コード。番号形式以外の既存入力も受け付ける。"""


@dataclass(frozen=True, slots=True)
class EvidenceContextLabel(BaseString):
    """根拠に付ける文脈ラベル。表記を保持し、前後の余白だけを除去する。"""

    def _normalize(self, value: object) -> str:
        if not isinstance(value, str):
            raise DomainValidationError("値は文字列である必要があります。")
        return value.strip()


@dataclass(frozen=True, slots=True)
class EvidenceBrandName(BaseString):
    """正規化せず原文を保持する根拠用の販売名。"""

    def _normalize(self, value: object) -> str:
        if not isinstance(value, str):
            raise DomainValidationError("値は文字列である必要があります。")
        return value


@dataclass(frozen=True, slots=True)
class EvidenceGenericName(BaseString):
    """正規化せず原文を保持する根拠用の一般名。"""

    def _normalize(self, value: object) -> str:
        if not isinstance(value, str):
            raise DomainValidationError("値は文字列である必要があります。")
        return value


@dataclass(frozen=True, slots=True)
class EvidenceSourceUrl(BaseString):
    """根拠の出典参照文字列。既存の入力契約を保持する。"""


@dataclass(frozen=True, slots=True)
class SearchUnitText(DomainPrimitive[str]):
    """空本文も含め、検索単位の原文をそのまま保持する。"""

    def validate(self) -> None:
        if not isinstance(self.value, str):
            raise DomainValidationError("text must be created from str")


@dataclass(frozen=True, slots=True)
class SearchUnitKind(BaseString):
    """原文を検索単位に加工した際の種類。JSONLの保存形式には依存しない。"""


@dataclass(frozen=True, slots=True)
class SearchUnitProductCode(BaseString):
    """検索単位に関連する製品コード。"""


@dataclass(frozen=True, slots=True)
class SearchUnitSectionCode(SearchSectionCode):
    """加工済み検索単位の番号形式の項目コード。"""

    def validate(self) -> None:
        super().validate()
        if re.fullmatch(r"\d+(?:\.\d+)*", self.value) is None:
            raise DomainValidationError("search unit section code must be numbered")


@dataclass(frozen=True, slots=True)
class SearchUnitUrl(BaseHttpUrl):
    """検索単位の外部参照URL。"""
