"""添付文書ドメイン固有の例外。"""

from ..foundation.exceptions import DomainError


class AttachmentDomainError(DomainError):
    """添付文書ドメインで発生した業務上の失敗。"""


class MissingOrInvalidYjError(AttachmentDomainError):
    """掲載製品全体を登録できない。名前や推測による補完をしない。"""

    code = "missing_or_invalid_yj"


class MissingRevisionError(AttachmentDomainError):
    """改訂年月がない原本を最新候補にしない。"""


class ConflictingRevisionError(AttachmentDomainError):
    """同じ改訂年月の別原本から最新を一意に選べない。"""
