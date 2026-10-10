"""医薬品コンテキストの業務例外。"""

from ..foundation.exceptions import DomainValidationError


class MedicineDomainError(DomainValidationError):
    """医薬品モデルの整合性に違反した。"""
