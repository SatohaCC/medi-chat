"""医薬品名称の照合に使う単一値。"""

from dataclasses import dataclass

from ..foundation.primitives.base import DomainPrimitive
from ..foundation.primitives.primitives import BaseString
from .exceptions import MedicineDomainError


@dataclass(frozen=True, slots=True)
class _MedicineName(DomainPrimitive[str]):
    """表示・検出された表記を変更せず保持する非空の名称。"""

    def validate(self) -> None:
        if not isinstance(self.value, str) or not self.value.strip():
            raise MedicineDomainError("medicine name must be a non-blank string")


@dataclass(frozen=True, slots=True)
class BrandName(_MedicineName):
    """販売名。"""


@dataclass(frozen=True, slots=True)
class GenericName(_MedicineName):
    """一般名。"""


@dataclass(frozen=True, slots=True)
class EnglishName(_MedicineName):
    """原本の英名。ASCIIだけに制限しない。"""


@dataclass(frozen=True, slots=True)
class HiraganaName(_MedicineName):
    """原本の読み名称。規格の数字・記号等も保持する。"""


@dataclass(frozen=True, slots=True)
class MatchedAlias(_MedicineName):
    """照合で検出された別名。"""


@dataclass(frozen=True, slots=True)
class ProductGroupId(BaseString):
    """名称照合で使う派生グループ識別値。成分同一性を保証しない。"""
