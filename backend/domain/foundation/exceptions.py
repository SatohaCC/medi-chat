"""ドメイン層の例外基底。"""


class DomainError(Exception):
    """ドメイン層から発生するすべての例外の基底クラス。"""


class DomainValidationError(DomainError):
    """ドメインのバリデーション違反を表す例外。"""


class DomainException(DomainError):
    """業務ルール違反を表す例外。"""
