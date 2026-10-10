"""文字列Enumの入力正規化とエラーを共通化する。"""

from enum import StrEnum
from typing import Self

from ..exceptions import DomainValidationError
from .primitives import BaseString


class ValidatedStrEnum(StrEnum):
    @classmethod
    def _missing_(cls, value: object) -> Self | None:
        if isinstance(value, str):
            normalized = BaseString(value).value
            for member in cls:
                if member.value == normalized:
                    return member
        raise DomainValidationError(f"{cls.__name__} does not support value {value!r}")
