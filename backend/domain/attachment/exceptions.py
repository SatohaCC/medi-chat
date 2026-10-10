"""添付文書ドメイン固有の例外。"""

from ..foundation.exceptions import DomainError


class AttachmentDomainError(DomainError):
    """添付文書ドメインで発生した業務上の失敗。"""
