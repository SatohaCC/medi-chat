"""医薬品コード対応表の単一値。"""

import re
from dataclasses import dataclass

from ..foundation.primitives.primitives import BaseString
from .exceptions import MedicineDomainError


@dataclass(frozen=True, slots=True)
class ReceiptCode(BaseString):
    """9桁のレセ電コード。"""

    def validate(self) -> None:
        super().validate()
        if re.fullmatch(r"[0-9]{9}", self.value) is None:
            raise MedicineDomainError("receipt code must contain 9 digits")


@dataclass(frozen=True, slots=True)
class GenericNameCode(BaseString):
    """一般名コード。"""


@dataclass(frozen=True, slots=True)
class MedicineName(BaseString):
    """対応表に記載された医薬品名称を原文のまま保持する。"""

    def _normalize(self, value: object) -> str:
        if not isinstance(value, str):
            raise MedicineDomainError("medicine name must be str")
        return value


@dataclass(frozen=True, slots=True)
class GenericPrescriptionName(MedicineName):
    """一般名処方の標準的記載。成分名とは区別する。"""
